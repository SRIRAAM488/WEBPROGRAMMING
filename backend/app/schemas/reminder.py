"""Schemas for the unified reminder centre."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

REMINDER_CATEGORIES = (
    "bill_overdue",
    "bill_due",
    "document_expired",
    "document_expiring",
    "dose_due",
    "dose_missed",
    "hydration_progress",
)

PRIORITIES = ("low", "medium", "high", "urgent")
REMINDER_BUCKETS = ("overdue", "today", "upcoming", "later")


class ReminderItem(BaseModel):
    """A single reminder generated from the current database state.

    Reminders are *derived*, not stored. Each one carries a stable ``source_key``
    so the same real-world event can never appear twice.
    """

    id: str = Field(..., description="Stable unique key, e.g. 'bill:12:2026-11-05'.")
    module: str = Field(..., description="billbell | dateguard | dosenote | aquahabit")
    category: str
    priority: str = "medium"
    bucket: str = "upcoming"
    title: str
    description: str | None = None
    due_at: datetime | None = None
    due_date: date | None = None
    link: str = Field(..., description="Frontend route to open when clicked.")
    reference_id: int | None = None
    is_actionable: bool = True
    amount_label: str | None = None


class ReminderGroup(BaseModel):
    overdue: list[ReminderItem] = Field(default_factory=list)
    today: list[ReminderItem] = Field(default_factory=list)
    upcoming: list[ReminderItem] = Field(default_factory=list)


class ReminderListResponse(BaseModel):
    """GET /api/reminders"""

    generated_at: datetime
    total: int = 0
    overdue_count: int = 0
    today_count: int = 0
    upcoming_count: int = 0
    modules: list[str] = Field(default_factory=list)
    groups: ReminderGroup
    items: list[ReminderItem] = Field(default_factory=list)


class ReminderSummary(BaseModel):
    """GET /api/reminders/summary - small numbers for the sidebar badge."""

    total: int = 0
    overdue: int = 0
    today: int = 0
    upcoming: int = 0
    by_module: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    highest_priority: str = "low"


class ReminderFilterOptions(BaseModel):
    """Static option lists the reminder page needs for its filter chips."""

    categories: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    buckets: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="ignore")