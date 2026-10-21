"""Create the SQLite database and its tables.

Run it with:   python -m app.db.init_db

It is safe to run more than once - SQLAlchemy's ``create_all`` only adds
missing tables and never drops existing data.
"""

from app.db.base import Base
from app.db.session import engine
from app.models import (  # noqa: F401  (importing registers every table)
    AppSettings,
    Bill,
    Document,
    DocumentRenewal,
    DoseLog,
    HydrationSettings,
    MedicationSchedule,
    MedicationScheduleTime,
    WaterIntakeRecord,
)
from app.services.settings_service import get_app_settings, get_hydration_settings
from app.db.session import SessionLocal


def create_all() -> None:
    """Create every table that does not exist yet."""
    Base.metadata.create_all(bind=engine)


def ensure_settings_rows() -> None:
    """Make sure the two single-row settings tables have a row."""
    db = SessionLocal()
    try:
        get_app_settings(db)
        get_hydration_settings(db)
    finally:
        db.close()


def init_db() -> None:
    """Full initialization: tables + default settings rows."""
    create_all()
    ensure_settings_rows()


if __name__ == "__main__":
    init_db()
    print("DailyFlow database is ready.")
    print(f"Tables created: {', '.join(sorted(Base.metadata.tables.keys()))}")