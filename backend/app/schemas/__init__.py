"""All Pydantic schemas for DailyFlow."""

from app.schemas.bill import (
    BillCreate,
    BillListResponse,
    BillPayRequest,
    BillResponse,
    BillSummary,
    BillUpdate,
)
from app.schemas.dashboard import (
    ActivityItem,
    ActivityResponse,
    BillCategorySlice,
    DashboardCharts,
    DashboardSummary,
    HydrationChartPoint,
    HydrationDashboardSummary,
    MedicationChartPoint,
    MedicationDashboardSummary,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentRenewRequest,
    DocumentRenewalRecord,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
)
from app.schemas.hydration import (
    HydrationDaySummary,
    HydrationHistoryResponse,
    HydrationMonthlyResponse,
    HydrationSettingsResponse,
    HydrationSettingsUpdate,
    HydrationTodayResponse,
    HydrationWeeklyResponse,
    WaterIntakeCreate,
    WaterIntakeResponse,
    WaterIntakeUpdate,
)
from app.schemas.medication import (
    DailyAdherence,
    DoseLogCreate,
    DoseLogResponse,
    DoseLogUpdate,
    MedicationAdherenceResponse,
    MedicationHistoryResponse,
    MedicationScheduleCreate,
    MedicationScheduleResponse,
    MedicationScheduleUpdate,
    TodayMedicationResponse,
)
from app.schemas.reminder import (
    ReminderGroup,
    ReminderItem,
    ReminderListResponse,
    ReminderSummary,
)
from app.schemas.settings import (
    AppSettingsMeta,
    AppSettingsResponse,
    AppSettingsUpdate,
    HealthResponse,
)

__all__ = [
    # bills
    "BillCreate", "BillUpdate", "BillResponse", "BillSummary", "BillPayRequest",
    "BillListResponse",
    # documents
    "DocumentCreate", "DocumentUpdate", "DocumentResponse", "DocumentSummary",
    "DocumentRenewRequest", "DocumentRenewalRecord", "DocumentListResponse",
    # medications
    "MedicationScheduleCreate", "MedicationScheduleUpdate", "MedicationScheduleResponse",
    "DoseLogCreate", "DoseLogUpdate", "DoseLogResponse", "TodayMedicationResponse",
    "MedicationHistoryResponse", "MedicationAdherenceResponse", "DailyAdherence",
    # hydration
    "HydrationSettingsResponse", "HydrationSettingsUpdate", "WaterIntakeCreate",
    "WaterIntakeUpdate", "WaterIntakeResponse", "HydrationTodayResponse",
    "HydrationHistoryResponse", "HydrationWeeklyResponse", "HydrationMonthlyResponse",
    "HydrationDaySummary",
    # dashboard
    "DashboardSummary", "DashboardCharts", "ActivityResponse", "ActivityItem",
    "HydrationChartPoint", "MedicationChartPoint", "MedicationDashboardSummary",
    "HydrationDashboardSummary", "BillCategorySlice",
    # reminders
    "ReminderItem", "ReminderListResponse", "ReminderSummary", "ReminderGroup",
    # settings
    "AppSettingsResponse", "AppSettingsUpdate", "AppSettingsMeta", "HealthResponse",
]