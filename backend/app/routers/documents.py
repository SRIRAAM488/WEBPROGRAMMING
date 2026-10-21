"""DateGuard endpoints: documents, expiry windows, summary and renewals."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.common import MessageResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentRenewRequest,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
)
from app.services import document_service
from app.utils.dates import local_today

router = APIRouter(prefix="/api/documents", tags=["DateGuard"])


@router.get("/expiring", response_model=list[DocumentResponse], summary="Documents expiring soon")
def get_expiring_documents(
    within_days: int = Query(30, ge=1, le=365, description="Expiry window in days."),
    include_expired: bool = Query(True, description="Include already-expired documents."),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> list[DocumentResponse]:
    """Documents inside the window, soonest expiry first. Expired ones sort last."""
    today = local_today(tz_offset)
    results = document_service.expiring_documents(db, within_days, tz_offset)
    if not include_expired:
        results = [doc for doc in results if not doc.is_expired]
    return results


@router.get("/summary", response_model=DocumentSummary, summary="DateGuard totals")
def get_document_summary(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentSummary:
    """Counts of active, expired and expiring-soon documents plus next expiry."""
    return document_service.document_summary(db, tz_offset)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents with search, filters and sorting",
)
def list_documents(
    search: str | None = Query(None, max_length=120, description="Match name or authority."),
    document_type: str | None = Query(None, description="Filter by type, or 'all'."),
    expiry_status: str | None = Query(
        None, alias="status", description="expired | expiring_soon | valid | all"
    ),
    within_days: int | None = Query(None, ge=1, le=365, description="Expiring within N days."),
    include_archived: bool = Query(False),
    sort_by: str = Query("expiry_date", description="expiry_date | document_name | created_at | document_type"),
    sort_order: str = Query("asc", description="asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentListResponse:
    """``status`` filters on the derived expiry status, so it is always current."""
    items, total, _ = document_service.list_documents(
        db,
        search=search,
        document_type=document_type,
        expiry_status=expiry_status,
        within_days=within_days,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        tz_offset=tz_offset,
    )
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track a document",
)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentResponse:
    """The stored status is always derived from expiry_date, never accepted from input."""
    document = document_service.create_document(db, payload)
    return document_service.to_response(document, local_today(tz_offset))


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get one document (full number + renewal history)",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentResponse:
    """This is the only endpoint that returns the unmasked document number and
    the renewal history. List and dashboard views always return a masked number."""
    document = document_service.get_document_or_404(db, document_id)
    return document_service.to_response(
        document,
        local_today(tz_offset),
        include_renewals=True,
        include_full_number=True,
    )


@router.patch("/{document_id}", response_model=DocumentResponse, summary="Edit a document")
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentResponse:
    """Partial update - only the fields you send are changed."""
    document = document_service.get_document_or_404(db, document_id)
    document = document_service.update_document(db, document, payload)
    return document_service.to_response(
        document, local_today(tz_offset), include_full_number=True
    )


@router.post(
    "/{document_id}/renew",
    response_model=DocumentResponse,
    summary="Record a renewal and update the expiry date",
)
def renew_document(
    document_id: int,
    payload: DocumentRenewRequest,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DocumentResponse:
    """Stores the previous expiry in the renewal history, then sets the new one.
    The new expiry must be later than the current expiry (400 otherwise)."""
    document = document_service.get_document_or_404(db, document_id)
    document, _renewal = document_service.renew_document(db, document, payload)
    return document_service.to_response(
        document, local_today(tz_offset), include_renewals=True
    )


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document",
)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    """Renewal history is removed too (ON DELETE CASCADE)."""
    document = document_service.get_document_or_404(db, document_id)
    name = document.document_name
    document_service.delete_document(db, document)
    return MessageResponse(message=f"Deleted '{name}'.", success=True)