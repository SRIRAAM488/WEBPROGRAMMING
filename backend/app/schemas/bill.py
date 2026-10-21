"""Pydantic request / response schemas for BillBell."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.bill import BILL_CATEGORIES, BILL_STATUSES, RECURRENCE_INTERVALS, SUPPORTED_CURRENCIES
from app.utils.constants import BILL_CATEGORY_LABELS, BILL_STATUS_LABELS, RECURRENCE_LABELS


# --- Reusable validators (plain functions so create + update can share them) ---


def normalise_text(value: str | None) -> str | None:
    """Trim whitespace and turn an empty string into None."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalise_choice(value: str | None, allowed, field_name: str) -> str | None:
    """Lower-case a value and check it against an allowed set."""
    if value is None:
        return None
    normalised = value.strip().lower()
    if normalised not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return normalised


def normalise_currency(value: str | None) -> str | None:
    """Upper-case a 3-letter currency code and check that we support it."""
    if value is None:
        return None
    code = value.strip().upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"currency must be one of: {', '.join(SUPPORTED_CURRENCIES)}")
    return code


class BillBase(BaseModel):
    """Fields shared by create and update payloads."""

    bill_name: str = Field(..., min_length=1, max_length=120, examples=["Electricity Bill"])
    category: str = Field("other", examples=["electricity"])
    provider: str | None = Field(None, max_length=120, examples=["BESCOM"])
    amount: Decimal = Field(..., gt=0, le=10_000_000, examples=[1250.00])
    currency: str = Field("INR", examples=["INR"])
    due_date: date
    status: str = Field("unpaid", examples=["unpaid"])
    payment_date: date | None = None
    recurring: bool = False
    recurrence_interval: str = Field("none", examples=["monthly"])
    notes: str | None = Field(None, max_length=1000)

    @field_validator("bill_name", "provider", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("category")
    @classmethod
    def _check_category(cls, value: str) -> str:
        return normalise_choice(value, BILL_CATEGORIES, "category")

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str) -> str:
        return normalise_choice(value, BILL_STATUSES, "status")

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, value: str) -> str:
        return normalise_currency(value)

    @field_validator("recurrence_interval")
    @classmethod
    def _check_recurrence(cls, value: str) -> str:
        return normalise_choice(value, RECURRENCE_INTERVALS, "recurrence_interval")

    @field_validator("due_date")
    @classmethod
    def _check_due_date(cls, value: date) -> date:
        if value.year < 1970 or value.year > 2200:
            raise ValueError("due_date must be a realistic date (1970-2200)")
        return value


class BillCreate(BillBase):
    """POST /api/bills payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bill_name": "Electricity Bill",
                "category": "electricity",
                "provider": "BESCOM",
                "amount": "1250.00",
                "currency": "INR",
                "due_date": "2026-11-05",
                "recurring": True,
                "recurrence_interval": "monthly",
            }
        }
    )


class BillUpdate(BaseModel):
    """PATCH /api/bills/{id} - every field optional (partial update)."""

    bill_name: str | None = Field(None, min_length=1, max_length=120)
    category: str | None = None
    provider: str | None = Field(None, max_length=120)
    amount: Decimal | None = Field(None, gt=0, le=10_000_000)
    currency: str | None = None
    due_date: date | None = None
    status: str | None = None
    payment_date: date | None = None
    recurring: bool | None = None
    recurrence_interval: str | None = None
    notes: str | None = Field(None, max_length=1000)

    @field_validator("bill_name", "provider", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("category")
    @classmethod
    def _check_category(cls, value: str | None) -> str | None:
        return normalise_choice(value, BILL_CATEGORIES, "category")

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str | None) -> str | None:
        return normalise_choice(value, BILL_STATUSES, "status")

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, value: str | None) -> str | None:
        return normalise_currency(value)

    @field_validator("recurrence_interval")
    @classmethod
    def _check_recurrence(cls, value: str | None) -> str | None:
        return normalise_choice(value, RECURRENCE_INTERVALS, "recurrence_interval")


class BillResponse(BillBase):
    """A bill as returned by the API, with derived fields added."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    # Derived, not stored - computed fresh on every response.
    days_until_due: int = 0
    is_overdue: bool = False
    category_label: str = ""
    status_label: str = ""
    recurrence_label: str = ""
    next_cycle_due_date: date | None = None


class BillSummary(BaseModel):
    """Aggregated BillBell numbers used by the dashboard."""

    total_bills: int = 0
    unpaid_count: int = 0
    paid_count: int = 0
    overdue_count: int = 0
    total_unpaid_amount: Decimal = Decimal("0.00")
    total_paid_this_month: Decimal = Decimal("0.00")
    currency: str = "INR"
    next_due_date: date | None = None
    next_due_bill_name: str | None = None
    due_soon_count: int = 0
    recurring_due_count: int = 0
    by_category: dict[str, int] = {}


class BillPayRequest(BaseModel):
    """POST /api/bills/{id}/pay payload."""

    payment_date: date | None = Field(None, description="Defaults to today if omitted.")
    mark_next_cycle: bool = Field(
        False,
        description=(
            "For a recurring bill, optionally create the next occurrence. The "
            "service checks for an existing next-cycle bill first so running "
            "this twice cannot create duplicates."
        ),
    )
    notes: str | None = Field(None, max_length=1000)


class BillListResponse(BaseModel):
    """Paginated list envelope used by list endpoints."""

    items: list[BillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


BILL_LABELS = {
    "categories": BILL_CATEGORY_LABELS,
    "statuses": BILL_STATUS_LABELS,
    "recurrences": RECURRENCE_LABELS,
}