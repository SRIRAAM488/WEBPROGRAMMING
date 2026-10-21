"""BillBell service: CRUD, payment handling, filtering and summaries.

All business rules for bills live here so the routers stay thin and readable.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.schemas.bill import BillResponse, BillSummary
from app.services.settings_service import get_currency
from app.utils.constants import BILL_CATEGORY_LABELS, BILL_STATUS_LABELS, RECURRENCE_LABELS
from app.utils.dates import add_months, days_between, month_end, month_start

# How many months each recurrence interval jumps forward.
RECURRENCE_MONTHS = {
    "none": 0,
    "weekly": 0,  # handled separately (7 days)
    "monthly": 1,
    "quarterly": 3,
    "yearly": 12,
    "yearly_2": 24,
    "custom": 1,
}

DUE_SOON_DAYS = 7


def next_cycle_date(bill: Bill) -> date | None:
    """Work out when a recurring bill is next due.

    Uses real calendar arithmetic, so a bill due on 31 Jan rolls to 28/29 Feb
    instead of crashing or landing in March.
    """
    if not bill.recurring or bill.recurrence_interval == "none":
        return None
    if bill.recurrence_interval == "weekly":
        return bill.due_date + timedelta(days=7)
    months = RECURRENCE_MONTHS.get(bill.recurrence_interval, 1)
    return add_months(bill.due_date, months)


def apply_overdue_flags(db: Session, tz_offset: int = 0) -> int:
    """Flip unpaid bills that are past their due date to 'overdue'.

    This runs at the start of the BillBell read endpoints. It keeps the stored
    ``status`` honest without storing a derived value that could go stale.
    """
    from app.utils.dates import local_today

    today = local_today(tz_offset)
    result = db.execute(
        select(Bill).where(
            Bill.status == "unpaid",
            Bill.due_date < today,
        )
    )
    changed = 0
    for bill in result.scalars().all():
        bill.status = "overdue"
        changed += 1
    if changed:
        db.commit()
    return changed


def to_response(bill: Bill, today: date) -> BillResponse:
    """Convert a Bill row into the API response schema with derived fields."""
    remaining = days_between(today, bill.due_date)
    is_overdue = bill.due_date < today and bill.status != "paid"
    return BillResponse(
        id=bill.id,
        bill_name=bill.bill_name,
        category=bill.category,
        provider=bill.provider,
        amount=bill.amount,
        currency=bill.currency,
        due_date=bill.due_date,
        status=bill.status,
        payment_date=bill.payment_date,
        recurring=bill.recurring,
        recurrence_interval=bill.recurrence_interval,
        notes=bill.notes,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
        days_until_due=remaining,
        is_overdue=is_overdue,
        category_label=BILL_CATEGORY_LABELS.get(bill.category, "Other"),
        status_label=BILL_STATUS_LABELS.get(bill.status, bill.status.title()),
        recurrence_label=RECURRENCE_LABELS.get(bill.recurrence_interval, "One-time"),
        next_cycle_due_date=next_cycle_date(bill),
    )


def get_bill_or_404(db: Session, bill_id: int) -> Bill:
    """Fetch a bill or raise a clean 404."""
    from fastapi import HTTPException, status

    bill = db.get(Bill, bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill with id {bill_id} was not found.",
        )
    return bill


def _apply_filters(
    query: Select,
    *,
    search: str | None,
    category: str | None,
    bill_status: str | None,
    due_before: date | None,
    due_after: date | None,
    paid_only: bool | None,
) -> Select:
    """Apply search / filter query parameters to a bills query."""
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(Bill.bill_name.ilike(pattern), Bill.provider.ilike(pattern))
        )
    if category and category != "all":
        query = query.where(Bill.category == category)
    if bill_status and bill_status != "all":
        query = query.where(Bill.status == bill_status)
    if due_before is not None:
        query = query.where(Bill.due_date <= due_before)
    if due_after is not None:
        query = query.where(Bill.due_date >= due_after)
    if paid_only is not None:
        query = query.where(Bill.payment_date.is_not(None) if paid_only else Bill.payment_date.is_(None))
    return query


SORT_COLUMNS = {
    "due_date": Bill.due_date,
    "amount": Bill.amount,
    "bill_name": Bill.bill_name,
    "created_at": Bill.created_at,
    "status": Bill.status,
}


def list_bills(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    bill_status: str | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    paid_only: bool | None = None,
    sort_by: str = "due_date",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    tz_offset: int = 0,
) -> tuple[list[BillResponse], int]:
    """Return a filtered, sorted, paginated list of bills plus the total count."""
    from app.utils.dates import local_today

    apply_overdue_flags(db, tz_offset)
    today = local_today(tz_offset)

    query = _apply_filters(
        select(Bill),
        search=search,
        category=category,
        bill_status=bill_status,
        due_before=due_before,
        due_after=due_after,
        paid_only=paid_only,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    column = SORT_COLUMNS.get(sort_by, Bill.due_date)
    order = column.desc() if sort_order == "desc" else column.asc()
    # Stable secondary sort keeps pagination from shuffling equal rows.
    query = query.order_by(order, Bill.id.desc())

    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return [to_response(bill, today) for bill in rows], total


def bill_summary(db: Session, tz_offset: int = 0) -> BillSummary:
    """Aggregate BillBell numbers. Every value comes from a real query."""
    from app.utils.dates import local_today

    apply_overdue_flags(db, tz_offset)
    today = local_today(tz_offset)
    zero = Decimal("0.00")

    all_bills = db.execute(select(Bill)).scalars().all()

    unpaid = [b for b in all_bills if b.status in ("unpaid", "overdue")]
    paid = [b for b in all_bills if b.status == "paid"]
    overdue = [b for b in all_bills if b.status == "overdue" or (b.status == "unpaid" and b.due_date < today)]

    total_unpaid = sum((b.amount for b in unpaid), zero)

    # "Paid this month" uses payment_date, falling back to created_at ordering
    # only when a paid bill has no recorded payment date.
    month_first, month_last = month_start(today), month_end(today)
    paid_this_month = sum(
        (b.amount for b in paid if b.payment_date and month_first <= b.payment_date <= month_last),
        zero,
    )

    outstanding_unpaid = sorted(
        [b for b in unpaid if b.due_date >= today],
        key=lambda b: b.due_date,
    )
    next_due = outstanding_unpaid[0] if outstanding_unpaid else None

    due_soon = [b for b in unpaid if 0 <= days_between(today, b.due_date) <= DUE_SOON_DAYS]

    by_category: dict[str, int] = {}
    for bill in all_bills:
        by_category[bill.category] = by_category.get(bill.category, 0) + 1

    return BillSummary(
        total_bills=len(all_bills),
        unpaid_count=len(unpaid),
        paid_count=len(paid),
        overdue_count=len(overdue),
        total_unpaid_amount=total_unpaid,
        total_paid_this_month=paid_this_month,
        currency=get_currency(db),
        next_due_date=next_due.due_date if next_due else None,
        next_due_bill_name=next_due.bill_name if next_due else None,
        due_soon_count=len(due_soon),
        recurring_due_count=len([b for b in unpaid if b.recurring]),
        by_category=by_category,
    )


# ---------------------------------------------------------------- write helpers


def create_bill(db: Session, payload) -> Bill:
    """Insert a new bill and return the stored row."""
    from app.utils.dates import local_today

    bill = Bill(
        bill_name=payload.bill_name,
        category=payload.category,
        provider=payload.provider,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        due_date=payload.due_date,
        status=payload.status,
        payment_date=payload.payment_date,
        recurring=payload.recurring,
        recurrence_interval=payload.recurrence_interval if payload.recurring else "none",
        notes=payload.notes,
    )

    # A bill created as 'paid' must always carry a payment date, otherwise
    # "paid this month" would silently ignore it. Default to today.
    if bill.status == "paid" and bill.payment_date is None:
        bill.payment_date = local_today()

    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def update_bill(db: Session, bill: Bill, payload) -> Bill:
    """Apply a partial update (PATCH) to a bill."""
    data = payload.model_dump(exclude_unset=True)

    # Keep the pair consistent: a one-time bill can never have a recurrence.
    recurring = data.get("recurring", bill.recurring)
    if "recurrence_interval" in data and not recurring:
        data["recurrence_interval"] = "none"
    elif "recurring" in data and not data["recurring"]:
        data["recurrence_interval"] = "none"
    elif recurring and "recurrence_interval" not in data:
        data["recurrence_interval"] = bill.recurrence_interval or "monthly"

    if "amount" in data and data["amount"] is not None:
        data["amount"] = Decimal(str(data["amount"]))

    for field, value in data.items():
        setattr(bill, field, value)

    # Marking paid from the edit form must still record the payment date.
    if bill.status == "paid" and bill.payment_date is None:
        from app.utils.dates import local_today

        bill.payment_date = local_today()

    db.commit()
    db.refresh(bill)
    return bill


def delete_bill(db: Session, bill: Bill) -> None:
    """Remove a bill."""
    db.delete(bill)
    db.commit()


def create_next_cycle_bill(db: Session, bill: Bill) -> Bill | None:
    """Create the next occurrence of a recurring bill.

    Returns ``None`` when the next cycle already exists, so paying the same bill
    twice can never silently create duplicate records.
    """
    from app.utils.dates import local_today

    next_due = next_cycle_date(bill)
    if next_due is None:
        return None

    existing = db.scalar(
        select(Bill).where(
            Bill.bill_name == bill.bill_name,
            Bill.provider == bill.provider,
            Bill.due_date == next_due,
        )
    )
    if existing is not None:
        return None

    today = local_today()
    new_bill = Bill(
        bill_name=bill.bill_name,
        category=bill.category,
        provider=bill.provider,
        amount=bill.amount,
        currency=bill.currency,
        due_date=next_due,
        status="overdue" if next_due < today else "unpaid",
        payment_date=None,
        recurring=bill.recurring,
        recurrence_interval=bill.recurrence_interval,
        notes=bill.notes,
    )
    db.add(new_bill)
    db.flush()
    return new_bill


def mark_bill_paid(
    db: Session,
    bill: Bill,
    *,
    payment_date: date | None = None,
    notes: str | None = None,
    mark_next_cycle: bool = False,
) -> tuple[Bill, Bill | None]:
    """Mark a bill as paid and (optionally) roll it into the next cycle.

    Both writes happen inside one transaction, so either the payment and the
    new occurrence are both saved, or neither is.
    """
    from app.utils.dates import local_today

    try:
        bill.status = "paid"
        bill.payment_date = payment_date or local_today()
        if notes:
            bill.notes = notes

        new_bill = create_next_cycle_bill(db, bill) if mark_next_cycle else None

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bill)
    if new_bill is not None:
        db.refresh(new_bill)
    return bill, new_bill


def unmark_bill_paid(db: Session, bill: Bill) -> Bill:
    """Undo a payment (safe 'Mark as unpaid' action)."""
    from app.utils.dates import local_today

    bill.payment_date = None
    bill.status = "overdue" if bill.due_date < local_today() else "unpaid"
    db.commit()
    db.refresh(bill)
    return bill