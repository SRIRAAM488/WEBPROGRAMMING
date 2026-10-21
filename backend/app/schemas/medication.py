"""Pydantic request / response schemas for DoseNote.

Reminder: DoseNote tracks a schedule the user already follows. It never
suggests a medication, a dose change, or any medical advice.
"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.medication import DOSE_STATUSES, DOSAGE_UNITS
from app.schemas.bill import normalise_choice, normalise_text
from app.utils.dates import parse_time_string


def normalise_times(values: list[str | time] | list[time]) -> list[time]:
    """Accept 'HH:MM' strings or time objects, de-duplicate and sort them."""
    parsed: list[time] = []
    for value in values:
        if isinstance(value, time):
            parsed.append(value.replace(second=0, microsecond=0))
        else:
            try:
                parsed.append(parse_time_string(str(value)).replace(second=0, microsecond=0))
            except ValueError as exc:
                raise ValueError(str(exc)) from exc

    unique = sorted(set(parsed))
    if not unique:
        raise ValueError("scheduled_times must contain at least one time")
    if len(unique) > 12:
        raise ValueError("a schedule cannot have more than 12 daily times")
    return unique


class MedicationScheduleBase(BaseModel):
    """Fields shared by create and update payloads."""

    medication_name: str = Field(..., min_length=1, max_length=120, examples=["Vitamin D3"])
    dosage: str = Field(..., min_length=1, max_length=40, examples=["1"])
    dosage_unit: str = Field("tablet", examples=["tablet"])
    instructions: str | None = Field(
        None,
        max_length=500,
        description="Free-text note the user enters themselves, e.g. 'after food'.",
    )
    start_date: date
    end_date: date | None = None
    active: bool = True
    notes: str | None = Field(None, max_length=1000)

    @field_validator("medication_name", "dosage", "instructions", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("dosage_unit")
    @classmethod
    def _check_unit(cls, value: str) -> str:
        return normalise_choice(value, DOSAGE_UNITS, "dosage_unit")


class MedicationScheduleCreate(MedicationScheduleBase):
    """POST /api/medications payload."""

    # Accepts 'HH:MM' strings and normalises them to time objects.
    scheduled_times: list[str | time] = Field(
        ...,
        min_length=1,
        max_length=12,
        description="Times of day in 24h HH:MM format, e.g. ['08:00', '20:00'].",
        examples=[["08:00", "20:00"]],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "medication_name": "Vitamin D3",
                "dosage": "1",
                "dosage_unit": "tablet",
                "instructions": "After food (user note)",
                "start_date": "2026-01-01",
                "scheduled_times": ["08:00"],
            }
        }
    )

    @field_validator("scheduled_times")
    @classmethod
    def _check_times(cls, value: list[str | time]) -> list[time]:
        return normalise_times(value)

    @field_validator("end_date")
    @classmethod
    def _check_end(cls, value: date | None, info) -> date | None:
        start = info.data.get("start_date")
        if value is not None and start is not None and value < start:
            raise ValueError("end_date cannot be earlier than start_date")
        return value


class MedicationScheduleUpdate(BaseModel):
    """PATCH /api/medications/{id} - every field optional."""

    medication_name: str | None = Field(None, min_length=1, max_length=120)
    dosage: str | None = Field(None, min_length=1, max_length=40)
    dosage_unit: str | None = None
    instructions: str | None = Field(None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    active: bool | None = None
    notes: str | None = Field(None, max_length=1000)
    scheduled_times: list[str | time] | None = Field(None, min_length=1, max_length=12)

    @field_validator("medication_name", "dosage", "instructions", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("dosage_unit")
    @classmethod
    def _check_unit(cls, value: str | None) -> str | None:
        return normalise_choice(value, DOSAGE_UNITS, "dosage_unit")

    @field_validator("scheduled_times")
    @classmethod
    def _check_times(cls, value: list[str | time] | None) -> list[time] | None:
        return normalise_times(value) if value is not None else None


class DoseLogCreate(BaseModel):
    """POST /api/medications/{schedule_id}/doses payload."""

    scheduled_date: date | None = Field(None, description="Defaults to today.")
    scheduled_time: str = Field(..., description="One of the schedule's times, HH:MM.")
    status: str = Field("pending", description="pending | taken | skipped")
    taken_at: datetime | None = None
    notes: str | None = Field(None, max_length=500)

    @field_validator("scheduled_time")
    @classmethod
    def _check_time(cls, value: str) -> time:
        try:
            return parse_time_string(value).replace(second=0, microsecond=0)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str) -> str:
        return normalise_choice(value, DOSE_STATUSES, "status")


class DoseLogUpdate(BaseModel):
    """PATCH /api/doses/{dose_log_id} payload."""

    status: str | None = None
    taken_at: datetime | None = None
    notes: str | None = Field(None, max_length=500)

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str | None) -> str | None:
        return normalise_choice(value, DOSE_STATUSES, "status")


class DoseLogResponse(BaseModel):
    """One dose log row, enriched with its medication details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_schedule_id: int
    medication_name: str
    dosage: str
    dosage_unit: str
    instructions: str | None = None

    scheduled_date: date
    scheduled_time: time
    status: str
    status_label: str = ""

    taken_at: datetime | None = None
    notes: str | None = None
    created_at: datetime | None = None

    # Derived by the service layer
    is_missed: bool = False
    is_due_now: bool = False


class MedicationScheduleResponse(MedicationScheduleBase):
    """A medication schedule as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    scheduled_times: list[time] = Field(default_factory=list)
    time_labels: list[str] = Field(default_factory=list)
    doses_today_total: int = 0
    doses_today_taken: int = 0
    doses_today_pending: int = 0
    doses_today_skipped: int = 0
    adherence_percent: int | None = None
    is_active_today: bool = False


class TodayMedicationResponse(BaseModel):
    """GET /api/medications/today"""

    date: date
    total_doses: int = 0
    taken: int = 0
    pending: int = 0
    skipped: int = 0
    missed: int = 0
    completion_percent: int = 0
    doses: list[DoseLogResponse] = Field(default_factory=list)


class MedicationHistoryResponse(BaseModel):
    """GET /api/medications/history"""

    start_date: date
    end_date: date
    total_scheduled: int = 0
    total_taken: int = 0
    total_skipped: int = 0
    total_missed: int = 0
    adherence_percent: int = 0
    daily: list["DailyAdherence"] = Field(default_factory=list)
    recent: list[DoseLogResponse] = Field(default_factory=list)


class DailyAdherence(BaseModel):
    """One bar in the weekly adherence chart."""

    date: date
    label: str
    scheduled: int = 0
    taken: int = 0
    skipped: int = 0
    missed: int = 0
    adherence_percent: int = 0


class MedicationAdherenceResponse(BaseModel):
    """GET /api/medications/adherence"""

    start_date: date
    end_date: date
    overall_adherence_percent: int = 0
    total_scheduled: int = 0
    total_taken: int = 0
    daily: list[DailyAdherence] = Field(default_factory=list)


MedicationHistoryResponse.model_rebuild()