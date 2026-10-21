"""Schemas for the application settings page."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.bill import normalise_currency


class AppSettingsUpdate(BaseModel):
    """PATCH /api/settings - every field optional."""

    default_currency: str | None = None
    theme: str | None = Field(None, examples=["light"])
    bill_reminder_days_before: int | None = Field(None, ge=0, le=90)
    document_reminder_days_before: int | None = Field(None, ge=0, le=365)
    hydration_reminder_percent: int | None = Field(None, ge=10, le=100)
    dose_grace_minutes: int | None = Field(None, ge=0, le=1440)
    show_medical_disclaimer: bool | None = None

    @field_validator("default_currency")
    @classmethod
    def _check_currency(cls, value: str | None) -> str | None:
        return normalise_currency(value)

    @field_validator("theme")
    @classmethod
    def _check_theme(cls, value: str | None) -> str | None:
        if value is None:
            return None
        theme = value.strip().lower()
        if theme not in ("light", "dark"):
            raise ValueError("theme must be either 'light' or 'dark'")
        return theme


class AppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    default_currency: str
    theme: str
    bill_reminder_days_before: int
    document_reminder_days_before: int
    hydration_reminder_percent: int
    dose_grace_minutes: int
    show_medical_disclaimer: bool
    created_at: datetime
    updated_at: datetime
    notes: dict[str, str] = Field(default_factory=dict)


class AppSettingsMeta(BaseModel):
    """Option lists + explanatory notes used to build the settings form."""

    currencies: list[str]
    themes: list[str]
    hydration_quick_add_ml: list[int]
    reminder_windows: list[int]
    notes: dict[str, str]


class HealthResponse(BaseModel):
    """GET /api/health"""

    status: str
    app: str
    version: str
    database: str
    database_connected: bool
    server_date: datetime
    modules: list[str]