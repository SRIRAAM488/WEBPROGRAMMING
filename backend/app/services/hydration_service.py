"""AquaHabit service: intake records, goals, daily/weekly/monthly rollups."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.hydration import WaterIntakeRecord
from app.schemas.hydration import (
    HydrationDaySummary,
    HydrationHistoryResponse,
    HydrationMonthlyResponse,
    HydrationTodayResponse,
    HydrationWeeklyResponse,
    WaterIntakeResponse,
)
from app.services.settings_service import get_hydration_settings
from app.utils.dates import local_today, month_end, month_start, utc_now, week_start

HYDRATION_NOTE = "Your goal is a personal preference, not medical advice."


def _day_label(day: date) -> str:
    return day.strftime("%a")


def _percent(total: int, goal: int) -> int:
    """Percentage of the goal, safe when the goal is 0 or changed."""
    if goal <= 0:
        return 0
    return round(total / goal * 100)


def _local_date_from(moment: datetime, tz_offset: int) -> date:
    """Work out which local day a UTC timestamp belongs to."""
    if moment.tzinfo is None:
        return moment.date()
    return (moment + timedelta(minutes=tz_offset)).date()


def daily_totals(db: Session, start: date, end: date) -> dict[date, int]:
    """Total ml per day for an inclusive date range, in one query."""
    rows = db.execute(
        select(WaterIntakeRecord.entry_date, func.sum(WaterIntakeRecord.amount_ml))
        .where(WaterIntakeRecord.entry_date >= start, WaterIntakeRecord.entry_date <= end)
        .group_by(WaterIntakeRecord.entry_date)
    ).all()
    return {row[0]: int(row[1] or 0) for row in rows}


def entry_counts(db: Session, start: date, end: date) -> dict[date, int]:
    """How many separate entries were logged per day."""
    rows = db.execute(
        select(WaterIntakeRecord.entry_date, func.count(WaterIntakeRecord.id))
        .where(WaterIntakeRecord.entry_date >= start, WaterIntakeRecord.entry_date <= end)
        .group_by(WaterIntakeRecord.entry_date)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _build_series(
    db: Session,
    start: date,
    end: date,
    goal_ml: int,
) -> list[HydrationDaySummary]:
    """Turn per-day totals into chart-ready summaries, zero-filling gaps."""
    totals = daily_totals(db, start, end)
    counts = entry_counts(db, start, end)

    series: list[HydrationDaySummary] = []
    current = start
    while current <= end:
        total = totals.get(current, 0)
        series.append(
            HydrationDaySummary(
                date=current,
                label=_day_label(current),
                total_ml=total,
                goal_ml=goal_ml,
                entry_count=counts.get(current, 0),
                percent_complete=_percent(total, goal_ml),
                goal_reached=goal_ml > 0 and total >= goal_ml,
            )
        )
        current += timedelta(days=1)
    return series


def today_summary(db: Session, tz_offset: int = 0) -> HydrationTodayResponse:
    """Today's intake, goal and progress.

    Daily progress resets automatically because every entry carries its own
    ``entry_date`` - nothing is deleted when the date changes.
    """
    settings = get_hydration_settings(db)
    today = local_today(tz_offset)

    total = db.scalar(
        select(func.coalesce(func.sum(WaterIntakeRecord.amount_ml), 0)).where(
            WaterIntakeRecord.entry_date == today
        )
    )
    total = int(total or 0)

    entries = db.execute(
        select(WaterIntakeRecord)
        .where(WaterIntakeRecord.entry_date == today)
        .order_by(WaterIntakeRecord.consumed_at.desc())
    ).scalars().all()

    goal = settings.daily_goal_ml

    return HydrationTodayResponse(
        date=today,
        total_ml=total,
        goal_ml=goal,
        remaining_ml=max(0, goal - total),
        percent_complete=_percent(total, goal),
        goal_reached=goal > 0 and total >= goal,
        default_serving_ml=settings.default_serving_ml,
        entries=[WaterIntakeResponse.model_validate(entry) for entry in entries],
        note=HYDRATION_NOTE,
    )


def weekly_summary(db: Session, tz_offset: int = 0, days: int = 7) -> HydrationWeeklyResponse:
    """Rolling window of the last N days ending today, for the weekly bar chart.

    A rolling window (not a Monday-to-Sunday week) always returns exactly ``days``
    points, which is what the dashboard chart expects.
    """
    settings = get_hydration_settings(db)
    today = local_today(tz_offset)
    end = today
    start = today - timedelta(days=days - 1)

    goal = settings.daily_goal_ml
    series = _build_series(db, start, end, goal)

    total = sum(d.total_ml for d in series)
    logged_days = len([d for d in series if d.entry_count > 0])

    return HydrationWeeklyResponse(
        start_date=start,
        end_date=end,
        goal_ml=goal,
        total_ml=total,
        average_ml=round(total / len(series)) if series else 0,
        days_goal_reached=len([d for d in series if d.goal_reached]),
        best_day=max(series, key=lambda d: d.total_ml) if series else None,
        daily=series,
    )


def history_summary(
    db: Session, start: date, end: date, tz_offset: int = 0
) -> HydrationHistoryResponse:
    """Hydration totals over an arbitrary date range."""
    settings = get_hydration_settings(db)
    goal = settings.daily_goal_ml
    series = _build_series(db, start, end, goal)

    total = sum(d.total_ml for d in series)
    logged = len([d for d in series if d.entry_count > 0])

    return HydrationHistoryResponse(
        start_date=start,
        end_date=end,
        goal_ml=goal,
        total_ml=total,
        average_ml=round(total / len(series)) if series else 0,
        days_logged=logged,
        days_goal_reached=len([d for d in series if d.goal_reached]),
        daily=series,
    )


def monthly_summary(db: Session, tz_offset: int = 0) -> HydrationMonthlyResponse:
    """Current calendar month overview."""
    settings = get_hydration_settings(db)
    today = local_today(tz_offset)
    start, end = month_start(today), month_end(today)

    goal = settings.daily_goal_ml
    series = _build_series(db, start, end, goal)
    total = sum(d.total_ml for d in series)
    logged = len([d for d in series if d.entry_count > 0])

    return HydrationMonthlyResponse(
        month=today.strftime("%B"),
        year=today.year,
        goal_ml=goal,
        total_ml=total,
        average_ml=round(total / len(series)) if series else 0,
        days_logged=logged,
        days_goal_reached=len([d for d in series if d.goal_reached]),
        daily=series,
    )


def update_hydration_settings(db: Session, payload) -> object:
    """Update the daily goal / default serving size.

    Changing the goal only affects progress *calculation* from now on. Existing
    intake entries are never modified or deleted.
    """
    settings = get_hydration_settings(db)
    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        if value is not None:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


def get_intake_or_404(db: Session, entry_id: int) -> WaterIntakeRecord:
    from fastapi import HTTPException, status

    entry = db.get(WaterIntakeRecord, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Water intake entry with id {entry_id} was not found.",
        )
    return entry


def create_intake(db: Session, payload, tz_offset: int = 0) -> WaterIntakeRecord:
    """Log water. Zero / negative amounts are rejected by the schema *and* by a
    database CHECK constraint, so bad data can never be stored."""
    consumed_at = payload.consumed_at or utc_now()

    if consumed_at.tzinfo is None:
        consumed_at = consumed_at.replace(tzinfo=ZoneInfo("UTC"))

    entry_date = payload.entry_date or _local_date_from(consumed_at, tz_offset)

    entry = WaterIntakeRecord(
        amount_ml=int(payload.amount_ml),
        consumed_at=consumed_at,
        entry_date=entry_date,
        notes=payload.notes,
    )

    try:
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(entry)
    return entry


def update_intake(db: Session, entry: WaterIntakeRecord, payload, tz_offset: int = 0) -> WaterIntakeRecord:
    """Correct a logged entry (amount, time, day or note)."""
    data = payload.model_dump(exclude_unset=True)

    if "amount_ml" in data and data["amount_ml"] is not None:
        entry.amount_ml = int(data["amount_ml"])

    if "consumed_at" in data and data["consumed_at"] is not None:
        consumed_at = data["consumed_at"]
        if consumed_at.tzinfo is None:
            consumed_at = consumed_at.replace(tzinfo=ZoneInfo("UTC"))
        entry.consumed_at = consumed_at

    if "entry_date" in data and data["entry_date"] is not None:
        entry.entry_date = data["entry_date"]
    elif "consumed_at" in data and data["consumed_at"] is not None:
        # Keep entry_date consistent with the new timestamp.
        entry.entry_date = _local_date_from(entry.consumed_at, tz_offset)

    if "notes" in data:
        entry.notes = data["notes"]

    db.commit()
    db.refresh(entry)
    return entry


def delete_intake(db: Session, entry: WaterIntakeRecord) -> None:
    """Remove an intake entry. History for other days is untouched."""
    db.delete(entry)
    db.commit()