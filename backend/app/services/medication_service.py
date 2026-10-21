"""DoseNote service: schedules, expected doses, dose logs and adherence.

Design notes
------------
* Expected doses are *generated* from active schedules for any given day. The
  generator never marks a dose as taken - it only ever creates 'pending' logs.
* A UNIQUE(schedule, date, time) constraint plus an explicit check means the
  same dose can never be logged twice.
* A dose is 'missed' when it is still pending more than ``grace_minutes`` after
  its scheduled time. It is never silently flipped to 'skipped'.

This module tracks a schedule the user already follows. It gives no medical
advice and never suggests changing a prescribed medication.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from app.models.medication import DoseLog, MedicationSchedule, MedicationScheduleTime
from app.schemas.medication import (
    DailyAdherence,
    DoseLogResponse,
    MedicationAdherenceResponse,
    MedicationScheduleResponse,
    TodayMedicationResponse,
)
from app.utils.constants import DOSE_STATUS_LABELS
from app.utils.dates import combine, local_now, local_today, parse_time_string, utc_now

DAY_LABEL_FORMAT = "%a"


def get_schedule_or_404(db: Session, schedule_id: int) -> MedicationSchedule:
    from fastapi import HTTPException, status

    schedule = db.get(MedicationSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication schedule with id {schedule_id} was not found.",
        )
    return schedule


def _time_label(value: time) -> str:
    """'08:00' -> '8:00 AM' for friendly display."""
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {suffix}"


def expected_times_for_day(schedule: MedicationSchedule, day: date) -> list[time]:
    """The times a schedule expects on ``day`` (empty when inactive that day)."""
    if not schedule.is_active_on(day):
        return []
    return sorted(item.scheduled_time for item in schedule.schedule_times)


def _is_missed(
    dose: DoseLog, now_local: datetime, grace_minutes: int
) -> bool:
    """A pending dose becomes 'missed' once the grace period has passed."""
    if dose.status != "pending":
        return False
    due = combine(dose.scheduled_date, dose.scheduled_time)
    return now_local > due + timedelta(minutes=grace_minutes)


def _is_due_now(dose: DoseLog, now_local: datetime, grace_minutes: int) -> bool:
    """A pending dose is 'due now' inside its grace window."""
    if dose.status != "pending":
        return False
    due = combine(dose.scheduled_date, dose.scheduled_time)
    return now_local >= due - timedelta(minutes=grace_minutes) and now_local <= due + timedelta(
        minutes=grace_minutes
    )


def _dose_response(
    dose: DoseLog,
    schedule: MedicationSchedule,
    now_local: datetime,
    grace_minutes: int,
) -> DoseLogResponse:
    """Build the enriched dose-log response schema."""
    return DoseLogResponse(
        id=dose.id,
        medication_schedule_id=dose.medication_schedule_id,
        medication_name=schedule.medication_name,
        dosage=schedule.dosage,
        dosage_unit=schedule.dosage_unit,
        instructions=schedule.instructions,
        scheduled_date=dose.scheduled_date,
        scheduled_time=dose.scheduled_time,
        status=dose.status,
        status_label=DOSE_STATUS_LABELS.get(dose.status, dose.status.title()),
        taken_at=dose.taken_at,
        notes=dose.notes,
        created_at=dose.created_at,
        is_missed=_is_missed(dose, now_local, grace_minutes),
        is_due_now=_is_due_now(dose, now_local, grace_minutes),
    )


def generate_doses_for_day(
    db: Session,
    day: date,
    *,
    grace_minutes: int = 60,
    flush_only: bool = True,
) -> int:
    """Create 'pending' dose logs for every active schedule on ``day``.

    Existing logs are left exactly as they are, so calling this repeatedly is
    safe. Returns the number of new rows created.
    """
    schedules = db.execute(
        select(MedicationSchedule)
        .options(selectinload(MedicationSchedule.schedule_times))
        .where(MedicationSchedule.active.is_(True))
    ).scalars().unique().all()

    if not schedules:
        return 0

    # Build the list of doses this day *should* have.
    wanted: list[tuple[int, time]] = []
    for schedule in schedules:
        for scheduled_time in expected_times_for_day(schedule, day):
            wanted.append((schedule.id, scheduled_time))

    if not wanted:
        return 0

    # Why ON CONFLICT DO NOTHING instead of a plain insert:
    #
    # The dashboard fires several requests at the same time (Promise.all), so
    # two of them can both call this function for the same day at the same
    # moment. A read-then-insert approach would have both requests decide the
    # dose log does not exist yet, and the second INSERT would then fail the
    # UNIQUE constraint and return a 500.
    #
    # "INSERT ... ON CONFLICT DO NOTHING" is decided atomically by SQLite
    # itself, so whichever request gets there first wins and the other silently
    # does nothing. Duplicates become impossible instead of merely unlikely.
    rows = [
        {
            "medication_schedule_id": schedule_id,
            "scheduled_date": day,
            "scheduled_time": scheduled_time,
            # Never auto-mark as taken.
            "status": "pending",
            "notes": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        for schedule_id, scheduled_time in wanted
    ]

    statement = sqlite_insert(DoseLog).values(rows)
    statement = statement.on_conflict_do_nothing(
        index_elements=[
            DoseLog.medication_schedule_id,
            DoseLog.scheduled_date,
            DoseLog.scheduled_time,
        ]
    )

    result = db.execute(statement)

    if flush_only:
        db.flush()
    else:
        db.commit()

    # rowcount is the number actually inserted (conflicts are not counted).
    return result.rowcount or 0


def schedule_response(
    db: Session,
    schedule: MedicationSchedule,
    today: date,
    grace_minutes: int = 60,
) -> MedicationScheduleResponse:
    """Convert a schedule row into its API schema, with today's counters."""
    now_local = local_now()
    doses_today = db.execute(
        select(DoseLog).where(
            DoseLog.medication_schedule_id == schedule.id,
            DoseLog.scheduled_date == today,
        )
    ).scalars().all()

    taken = len([d for d in doses_today if d.status == "taken"])
    skipped = len([d for d in doses_today if d.status == "skipped"])
    pending = len([d for d in doses_today if d.status == "pending"])

    times = sorted(item.scheduled_time for item in schedule.schedule_times)

    # Adherence for the last 30 days.
    window_start = today - timedelta(days=30)
    stats = db.execute(
        select(DoseLog.status, func.count(DoseLog.id))
        .where(
            DoseLog.medication_schedule_id == schedule.id,
            DoseLog.scheduled_date >= window_start,
            DoseLog.scheduled_date <= today,
        )
        .group_by(DoseLog.status)
    ).all()
    counts = {row[0]: row[1] for row in stats}
    total_30 = sum(counts.values())
    adherence = round(counts.get("taken", 0) / total_30 * 100) if total_30 else None

    return MedicationScheduleResponse(
        id=schedule.id,
        medication_name=schedule.medication_name,
        dosage=schedule.dosage,
        dosage_unit=schedule.dosage_unit,
        instructions=schedule.instructions,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        active=schedule.active,
        notes=schedule.notes,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        scheduled_times=times,
        time_labels=[_time_label(t) for t in times],
        doses_today_total=len(doses_today),
        doses_today_taken=taken,
        doses_today_pending=pending,
        doses_today_skipped=skipped,
        adherence_percent=adherence,
        is_active_today=schedule.is_active_on(today),
    )


def list_schedules(
    db: Session,
    *,
    search: str | None = None,
    active_only: bool = False,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    tz_offset: int = 0,
    grace_minutes: int = 60,
) -> list[MedicationScheduleResponse]:
    """Return all medication schedules with today's counters attached."""
    today = local_today(tz_offset)

    query = (
        select(MedicationSchedule)
        .options(
            selectinload(MedicationSchedule.schedule_times),
            selectinload(MedicationSchedule.dose_logs),
        )
    )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(MedicationSchedule.medication_name.ilike(pattern))
    if active_only:
        query = query.where(MedicationSchedule.active.is_(True))

    sort_columns = {
        "created_at": MedicationSchedule.created_at,
        "medication_name": MedicationSchedule.medication_name,
        "start_date": MedicationSchedule.start_date,
    }
    column = sort_columns.get(sort_by, MedicationSchedule.created_at)
    order = column.desc() if sort_order == "desc" else column.asc()

    schedules = db.execute(query.order_by(order, MedicationSchedule.id.desc())).scalars().unique().all()
    return [schedule_response(db, s, today, grace_minutes) for s in schedules]


def today_doses(db: Session, tz_offset: int = 0, grace_minutes: int = 60) -> TodayMedicationResponse:
    """Today's doses for every active schedule, generating pending logs first."""
    today = local_today(tz_offset)
    now_local = local_now()

    generate_doses_for_day(db, today, grace_minutes=grace_minutes)
    db.commit()

    schedules = {
        s.id: s
        for s in db.execute(
            select(MedicationSchedule).options(selectinload(MedicationSchedule.schedule_times))
        )
        .scalars()
        .unique()
        .all()
    }

    rows = db.execute(
        select(DoseLog)
        .where(DoseLog.scheduled_date == today)
        .order_by(DoseLog.scheduled_time.asc())
    ).scalars().all()

    items: list[DoseLogResponse] = []
    for dose in rows:
        schedule = schedules.get(dose.medication_schedule_id)
        if schedule is None:
            continue
        items.append(_dose_response(dose, schedule, now_local, grace_minutes))

    taken = len([i for i in items if i.status == "taken"])
    skipped = len([i for i in items if i.status == "skipped"])
    pending = len([i for i in items if i.status == "pending"])
    missed = len([i for i in items if i.is_missed])
    total = len(items)
    # Completion counts resolved doses (taken + skipped) against the total.
    completion = round((taken + skipped) / total * 100) if total else 0

    return TodayMedicationResponse(
        date=today,
        total_doses=total,
        taken=taken,
        pending=pending,
        skipped=skipped,
        missed=missed,
        completion_percent=completion,
        doses=items,
    )


def daily_adherence_series(
    db: Session, start: date, end: date, tz_offset: int = 0, grace_minutes: int = 60
) -> list[DailyAdherence]:
    """Build a per-day adherence series - the data behind the weekly chart."""
    today = local_today(tz_offset)
    now_local = local_now()

    # Make sure the range has its pending doses materialised.
    day = start
    while day <= end:
        generate_doses_for_day(db, day, grace_minutes=grace_minutes)
        day += timedelta(days=1)
    db.commit()

    schedules = {
        s.id: s
        for s in db.execute(
            select(MedicationSchedule).options(selectinload(MedicationSchedule.schedule_times))
        )
        .scalars()
        .unique()
        .all()
    }

    rows = db.execute(
        select(DoseLog).where(DoseLog.scheduled_date >= start, DoseLog.scheduled_date <= end)
    ).scalars().all()

    series: list[DailyAdherence] = []
    current = start
    while current <= end:
        day_doses = [d for d in rows if d.scheduled_date == current]
        taken = len([d for d in day_doses if d.status == "taken"])
        skipped = len([d for d in day_doses if d.status == "skipped"])
        # Only doses whose time has already passed can be 'missed'.
        missed = len(
            [
                d
                for d in day_doses
                if _is_missed(d, now_local, grace_minutes) and current <= today
            ]
        )
        scheduled = len(day_doses)
        resolved = taken + skipped + missed
        adherence = round(taken / resolved * 100) if resolved else 0

        series.append(
            DailyAdherence(
                date=current,
                label=current.strftime(DAY_LABEL_FORMAT),
                scheduled=scheduled,
                taken=taken,
                skipped=skipped,
                missed=missed,
                adherence_percent=adherence,
            )
        )
        current += timedelta(days=1)

    return series


def adherence_report(
    db: Session, start: date, end: date, tz_offset: int = 0, grace_minutes: int = 60
) -> MedicationAdherenceResponse:
    """Weekly (or custom range) adherence summary."""
    series = daily_adherence_series(db, start, end, tz_offset, grace_minutes)

    total_scheduled = sum(s.scheduled for s in series)
    total_taken = sum(s.taken for s in series)
    total_skipped = sum(s.skipped for s in series)
    total_missed = sum(s.missed for s in series)

    resolved = total_taken + total_skipped + total_missed
    overall = round(total_taken / resolved * 100) if resolved else 0

    return MedicationAdherenceResponse(
        start_date=start,
        end_date=end,
        overall_adherence_percent=overall,
        total_scheduled=total_scheduled,
        total_taken=total_taken,
        daily=series,
    )


def dose_history(
    db: Session,
    start: date,
    end: date,
    limit: int = 100,
    tz_offset: int = 0,
    grace_minutes: int = 60,
):
    """Dose logs inside a date range, newest first."""
    today = local_today(tz_offset)
    now_local = local_now()

    day = start
    while day <= end:
        generate_doses_for_day(db, day, grace_minutes=grace_minutes)
        day += timedelta(days=1)
    db.commit()

    schedules = {
        s.id: s
        for s in db.execute(
            select(MedicationSchedule).options(selectinload(MedicationSchedule.schedule_times))
        )
        .scalars()
        .unique()
        .all()
    }

    rows = db.execute(
        select(DoseLog)
        .where(DoseLog.scheduled_date >= start, DoseLog.scheduled_date <= end)
        .order_by(DoseLog.scheduled_date.desc(), DoseLog.scheduled_time.desc())
        .limit(limit)
    ).scalars().all()

    items = [
        _dose_response(dose, schedules[dose.medication_schedule_id], now_local, grace_minutes)
        for dose in rows
        if dose.medication_schedule_id in schedules
    ]

    taken = len([i for i in items if i.status == "taken"])
    skipped = len([i for i in items if i.status == "skipped"])
    missed = len([i for i in items if i.is_missed])

    return {
        "items": items,
        "total_taken": taken,
        "total_skipped": skipped,
        "total_missed": missed,
        "total_scheduled": len(items),
        "end_date": today if end > today else end,
    }


# --------------------------------------------------------------- write helpers


def _replace_schedule_times(db: Session, schedule: MedicationSchedule, times: list[time]) -> None:
    """Swap a schedule's times for a new set (schedule times only, never doses)."""
    schedule.schedule_times.clear()
    db.flush()
    for value in times:
        schedule.schedule_times.append(MedicationScheduleTime(scheduled_time=value))


def create_schedule(db: Session, payload) -> MedicationSchedule:
    """Create a medication schedule together with its daily times."""
    schedule = MedicationSchedule(
        medication_name=payload.medication_name,
        dosage=payload.dosage,
        dosage_unit=payload.dosage_unit,
        instructions=payload.instructions,
        start_date=payload.start_date,
        end_date=payload.end_date,
        active=payload.active,
        notes=payload.notes,
    )
    for value in payload.scheduled_times:
        schedule.schedule_times.append(MedicationScheduleTime(scheduled_time=value))

    try:
        db.add(schedule)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(schedule)
    return schedule


def update_schedule(db: Session, schedule: MedicationSchedule, payload) -> MedicationSchedule:
    """Apply a partial update to a schedule."""
    data = payload.model_dump(exclude_unset=True)
    times = data.pop("scheduled_times", None)

    if "start_date" in data and "end_date" not in data and schedule.end_date is not None:
        if data["start_date"] and schedule.end_date < data["start_date"]:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than the existing end_date.",
            )

    for field, value in data.items():
        setattr(schedule, field, value)

    try:
        if times:
            _replace_schedule_times(db, schedule, times)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: MedicationSchedule) -> None:
    """Delete a schedule; dose logs cascade away with it."""
    db.delete(schedule)
    db.commit()


def create_dose_log(
    db: Session,
    schedule: MedicationSchedule,
    payload,
    tz_offset: int = 0,
) -> DoseLog:
    """Log a dose for one of a schedule's times, rejecting duplicates."""
    from fastapi import HTTPException, status

    day: date = payload.scheduled_date or local_today(tz_offset)
    scheduled_time: time = payload.scheduled_time

    valid_times = expected_times_for_day(schedule, day)
    if valid_times and scheduled_time not in valid_times:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{scheduled_time.strftime('%H:%M')} is not one of this schedule's "
                f"times ({', '.join(t.strftime('%H:%M') for t in valid_times)})."
            ),
        )

    existing = db.scalar(
        select(DoseLog).where(
            DoseLog.medication_schedule_id == schedule.id,
            DoseLog.scheduled_date == day,
            DoseLog.scheduled_time == scheduled_time,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A dose log already exists for this schedule, date and time "
                f"(log id {existing.id}). Update it instead of creating a duplicate."
            ),
        )

    taken_at = payload.taken_at
    if payload.status == "taken" and taken_at is None:
        from app.utils.dates import utc_now

        taken_at = utc_now()

    dose = DoseLog(
        medication_schedule_id=schedule.id,
        scheduled_date=day,
        scheduled_time=scheduled_time,
        status=payload.status,
        taken_at=taken_at if payload.status == "taken" else None,
        notes=payload.notes,
    )

    try:
        db.add(dose)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(dose)
    return dose


def get_dose_or_404(db: Session, dose_id: int) -> DoseLog:
    from fastapi import HTTPException, status

    dose = db.get(DoseLog, dose_id)
    if dose is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dose log with id {dose_id} was not found.",
        )
    return dose


def update_dose_log(db: Session, dose: DoseLog, payload) -> DoseLog:
    """Correct a dose log (taken / skipped / pending)."""
    from app.utils.dates import utc_now

    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status", dose.status)

    if new_status == "taken":
        dose.status = "taken"
        dose.taken_at = data.get("taken_at") or dose.taken_at or utc_now()
    elif new_status == "pending":
        dose.status = "pending"
        dose.taken_at = None
    else:
        dose.status = new_status
        dose.taken_at = None

    if "notes" in data:
        dose.notes = data["notes"]
    elif "taken_at" in data:
        dose.taken_at = data["taken_at"]

    db.commit()
    db.refresh(dose)
    return dose


def delete_dose_log(db: Session, dose: DoseLog) -> None:
    """Delete a dose log row."""
    db.delete(dose)
    db.commit()