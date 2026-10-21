"""All SQLAlchemy models for DailyFlow.

Importing this package registers every table with ``Base.metadata`` so that
``Base.metadata.create_all()`` can build the whole schema in one go.
"""

from app.db.base import Base
from app.models.app_settings import SUPPORTED_THEMES, AppSettings
from app.models.bill import (
    BILL_CATEGORIES,
    BILL_STATUSES,
    RECURRENCE_INTERVALS,
    SUPPORTED_CURRENCIES,
    Bill,
)
from app.models.document import (
    DOCUMENT_STATUSES,
    DOCUMENT_TYPES,
    Document,
    DocumentRenewal,
)
from app.models.hydration import HydrationSettings, WaterIntakeRecord
from app.models.medication import (
    DOSE_STATUSES,
    DOSAGE_UNITS,
    DoseLog,
    MedicationSchedule,
    MedicationScheduleTime,
)

__all__ = [
    "Base",
    "AppSettings",
    "Bill",
    "BILL_CATEGORIES",
    "BILL_STATUSES",
    "RECURRENCE_INTERVALS",
    "SUPPORTED_CURRENCIES",
    "SUPPORTED_THEMES",
    "Document",
    "DOCUMENT_TYPES",
    "DOCUMENT_STATUSES",
    "DocumentRenewal",
    "DoseLog",
    "MedicationSchedule",
    "MedicationScheduleTime",
    "DOSE_STATUSES",
    "DOSAGE_UNITS",
    "HydrationSettings",
    "WaterIntakeRecord",
]