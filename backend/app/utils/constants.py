"""Labels and other shared constants used by schemas and services."""

from app.models.app_settings import SUPPORTED_THEMES
from app.models.bill import BILL_CATEGORIES, BILL_STATUSES, RECURRENCE_INTERVALS, SUPPORTED_CURRENCIES
from app.models.document import DOCUMENT_STATUSES, DOCUMENT_TYPES
from app.models.medication import DOSE_STATUSES, DOSAGE_UNITS

# Human readable labels so the frontend does not have to duplicate them.
BILL_CATEGORY_LABELS = {
    "electricity": "Electricity",
    "water": "Water",
    "internet": "Internet",
    "mobile": "Mobile",
    "rent": "Rent",
    "subscription": "Subscription",
    "education": "Education",
    "insurance": "Insurance",
    "other": "Other",
}

BILL_STATUS_LABELS = {
    "unpaid": "Unpaid",
    "paid": "Paid",
    "overdue": "Overdue",
}

RECURRENCE_LABELS = {
    "none": "One-time",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
    "yearly_2": "Every 2 years",
    "custom": "Custom",
}

DOCUMENT_TYPE_LABELS = {
    "driving_licence": "Driving Licence",
    "passport": "Passport",
    "aadhaar": "Aadhaar",
    "pan": "PAN",
    "vehicle_insurance": "Vehicle Insurance",
    "health_insurance": "Health Insurance",
    "certificate": "Certificate",
    "warranty": "Warranty",
    "other": "Other",
}

DOCUMENT_STATUS_LABELS = {
    "expired": "Expired",
    "expiring_soon": "Expiring Soon",
    "valid": "Valid",
}

DOSE_STATUS_LABELS = {
    "pending": "Pending",
    "taken": "Taken",
    "skipped": "Skipped",
}

DOSAGE_UNIT_LABELS = {
    "mg": "mg",
    "g": "g",
    "ml": "ml",
    "tablet": "tablet",
    "tablets": "tablets",
    "capsule": "capsule",
    "capsules": "capsules",
    "drop": "drop",
    "drops": "drops",
    "IU": "IU",
    "unit": "unit",
}

# Which colour / icon each module uses. The frontend mirrors these.
MODULE_KEYS = ("billbell", "dateguard", "dosenote", "aquahabit")

__all__ = [
    "BILL_CATEGORIES",
    "BILL_STATUSES",
    "RECURRENCE_INTERVALS",
    "SUPPORTED_CURRENCIES",
    "SUPPORTED_THEMES",
    "DOCUMENT_TYPES",
    "DOCUMENT_STATUSES",
    "DOSE_STATUSES",
    "DOSAGE_UNITS",
    "BILL_CATEGORY_LABELS",
    "BILL_STATUS_LABELS",
    "RECURRENCE_LABELS",
    "DOCUMENT_TYPE_LABELS",
    "DOCUMENT_STATUS_LABELS",
    "DOSE_STATUS_LABELS",
    "DOSAGE_UNIT_LABELS",
    "MODULE_KEYS",
]