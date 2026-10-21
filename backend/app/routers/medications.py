"""DoseNote endpoints: medication schedules and dose logs.

DoseNote is a personal tracking tool. It does not provide medical advice and
does not tell a user to change any prescribed medication or dose.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.common import MessageResponse
from app.schemas.medication import (
    DoseLogCreate,
    DoseLogResponse,
    DoseLogUpdate,
    MedicationAdherenceResponse,
    MedicationHistoryResponse,
    MedicationScheduleCreate,
    MedicationScheduleResponse,
    MedicationScheduleUpdate,
    TodayMedicationResponse,
)
from app.services import medication_service
from app.services.settings_service import get_app_settings

router = APIRouter(prefix="/api", tags=["DoseNote"])

MEDICAL_NOTE = (
    "DoseNote records the schedule you entered. It is not medical advice and "
    "does not tell you to change any prescribed medication."
)


@router.get("/medications/today", response_model=TodayMedicationResponse, summary="Today's doses")
def get_today_doses(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> TodayMedicationResponse:
    """Generates any missing 'pending' dose logs for today's active schedules,
    then returns them with taken / pending / skipped / missed counts."""
    grace = get_app_settings(db).dose_grace_minutes
    return medication_service.today_doses(db, tz_offset, grace)


@router.get(
    "/medications/history",
    response_model=MedicationHistoryResponse,
    summary="Dose history for a date range",
)
def get_dose_history(
    start_date: date | None = Query(None, description="Defaults to 7 days ago."),
    end_date: date | None = Query(None, description="Defaults to today."),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> MedicationHistoryResponse:
    """Dose logs newest-first, with per-day adherence figures."""
    from app.utils.dates import local_today

    today = local_today(tz_offset)
    end = end_date or today
    start = start_date or (end - timedelta(days=6))
    if start > end:
        start, end = end, start

    grace = get_app_settings(db).dose_grace_minutes
    data = medication_service.dose_history(db, start, end, limit, tz_offset, grace)

    series = medication_service.daily_adherence_series(db, start, end, tz_offset, grace)

    total_scheduled = sum(d.scheduled for d in series)
    total_taken = sum(d.taken for d in series)
    total_skipped = sum(d.skipped for d in series)
    total_missed = sum(d.missed for d in series)
    resolved = total_taken + total_skipped + total_missed
    adherence = round(total_taken / resolved * 100) if resolved else 0

    return MedicationHistoryResponse(
        start_date=start,
        end_date=end,
        total_scheduled=total_scheduled,
        total_taken=total_taken,
        total_skipped=total_skipped,
        total_missed=total_missed,
        adherence_percent=adherence,
        daily=series,
        recent=data["items"],
    )


@router.get(
    "/medications/adherence",
    response_model=MedicationAdherenceResponse,
    summary="Weekly adherence chart data",
)
def get_adherence(
    days: int = Query(7, ge=1, le=90, description="Number of days back from today."),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> MedicationAdherenceResponse:
    """Data for the adherence chart: per-day scheduled / taken / skipped / missed."""
    from app.utils.dates import local_today

    today = local_today(tz_offset)
    grace = get_app_settings(db).dose_grace_minutes
    return medication_service.adherence_report(
        db, today - timedelta(days=days - 1), today, tz_offset, grace
    )


@router.get(
    "/medications",
    response_model=list[MedicationScheduleResponse],
    summary="List medication schedules",
)
def list_schedules(
    search: str | None = Query(None, max_length=120),
    active_only: bool = Query(False),
    sort_by: str = Query("created_at", description="created_at | medication_name | start_date"),
    sort_order: str = Query("desc", description="asc | desc"),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> list[MedicationScheduleResponse]:
    """Each schedule includes its times and today's taken/pending counters."""
    grace = get_app_settings(db).dose_grace_minutes
    return medication_service.list_schedules(
        db,
        search=search,
        active_only=active_only,
        sort_by=sort_by,
        sort_order=sort_order,
        tz_offset=tz_offset,
        grace_minutes=grace,
    )


@router.post(
    "/medications",
    response_model=MedicationScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a medication schedule",
)
def create_schedule(
    payload: MedicationScheduleCreate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> MedicationScheduleResponse:
    """``scheduled_times`` accepts 1-12 times in HH:MM format. Duplicates are
    collapsed and times are sorted. end_date must not precede start_date."""
    schedule = medication_service.create_schedule(db, payload)
    grace = get_app_settings(db).dose_grace_minutes
    from app.utils.dates import local_today

    return medication_service.schedule_response(db, schedule, local_today(tz_offset), grace)


@router.get(
    "/medications/{schedule_id}",
    response_model=MedicationScheduleResponse,
    summary="Get one medication schedule",
)
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> MedicationScheduleResponse:
    """Returns 404 when the schedule does not exist."""
    grace = get_app_settings(db).dose_grace_minutes
    schedule = medication_service.get_schedule_or_404(db, schedule_id)
    from app.utils.dates import local_today

    return medication_service.schedule_response(db, schedule, local_today(tz_offset), grace)


@router.patch(
    "/medications/{schedule_id}",
    response_model=MedicationScheduleResponse,
    summary="Edit or deactivate a medication schedule",
)
def update_schedule(
    schedule_id: int,
    payload: MedicationScheduleUpdate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> MedicationScheduleResponse:
    """Set ``active: false`` to deactivate instead of deleting, so past dose logs
    stay intact. Replacing the times never deletes existing dose logs."""
    grace = get_app_settings(db).dose_grace_minutes
    schedule = medication_service.get_schedule_or_404(db, schedule_id)
    schedule = medication_service.update_schedule(db, schedule, payload)
    from app.utils.dates import local_today

    return medication_service.schedule_response(db, schedule, local_today(tz_offset), grace)


@router.post(
    "/medications/{schedule_id}/doses",
    response_model=DoseLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a dose for a schedule",
)
def create_dose(
    schedule_id: int,
    payload: DoseLogCreate,
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
    grace_minutes: int = Query(60, description="Minutes after the time before a dose counts as missed."),
) -> DoseLogResponse:
    """The time must be one of that schedule's times (400 otherwise). A second log
    for the same schedule + date + time returns 409 instead of creating a duplicate.
    New logs are always 'pending' unless you explicitly set a status."""
    from app.utils.dates import local_now

    schedule = medication_service.get_schedule_or_404(db, schedule_id)
    dose = medication_service.create_dose_log(db, schedule, payload, tz_offset)
    return medication_service._dose_response(dose, schedule, local_now(), grace_minutes)


@router.patch("/doses/{dose_log_id}", response_model=DoseLogResponse, summary="Correct a dose log")
def update_dose(
    dose_log_id: int,
    payload: DoseLogUpdate,
    db: Session = Depends(get_db),
) -> DoseLogResponse:
    """Mark a dose taken / skipped / pending again. Marking 'taken' without an
    explicit ``taken_at`` stores the current time. Moving back to pending clears
    ``taken_at`` so the history stays consistent."""
    from app.utils.dates import local_now

    grace = get_app_settings(db).dose_grace_minutes
    dose = medication_service.get_dose_or_404(db, dose_log_id)
    dose = medication_service.update_dose_log(db, dose, payload)
    schedule = medication_service.get_schedule_or_404(db, dose.medication_schedule_id)
    return medication_service._dose_response(dose, schedule, local_now(), grace)


@router.delete(
    "/doses/{dose_log_id}",
    response_model=MessageResponse,
    summary="Delete a dose log",
)
def delete_dose(dose_log_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    """The UI asks for confirmation before calling this."""
    dose = medication_service.get_dose_or_404(db, dose_log_id)
    db.delete(dose)
    db.commit()
    return MessageResponse(message="Dose log deleted.", success=True)


@router.delete(
    "/medications/{schedule_id}",
    response_model=MessageResponse,
    summary="Delete a medication schedule",
)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    """Deletes the schedule and all of its dose logs (ON DELETE CASCADE).
    The UI asks for confirmation before calling this."""
    schedule = medication_service.get_schedule_or_404(db, schedule_id)
    name = schedule.medication_name
    medication_service.delete_schedule(db, schedule)
    return MessageResponse(message=f"Deleted '{name}' and its dose logs.", success=True)