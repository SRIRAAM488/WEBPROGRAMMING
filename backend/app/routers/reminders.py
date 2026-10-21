"""Unified reminder centre endpoints.

These are IN-APP reminders: they are generated on demand from current database
state and shown while the DailyFlow page is open. DailyFlow does not send push
notifications, email or SMS, and nothing runs in the background once the tab is
closed.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.reminder import ReminderItem, ReminderListResponse, ReminderSummary
from app.services import reminder_service

router = APIRouter(prefix="/api/reminders", tags=["Reminders"])


@router.get("/summary", response_model=ReminderSummary, summary="Reminder counts for the badge")
def get_summary(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> ReminderSummary:
    """Small numbers: total, overdue, today, upcoming, per-module and per-priority."""
    return reminder_service.reminder_summary(db, tz_offset)


@router.get("/upcoming", response_model=list[ReminderItem], summary="Overdue + today + next days")
def get_upcoming(
    days: int = Query(7, ge=1, le=30, description="How many days ahead to include."),
    module: str | None = Query(None, description="billbell | dateguard | dosenote | aquahabit"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> list[ReminderItem]:
    """Everything still actionable in the near future, sorted by due moment."""
    modules = [module] if module else None
    items = reminder_service.build_all_reminders(db, modules=modules, tz_offset=tz_offset)

    from app.utils.dates import local_today

    cutoff = local_today(tz_offset)
    from datetime import timedelta

    limit_date = cutoff + timedelta(days=days)
    return [
        item
        for item in items
        if item.due_date is not None and item.due_date <= limit_date
    ][:limit]


@router.get("", response_model=ReminderListResponse, summary="Full reminder centre")
def list_reminders(
    module: list[str] | None = Query(None, description="Repeat to filter by module."),
    category: list[str] | None = Query(None, description="Repeat to filter by category."),
    priority: list[str] | None = Query(None, description="low | medium | high | urgent"),
    bucket: list[str] | None = Query(None, description="overdue | today | upcoming"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> ReminderListResponse:
    """Reminders from all four modules, grouped by overdue / today / upcoming.

    Each item has a stable ``id`` built from the event it describes, so the same
    event is never listed twice.
    """
    return reminder_service.reminder_list(
        db,
        modules=module,
        categories=category,
        priorities=priority,
        buckets=bucket,
        limit=limit,
        tz_offset=tz_offset,
    )