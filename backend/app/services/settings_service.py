"""Shared settings service: fetch-or-create the single-user settings rows."""

from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.hydration import HydrationSettings


def get_app_settings(db: Session) -> AppSettings:
    """Return the single AppSettings row, creating it with defaults if missing.

    Uses a nested transaction so that a concurrent request creating the same
    row cannot blow up with an IntegrityError.
    """
    settings_row = db.get(AppSettings, 1)
    if settings_row is not None:
        return settings_row

    try:
        with db.begin_nested():
            settings_row = AppSettings(id=1)
            db.add(settings_row)
            db.flush()
    except Exception:  # pragma: no cover - only on a genuine race
        db.rollback()
        settings_row = db.get(AppSettings, 1)
        if settings_row is None:
            raise
    db.commit()
    return settings_row


def get_hydration_settings(db: Session) -> HydrationSettings:
    """Return the single HydrationSettings row, creating it if missing."""
    settings_row = db.get(HydrationSettings, 1)
    if settings_row is not None:
        return settings_row

    try:
        with db.begin_nested():
            settings_row = HydrationSettings(id=1)
            db.add(settings_row)
            db.flush()
    except Exception:  # pragma: no cover - only on a genuine race
        db.rollback()
        settings_row = db.get(HydrationSettings, 1)
        if settings_row is None:
            raise
    db.commit()
    return settings_row


def get_currency(db: Session) -> str:
    """The user's preferred currency code (used as a display default)."""
    return get_app_settings(db).default_currency