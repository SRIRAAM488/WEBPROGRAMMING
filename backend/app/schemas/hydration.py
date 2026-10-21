"""Pydantic request / response schemas for AquaHabit."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.bill import normalise_text

MAX_INTAKE_ML = 5000


class HydrationSettingsBase(BaseModel):
    """Fields shared by the settings create/update payloads."""

    daily_goal_ml: int = Field(2000, gt=0, le=10_000)
    default_serving_ml: int = Field(250, gt=0, le=MAX_INTAKE_ML)
    reminder_enabled: bool = True


class HydrationSettingsUpdate(BaseModel):
    """PATCH /api/hydration/settings - every field optional."""

    daily_goal_ml: int | None = Field(None, gt=0, le=10_000)
    default_serving_ml: int | None = Field(None, gt=0, le=MAX_INTAKE_ML)
    reminder_enabled: bool | None = None

    @field_validator("default_serving_ml")
    @classmethod
    def _check_serving(cls, value: int | None) -> int | None:
        # Serving bigger than the goal makes no sense, but a goal change can
        # legitimately lower the goal below the serving, so we only warn-by-doc.
        return value


class HydrationSettingsResponse(HydrationSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    note: str = "Your goal is a personal preference, not medical advice."


class WaterIntakeCreate(BaseModel):
    """POST /api/hydration/intake payload."""

    amount_ml: int = Field(..., gt=0, le=MAX_INTAKE_ML, examples=[250])
    consumed_at: datetime | None = Field(
        None, description="Defaults to now. Use this to back-fill a missing entry."
    )
    entry_date: date | None = Field(
        None, description="Overrides the local day derived from consumed_at."
    )
    notes: str | None = Field(None, max_length=300)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, value: str | None) -> str | None:
        return normalise_text(value)


class WaterIntakeUpdate(BaseModel):
    """PATCH /api/hydration/intake/{id} - lets the user correct an entry."""

    amount_ml: int | None = Field(None, gt=0, le=MAX_INTAKE_ML)
    consumed_at: datetime | None = None
    entry_date: date | None = None
    notes: str | None = Field(None, max_length=300)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, value: str | None) -> str | None:
        return normalise_text(value)


class WaterIntakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_ml: int
    consumed_at: datetime
    entry_date: date
    notes: str | None = None
    created_at: datetime


class HydrationDaySummary(BaseModel):
    """One day's hydration numbers - used by today, weekly and charts."""

    date: date
    label: str
    total_ml: int = 0
    goal_ml: int = 0
    entry_count: int = 0
    percent_complete: int = 0
    goal_reached: bool = False


class HydrationTodayResponse(BaseModel):
    """GET /api/hydration/today"""

    date: date
    total_ml: int = 0
    goal_ml: int = 0
    remaining_ml: int = 0
    percent_complete: int = 0
    goal_reached: bool = False
    default_serving_ml: int = 250
    entries: list[WaterIntakeResponse] = Field(default_factory=list)
    note: str = "Your goal is a personal preference, not medical advice."


class HydrationHistoryResponse(BaseModel):
    """GET /api/hydration/history"""

    start_date: date
    end_date: date
    goal_ml: int = 0
    total_ml: int = 0
    average_ml: int = 0
    days_logged: int = 0
    days_goal_reached: int = 0
    daily: list[HydrationDaySummary] = Field(default_factory=list)


class HydrationWeeklyResponse(BaseModel):
    """GET /api/hydration/weekly"""

    start_date: date
    end_date: date
    goal_ml: int = 0
    total_ml: int = 0
    average_ml: int = 0
    days_goal_reached: int = 0
    best_day: HydrationDaySummary | None = None
    daily: list[HydrationDaySummary] = Field(default_factory=list)


class HydrationMonthlyResponse(BaseModel):
    """GET /api/hydration/monthly"""

    month: str
    year: int
    goal_ml: int = 0
    total_ml: int = 0
    average_ml: int = 0
    days_logged: int = 0
    days_goal_reached: int = 0
    daily: list[HydrationDaySummary] = Field(default_factory=list)