"""BillBell endpoints: CRUD, payment and summary.

Route order matters: the fixed paths (/summary, /search-suggestions) are declared
before /{bill_id} so FastAPI never treats "summary" as an id.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.bill import (
    BillCreate,
    BillListResponse,
    BillPayRequest,
    BillResponse,
    BillSummary,
    BillUpdate,
)
from app.schemas.common import MessageResponse
from app.services import bill_service

router = APIRouter(prefix="/api/bills", tags=["BillBell"])


@router.get("/summary", response_model=BillSummary, summary="BillBell totals for the dashboard")
def get_bill_summary(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> BillSummary:
    """Unpaid totals, paid-this-month total, next due bill and due-soon count."""
    return bill_service.bill_summary(db, tz_offset)


@router.get(
    "",
    response_model=BillListResponse,
    summary="List bills with search, filters, sorting and pagination",
)
def list_bills(
    search: str | None = Query(None, max_length=120, description="Match bill name or provider."),
    category: str | None = Query(None, description="Filter by category, or 'all'."),
    bill_status: str | None = Query(
        None, alias="status", description="unpaid | paid | overdue | all"
    ),
    due_before: date | None = Query(None, description="Only bills due on or before this date."),
    due_after: date | None = Query(None, description="Only bills due on or after this date."),
    paid_only: bool | None = Query(None),
    sort_by: str = Query("due_date", description="due_date | amount | bill_name | created_at | status"),
    sort_order: str = Query("asc", description="asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> BillListResponse:
    """Returns a paginated envelope: { items, total, page, page_size, total_pages }."""
    items, total = bill_service.list_bills(
        db,
        search=search,
        category=category,
        bill_status=bill_status,
        due_before=due_before,
        due_after=due_after,
        paid_only=paid_only,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        tz_offset=tz_offset,
    )
    return BillListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.post(
    "",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bill",
)
def create_bill(payload: BillCreate, db: Session = Depends(get_db)) -> BillResponse:
    """Amount must be greater than 0. Category, status, currency and recurrence
    are validated against the supported lists."""
    from app.utils.dates import local_today

    bill = bill_service.create_bill(db, payload)
    return bill_service.to_response(bill, local_today())


@router.post(
    "/{bill_id}/pay",
    response_model=BillResponse,
    summary="Mark a bill as paid",
)
def pay_bill(
    bill_id: int,
    payload: BillPayRequest | None = None,
    db: Session = Depends(get_db),
) -> BillResponse:
    """Records the payment date and sets status to 'paid' in one transaction.

    For a recurring bill, pass ``mark_next_cycle: true`` to also create the next
    occurrence. The service skips creation when that cycle already exists, so
    this endpoint can be called twice without producing duplicates.
    """
    payload = payload or BillPayRequest()
    bill = bill_service.get_bill_or_404(db, bill_id)
    bill, _new_bill = bill_service.mark_bill_paid(
        db,
        bill,
        payment_date=payload.payment_date,
        notes=payload.notes,
        mark_next_cycle=payload.mark_next_cycle,
    )
    from app.utils.dates import local_today

    return bill_service.to_response(bill, local_today())


@router.post(
    "/{bill_id}/unpay",
    response_model=BillResponse,
    summary="Undo a payment (mark as unpaid again)",
)
def unpay_bill(bill_id: int, db: Session = Depends(get_db)) -> BillResponse:
    """Safely clears payment_date and restores unpaid/overdue status."""
    from app.utils.dates import local_today

    bill = bill_service.get_bill_or_404(db, bill_id)
    bill = bill_service.unmark_bill_paid(db, bill)
    return bill_service.to_response(bill, local_today())


@router.get("/{bill_id}", response_model=BillResponse, summary="Get one bill")
def get_bill(bill_id: int, db: Session = Depends(get_db)) -> BillResponse:
    """Returns 404 when the bill does not exist."""
    from app.utils.dates import local_today

    bill = bill_service.get_bill_or_404(db, bill_id)
    return bill_service.to_response(bill, local_today())


@router.patch("/{bill_id}", response_model=BillResponse, summary="Edit a bill")
def update_bill(
    bill_id: int,
    payload: BillUpdate,
    db: Session = Depends(get_db),
) -> BillResponse:
    """Partial update - only the fields you send are changed."""
    from app.utils.dates import local_today

    bill = bill_service.get_bill_or_404(db, bill_id)
    bill = bill_service.update_bill(db, bill, payload)
    return bill_service.to_response(bill, local_today())


@router.delete(
    "/{bill_id}",
    response_model=MessageResponse,
    summary="Delete a bill",
)
def delete_bill(bill_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    """The UI asks for confirmation before calling this."""
    bill = bill_service.get_bill_or_404(db, bill_id)
    name = bill.bill_name
    bill_service.delete_bill(db, bill)
    return MessageResponse(message=f"Deleted '{name}'.", success=True)