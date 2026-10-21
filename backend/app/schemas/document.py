"""Pydantic request / response schemas for DateGuard."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.document import DOCUMENT_TYPES
from app.schemas.bill import normalise_choice, normalise_text


class DocumentBase(BaseModel):
    """Fields shared by create and update payloads."""

    document_name: str = Field(..., min_length=1, max_length=120, examples=["Driving Licence"])
    document_type: str = Field("other", examples=["driving_licence"])
    document_number: str | None = Field(
        None,
        max_length=60,
        description="Optional. Never returned unmasked in list/dashboard views.",
    )
    issue_date: date | None = None
    expiry_date: date
    issuing_authority: str | None = Field(None, max_length=120, examples=["RTO Bengaluru"])
    reminder_days_before: int = Field(15, ge=0, le=365, examples=[30])
    notes: str | None = Field(None, max_length=1000)
    archived: bool = False

    @field_validator("document_name", "document_number", "issuing_authority", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("document_type")
    @classmethod
    def _check_type(cls, value: str) -> str:
        return normalise_choice(value, DOCUMENT_TYPES, "document_type")

    @field_validator("expiry_date", "issue_date")
    @classmethod
    def _check_year(cls, value: date | None) -> date | None:
        if value is None:
            return None
        if value.year < 1970 or value.year > 2200:
            raise ValueError("dates must be within 1970-2200")
        return value


class DocumentCreate(DocumentBase):
    """POST /api/documents payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_name": "Vehicle Insurance",
                "document_type": "vehicle_insurance",
                "document_number": "POL-99887766",
                "issue_date": "2025-01-10",
                "expiry_date": "2027-01-10",
                "issuing_authority": "Demo Insurance Ltd",
                "reminder_days_before": 30,
            }
        }
    )


class DocumentUpdate(BaseModel):
    """PATCH /api/documents/{id} - every field optional."""

    document_name: str | None = Field(None, min_length=1, max_length=120)
    document_type: str | None = None
    document_number: str | None = Field(None, max_length=60)
    issue_date: date | None = None
    expiry_date: date | None = None
    issuing_authority: str | None = Field(None, max_length=120)
    reminder_days_before: int | None = Field(None, ge=0, le=365)
    notes: str | None = Field(None, max_length=1000)
    archived: bool | None = None

    @field_validator("document_name", "document_number", "issuing_authority", "notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return normalise_text(value)

    @field_validator("document_type")
    @classmethod
    def _check_type(cls, value: str | None) -> str | None:
        return normalise_choice(value, DOCUMENT_TYPES, "document_type")


class DocumentRenewRequest(BaseModel):
    """POST /api/documents/{id}/renew payload."""

    new_expiry_date: date
    issue_date: date | None = None
    document_number: str | None = Field(None, max_length=60)
    notes: str | None = Field(
        None, max_length=1000, description="Optional renewal note kept for history."
    )


class DocumentRenewalRecord(BaseModel):
    """One entry from the document's simple renewal history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_expiry_date: date
    new_expiry_date: date
    renewed_at: datetime
    notes: str | None = None


class DocumentResponse(DocumentBase):
    """A document as returned by the API, with derived expiry information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    # Derived from the current date every single time - never stored.
    status: str = "valid"
    status_label: str = ""
    days_remaining: int = 0
    is_expired: bool = False
    is_expiring_soon: bool = False
    document_type_label: str = ""
    masked_document_number: str | None = None
    renewals: list[DocumentRenewalRecord] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    """Aggregated DateGuard numbers used by the dashboard."""

    total_documents: int = 0
    active_documents: int = 0
    expired_count: int = 0
    expiring_in_7_days: int = 0
    expiring_in_15_days: int = 0
    expiring_in_30_days: int = 0
    next_expiry_date: date | None = None
    next_expiry_name: str | None = None
    by_type: dict[str, int] = {}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int