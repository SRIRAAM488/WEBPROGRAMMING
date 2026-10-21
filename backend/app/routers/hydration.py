"""AquaHabit endpoints: settings, today's intake, history and charts."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.common import MessageResponse
from app.schemas.hydration import (
    HydrationHistoryResponse,
    HydrationMonthlyResponse,
    HydrationSettingsResponse,
    HydrationSettingsUpdate,
    HydrationTodayResponse,
    HydrationWeeklyResponse,
    WaterIntakeCreate,
    WaterIntakeResponse,
    WaterIntakeUpdate,
)
from app.services import hydration_service
from app.services.settings_service import get_hydration_settings

router = APIRouter(prefix="/api/hydration", tags=["AquaHabit"])


@router.get("/settings", response_model=HydrationSettingsResponse, summary="Hydration goals")
def get_settings(db: Session = Depends(get_db)) -> HydrationSettingsResponse:
    """Daily goal and default serving size. Created with defaults on first read."""
    settings_row = get_hydration_settings(db)
    return HydrationSettingsResponse.model_validate(settings_row)


@router.patch("/settings", response_model=HydrationSettingsResponse, summary="Update hydration goals")
def update_settings(
    payload: HydrationSettingsUpdate,
    db: Session = Depends(get_db),
) -> HydrationSettingsResponse:
    """Changing the goal affects progress calculations from now on. Existing
    intake entries are never modified or deleted."""
    settings_row = hydration_service.update_hydration_settings(db, payload)
    return HydrationSettingsResponse.model_validate(settings_row)


@router.get("/today", response_model=HydrationTodayResponse, summary="Today's water intake")
def get_today(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> HydrationTodayResponse:
    """Today's total, remaining to goal, percent complete and the entry list.
    Daily progress resets by itself when the date changes - history is kept."""
    return hydration_service.today_summary(db, tz_offset)


@router.get("/weekly", response_model=HydrationWeeklyResponse, summary="Last 7 days (chart data)")
def get_weekly(
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> HydrationWeeklyResponse:
    """Per-day totals for the weekly bar chart, including the daily goal line."""
    return hydration_service.weekly_summary(db, tz_offset, days)


@router.get("/monthly", response_model=HydrationMonthlyResponse, summary="Current month overview")
def get_monthly(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> HydrationMonthlyResponse:
    """Month-to-date totals, average per day and days the goal was reached."""
    return hydration_service.monthly_summary(db, tz_offset)


@router.get("/history", response_model=HydrationHistoryResponse, summary="Intake for a date range")
def get_history(
    start_date: date | None = Query(None, description="Defaults to 30 days ago."),
    end_date: date | None = Query(None, description="Defaults to today."),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> HydrationHistoryResponse:
    """Daily totals for an arbitrary range, zero-filled so charts never break."""
    from datetime import timedelta

    from app.utils.dates import local_today

    today = local_today(tz_offset)
    end = end_date or today
    start = start_date or (end - timedelta(days=29))
    if start > end:
        start, end = end, start

    return hydration_service.history_summary(db, start, end, tz_offset)


@router.post(
    "/intake",
    response_model=WaterIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log water intake",
)
def create_intake(
    payload: WaterIntakeCreate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> WaterIntakeResponse:
    """amount_ml must be between 1 and 5000 (422 otherwise). Rejected values are
    blocked by both Pydantic and a database CHECK constraint."""
    entry = hydration_service.create_intake(db, payload, tz_offset)
    return WaterIntakeResponse.model_validate(entry)


@router.patch(
    "/intake/{entry_id}",
    response_model=WaterIntakeResponse,
    summary="Correct an intake entry",
)
def update_intake(
    entry_id: int,
    payload: WaterIntakeUpdate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> WaterIntakeResponse:
    """Lets you fix the amount, the timestamp, the day or the note. Updating the
    timestamp also recomputes entry_date so day totals stay correct."""
    entry = hydration_service.get_intake_or_404(db, entry_id)
    entry = hydration_service.update_intake(db, entry, payload, tz_offset)
    return WaterIntakeResponse.model_validate(entry)


@router.delete(
    "/intake/{entry_id}",
    response_model=MessageResponse,
    summary="Delete an intake entry",
)
def delete_intake(entry_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    """Removes only this entry; other days are untouched."""
    entry = hydration_service.get_intake_or_404(db, entry_id)
    amount = entry.amount_ml
    hydration_service.delete_intake(db, entry)
    return MessageResponse(message=f"Deleted a {amount} ml entry.", success=True)