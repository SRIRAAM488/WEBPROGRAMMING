"""Dashboard endpoints: summary cards, chart data and recent activity."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_tz_offset
from app.schemas.dashboard import ActivityResponse, DashboardCharts, DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary, summary="All four module cards")
def get_summary(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DashboardSummary:
    """One request powers the four overview cards. Every value is computed from
    a real database query inside the service layer."""
    return dashboard_service.build_summary(db, tz_offset)


@router.get("/charts", response_model=DashboardCharts, summary="Data for every dashboard chart")
def get_charts(
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> DashboardCharts:
    """Weekly hydration bars, weekly medication adherence bars, paid-vs-unpaid
    totals, bills by category and document expiry buckets."""
    return dashboard_service.build_charts(db, tz_offset)


@router.get("/activity", response_model=ActivityResponse, summary="Recent activity feed")
def get_activity(
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    tz_offset: int = Depends(get_tz_offset),
) -> ActivityResponse:
    """Built from the timestamps on real records (created_at, payment_date,
    taken_at, consumed_at) so it can never disagree with the module data."""
    return dashboard_service.build_activity(db, limit, tz_offset)