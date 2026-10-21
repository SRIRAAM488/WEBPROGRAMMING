"""DateGuard service: document CRUD, derived expiry status and renewals.

Expiry status is always *derived* from ``expiry_date`` versus today's date. It is
never stored, so it can never go stale.
"""

from datetime import date, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentRenewal
from app.schemas.document import DocumentResponse, DocumentSummary
from app.utils.constants import DOCUMENT_STATUS_LABELS, DOCUMENT_TYPE_LABELS
from app.utils.dates import days_between, local_today
from app.utils.masking import mask_document_number

EXPIRY_WINDOWS = (7, 15, 30)


def derive_status(expiry_date: date, today: date, reminder_days_before: int) -> str:
    """Return 'expired', 'expiring_soon' or 'valid' for a document."""
    remaining = days_between(today, expiry_date)
    if remaining < 0:
        return "expired"
    if remaining <= max(reminder_days_before, 0):
        return "expiring_soon"
    return "valid"


def get_document_or_404(db: Session, document_id: int) -> Document:
    from fastapi import HTTPException, status

    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} was not found.",
        )
    return document


def to_response(
    document: Document,
    today: date,
    *,
    include_renewals: bool = False,
    include_full_number: bool = False,
) -> DocumentResponse:
    """Convert a Document row into the API schema with derived expiry info."""
    remaining = days_between(today, document.expiry_date)
    doc_status = derive_status(document.expiry_date, today, document.reminder_days_before)

    # Full document numbers are only ever returned on the single-document
    # endpoint, never in lists or on the dashboard.
    masked = mask_document_number(document.document_number)

    return DocumentResponse(
        id=document.id,
        document_name=document.document_name,
        document_type=document.document_type,
        document_number=document.document_number if include_full_number else None,
        issue_date=document.issue_date,
        expiry_date=document.expiry_date,
        issuing_authority=document.issuing_authority,
        reminder_days_before=document.reminder_days_before,
        notes=document.notes,
        archived=document.archived,
        created_at=document.created_at,
        updated_at=document.updated_at,
        status=doc_status,
        status_label=DOCUMENT_STATUS_LABELS.get(doc_status, doc_status.title()),
        days_remaining=remaining,
        is_expired=doc_status == "expired",
        is_expiring_soon=doc_status == "expiring_soon",
        document_type_label=DOCUMENT_TYPE_LABELS.get(document.document_type, "Other"),
        masked_document_number=masked,
        renewals=list(document.renewals) if include_renewals else [],
    )


def _apply_filters(
    query: Select,
    *,
    search: str | None,
    document_type: str | None,
    expiry_status: str | None,
    within_days: int | None,
    include_archived: bool,
    today: date,
) -> Select:
    """Apply search / filter parameters.

    ``expiry_status`` filters on the *derived* status, so it is resolved in
    Python after the SQL filters instead of in the database.
    """
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Document.document_name.ilike(pattern),
                Document.issuing_authority.ilike(pattern),
            )
        )
    if document_type and document_type != "all":
        query = query.where(Document.document_type == document_type)
    if not include_archived:
        query = query.where(Document.archived.is_(False))
    if within_days is not None:
        query = query.where(
            Document.expiry_date >= today,
            Document.expiry_date <= today + timedelta(days=within_days),
        )
    return query


def list_documents(
    db: Session,
    *,
    search: str | None = None,
    document_type: str | None = None,
    expiry_status: str | None = None,
    within_days: int | None = None,
    include_archived: bool = False,
    sort_by: str = "expiry_date",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    tz_offset: int = 0,
) -> tuple[list[DocumentResponse], int, int]:
    """Return filtered/sorted documents, the total count and the total count
    after the derived-status filter (for accurate pagination)."""
    today = local_today(tz_offset)

    query = _apply_filters(
        select(Document),
        search=search,
        document_type=document_type,
        expiry_status=expiry_status,
        within_days=within_days,
        include_archived=include_archived,
        today=today,
    )

    sort_columns = {
        "expiry_date": Document.expiry_date,
        "document_name": Document.document_name,
        "created_at": Document.created_at,
        "document_type": Document.document_type,
    }
    column = sort_columns.get(sort_by, Document.expiry_date)
    order = column.desc() if sort_order == "desc" else column.asc()
    query = query.order_by(order, Document.id.desc())

    rows = db.execute(query).scalars().all()

    # Derived-status filtering happens here.
    if expiry_status and expiry_status != "all":
        rows = [
            doc
            for doc in rows
            if derive_status(doc.expiry_date, today, doc.reminder_days_before) == expiry_status
        ]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    return [to_response(doc, today) for doc in page_rows], total, total


def document_summary(db: Session, tz_offset: int = 0) -> DocumentSummary:
    """Aggregate DateGuard numbers straight from the documents table."""
    today = local_today(tz_offset)
    documents = db.execute(
        select(Document).where(Document.archived.is_(False))
    ).scalars().all()

    remaining = [(days_between(today, d.expiry_date), d) for d in documents]

    expiring = sorted(
        [(r, d) for r, d in remaining if r >= 0], key=lambda pair: pair[0]
    )

    by_type: dict[str, int] = {}
    for doc in documents:
        by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1

    def count_within(days: int) -> int:
        return len([r for r, _ in remaining if 0 <= r <= days])

    next_pair = expiring[0] if expiring else None

    return DocumentSummary(
        total_documents=len(documents),
        active_documents=len(documents),
        expired_count=len([r for r, _ in remaining if r < 0]),
        expiring_in_7_days=count_within(7),
        expiring_in_15_days=count_within(15),
        expiring_in_30_days=count_within(30),
        next_expiry_date=next_pair[1].expiry_date if next_pair else None,
        next_expiry_name=next_pair[1].document_name if next_pair else None,
        by_type=by_type,
    )


def expiring_documents(db: Session, within_days: int = 30, tz_offset: int = 0) -> list[DocumentResponse]:
    """Documents expiring inside the window (soonest first), expired ones last."""
    today = local_today(tz_offset)
    limit = today + timedelta(days=within_days)
    rows = db.execute(
        select(Document)
        .where(Document.archived.is_(False), Document.expiry_date <= limit)
        .order_by(Document.expiry_date.asc())
    ).scalars().all()
    return [to_response(doc, today) for doc in rows]


# --------------------------------------------------------------- write helpers


def create_document(db: Session, payload) -> Document:
    """Insert a new document."""
    document = Document(
        document_name=payload.document_name,
        document_type=payload.document_type,
        document_number=payload.document_number,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        issuing_authority=payload.issuing_authority,
        reminder_days_before=payload.reminder_days_before,
        notes=payload.notes,
        archived=payload.archived,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_document(db: Session, document: Document, payload) -> Document:
    """Apply a partial update to a document."""
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> None:
    """Delete a document (renewal history is removed by the cascade)."""
    db.delete(document)
    db.commit()


def renew_document(db: Session, document: Document, payload) -> tuple[Document, DocumentRenewal]:
    """Record a renewal: store the old expiry, set the new one, log the history."""
    if payload.new_expiry_date <= document.expiry_date:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new expiry date must be later than the current expiry date.",
        )

    renewal = DocumentRenewal(
        document_id=document.id,
        previous_expiry_date=document.expiry_date,
        new_expiry_date=payload.new_expiry_date,
        notes=payload.notes,
    )

    try:
        document.expiry_date = payload.new_expiry_date
        if payload.issue_date is not None:
            document.issue_date = payload.issue_date
        if payload.document_number is not None:
            document.document_number = payload.document_number
        if payload.notes:
            document.notes = payload.notes

        db.add(renewal)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(document)
    db.refresh(renewal)
    return document, renewal