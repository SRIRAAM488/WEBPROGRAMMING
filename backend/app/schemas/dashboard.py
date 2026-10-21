"""Schemas for the aggregated dashboard."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.bill import BillSummary
from app.schemas.document import DocumentSummary


class MedicationDashboardSummary(BaseModel):
    """DoseNote numbers for the dashboard card."""

    active_schedules: int = 0
    total_schedules: int = 0
    doses_today_total: int = 0
    doses_taken_today: int = 0
    doses_pending_today: int = 0
    doses_missed_today: int = 0
    completion_percent: int = 0
    next_dose: str | None = None
    next_dose_medication: str | None = None


class HydrationDashboardSummary(BaseModel):
    """AquaHabit numbers for the dashboard card."""

    consumed_today_ml: int = 0
    daily_goal_ml: int = 0
    remaining_ml: int = 0
    percent_complete: int = 0
    goal_reached: bool = False
    average_last_7_days_ml: int = 0


class DashboardSummary(BaseModel):
    """GET /api/dashboard/summary - every number comes from the database."""

    generated_at: datetime
    today: date
    greeting_name: str = "there"

    bills: BillSummary
    documents: DocumentSummary
    medications: MedicationDashboardSummary
    hydration: HydrationDashboardSummary

    total_pending_reminders: int = 0
    overdue_reminders: int = 0


class HydrationChartPoint(BaseModel):
    """One bar in the weekly hydration chart."""

    date: date
    label: str
    total_ml: int = 0
    goal_ml: int = 0
    percent_complete: int = 0
    goal_reached: bool = False


class MedicationChartPoint(BaseModel):
    """One bar in the weekly adherence chart."""

    date: date
    label: str
    scheduled: int = 0
    taken: int = 0
    skipped: int = 0
    missed: int = 0
    adherence_percent: int = 0


class BillCategorySlice(BaseModel):
    label: str
    key: str
    count: int = 0
    amount: float = 0.0


class DashboardCharts(BaseModel):
    """GET /api/dashboard/charts - data for every chart on the dashboard."""

    generated_at: datetime
    hydration_weekly: list[HydrationChartPoint] = Field(default_factory=list)
    medication_weekly: list[MedicationChartPoint] = Field(default_factory=list)
    bills_paid_vs_unpaid: dict[str, float] = Field(default_factory=dict)
    bills_by_category: list[BillCategorySlice] = Field(default_factory=list)
    document_expiry_buckets: dict[str, int] = Field(default_factory=dict)


class ActivityItem(BaseModel):
    """One real row from the database, shown in the Recent Activity feed."""

    id: str
    module: str
    action: str
    title: str
    detail: str | None = None
    occurred_at: datetime
    link: str
    accent: str = "primary"


class ActivityResponse(BaseModel):
    """GET /api/dashboard/activity"""

    generated_at: datetime
    total: int = 0
    items: list[ActivityItem] = Field(default_factory=list)