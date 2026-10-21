"""Application settings endpoints and the health check."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings as app_config
from app.db.session import get_db
from app.schemas.settings import (
    AppSettingsMeta,
    AppSettingsResponse,
    AppSettingsUpdate,
    HealthResponse,
)
from app.services.settings_service import get_app_settings
from app.utils.dates import utc_now

router = APIRouter(prefix="/api", tags=["Settings"])

# Notes shown under each setting so the user knows what it changes.
SETTING_NOTES = {
    "default_currency": (
        "Used as the default currency for new bills. Existing bills keep the "
        "currency they were created with. No conversion is performed."
    ),
    "theme": "Light or dark appearance for DailyFlow. Saved in the database and applied on reload.",
    "bill_reminder_days_before": (
        "How early a reminder appears for an unpaid bill. Does not change any bill data."
    ),
    "document_reminder_days_before": (
        "Fallback reminder lead time. Each document can still override it with its own "
        "'remind me before' value."
    ),
    "hydration_reminder_percent": (
        "The in-app hydration nudge appears once you are below this percentage of your goal."
    ),
    "dose_grace_minutes": (
        "A pending dose counts as 'missed' after this many minutes past its scheduled time. "
        "It is never changed automatically to 'taken'."
    ),
    "show_medical_disclaimer": "Show the DoseNote reminder that the app is not medical advice.",
}


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Verifies the API is up and the database connection works."""
    connected = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        connected = False

    return HealthResponse(
        status="ok" if connected else "degraded",
        app=app_config.APP_NAME,
        version=app_config.APP_VERSION,
        database="SQLite",
        database_connected=connected,
        server_date=utc_now(),
        modules=["BillBell", "DateGuard", "DoseNote", "AquaHabit"],
    )


@router.get("/settings/meta", response_model=AppSettingsMeta, summary="Settings form options")
def get_settings_meta() -> AppSettingsMeta:
    """Option lists (currencies, themes, quick-add sizes) used by the settings form."""
    from app.models.app_settings import SUPPORTED_THEMES
    from app.models.bill import SUPPORTED_CURRENCIES

    return AppSettingsMeta(
        currencies=list(SUPPORTED_CURRENCIES),
        themes=list(SUPPORTED_THEMES),
        hydration_quick_add_ml=[150, 250, 350, 500],
        reminder_windows=[1, 3, 7, 14, 30],
        notes=SETTING_NOTES,
    )


@router.get("/settings", response_model=AppSettingsResponse, summary="Current settings")
def get_settings(db: Session = Depends(get_db)) -> AppSettingsResponse:
    """Returns the single settings row, creating it with defaults on first read."""
    row = get_app_settings(db)
    return _to_response(row)


@router.patch("/settings", response_model=AppSettingsResponse, summary="Update settings")
def update_settings(
    payload: AppSettingsUpdate,
    db: Session = Depends(get_db),
) -> AppSettingsResponse:
    """Partial update. Settings that are not sent keep their current value."""
    row = get_app_settings(db)
    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return _to_response(row)


def _to_response(row) -> AppSettingsResponse:
    """Build the settings response schema with the explanatory notes attached."""
    return AppSettingsResponse(
        id=row.id,
        default_currency=row.default_currency,
        theme=row.theme,
        bill_reminder_days_before=row.bill_reminder_days_before,
        document_reminder_days_before=row.document_reminder_days_before,
        hydration_reminder_percent=row.hydration_reminder_percent,
        dose_grace_minutes=row.dose_grace_minutes,
        show_medical_disclaimer=row.show_medical_disclaimer,
        created_at=row.created_at,
        updated_at=row.updated_at,
        notes=SETTING_NOTES,
    )