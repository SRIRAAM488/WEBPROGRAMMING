"""Dashboard aggregation.

Every number the dashboard shows is computed here from real queries against the
SQLite database. Nothing on this page is hard-coded or faked.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.bill import Bill
from app.models.document import Document
from app.models.hydration import WaterIntakeRecord
from app.models.medication import DoseLog, MedicationSchedule
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
from app.services import bill_service, document_service, hydration_service
from app.services.medication_service import daily_adherence_series, expected_times_for_day
from app.services.reminder_service import reminder_summary
from app.services.settings_service import get_app_settings
from app.utils.constants import BILL_CATEGORY_LABELS
from app.utils.dates import as_utc, combine, local_now, local_today, week_start


def greeting_for(moment: datetime) -> str:
    """'Good morning!' based on the hour of the client's local clock."""
    hour = moment.hour
    if hour < 12:
        return "Good morning!"
    if hour < 17:
        return "Good afternoon!"
    return "Good evening!"


def _medication_dashboard(db: Session, today: date, tz_offset: int) -> MedicationDashboardSummary:
    """Active schedule count, today's taken/pending doses, next dose."""
    settings = get_app_settings(db)
    grace = settings.dose_grace_minutes

    schedules = db.execute(
        select(MedicationSchedule).options(selectinload(MedicationSchedule.schedule_times))
    ).scalars().unique().all()

    active = [s for s in schedules if s.is_active_on(today)]
    now_local = local_now()

    total = taken = pending = missed = 0
    next_time: datetime | None = None
    next_medication: str | None = None

    for schedule in active:
        for scheduled_time in expected_times_for_day(schedule, today):
            total += 1
            # combine() gives a UTC-aware moment we can safely compare with now.
            due = combine(today, scheduled_time)

            dose = db.scalar(
                select(DoseLog).where(
                    DoseLog.medication_schedule_id == schedule.id,
                    DoseLog.scheduled_date == today,
                    DoseLog.scheduled_time == scheduled_time,
                )
            )

            if dose is not None and dose.status == "taken":
                taken += 1
                continue
            if dose is not None and dose.status == "skipped":
                continue

            pending += 1
            if now_local > due + timedelta(minutes=grace):
                missed += 1

            if due >= now_local and (next_time is None or due < next_time):
                next_time = due
                next_medication = schedule.medication_name

    completion = round((taken / total) * 100) if total else 0

    return MedicationDashboardSummary(
        active_schedules=len(active),
        total_schedules=len(schedules),
        doses_today_total=total,
        doses_taken_today=taken,
        doses_pending_today=pending,
        doses_missed_today=missed,
        completion_percent=completion,
        next_dose=next_time.strftime("%H:%M") if next_time else None,
        next_dose_medication=next_medication,
    )


def _hydration_dashboard(db: Session, today: date, tz_offset: int) -> HydrationDashboardSummary:
    """Today's intake, goal, percentage and a 7-day average."""
    summary = hydration_service.today_summary(db, tz_offset)
    week = hydration_service.weekly_summary(db, tz_offset, days=7)

    return HydrationDashboardSummary(
        consumed_today_ml=summary.total_ml,
        daily_goal_ml=summary.goal_ml,
        remaining_ml=summary.remaining_ml,
        percent_complete=summary.percent_complete,
        goal_reached=summary.goal_reached,
        average_last_7_days_ml=week.average_ml,
    )


def build_summary(db: Session, tz_offset: int = 0) -> DashboardSummary:
    """GET /api/dashboard/summary - the four module cards in one payload."""
    today = local_today(tz_offset)
    now_local = local_now()
    reminders = reminder_summary(db, tz_offset)

    return DashboardSummary(
        generated_at=now_local,
        today=today,
        greeting_name=greeting_for(now_local),
        bills=bill_service.bill_summary(db, tz_offset),
        documents=document_service.document_summary(db, tz_offset),
        medications=_medication_dashboard(db, today, tz_offset),
        hydration=_hydration_dashboard(db, today, tz_offset),
        total_pending_reminders=reminders.total,
        overdue_reminders=reminders.overdue,
    )


def build_charts(db: Session, tz_offset: int = 0) -> DashboardCharts:
    """GET /api/dashboard/charts - every chart's data, from the database.

    Both weekly charts use a rolling 7-day window ending today, so there are
    always exactly seven bars even at the start or end of a calendar week.
    """
    today = local_today(tz_offset)
    window_start = today - timedelta(days=6)
    week_begin, week_end = window_start, today

    hydration_weekly = [
        HydrationChartPoint(
            date=point.date,
            label=point.label,
            total_ml=point.total_ml,
            goal_ml=point.goal_ml,
            percent_complete=point.percent_complete,
            goal_reached=point.goal_reached,
        )
        for point in hydration_service._build_series(
            db, week_begin, week_end, hydration_service.get_hydration_settings(db).daily_goal_ml
        )
    ]

    settings = get_app_settings(db)
    adherence = daily_adherence_series(
        db, week_begin, week_end, tz_offset, settings.dose_grace_minutes
    )
    medication_weekly = [
        MedicationChartPoint(
            date=point.date,
            label=point.label,
            scheduled=point.scheduled,
            taken=point.taken,
            skipped=point.skipped,
            missed=point.missed,
            adherence_percent=point.adherence_percent,
        )
        for point in adherence
    ]

    bills = db.execute(select(Bill)).scalars().all()
    total_paid = sum((b.amount for b in bills if b.status == "paid"), Decimal("0.00"))
    total_unpaid = sum(
        (b.amount for b in bills if b.status in ("unpaid", "overdue")), Decimal("0.00")
    )

    category_totals: dict[str, tuple[int, Decimal]] = {}
    for bill in bills:
        count, amount = category_totals.get(bill.category, (0, Decimal("0.00")))
        category_totals[bill.category] = (count + 1, amount + bill.amount)

    by_category = [
        BillCategorySlice(
            key=key,
            label=BILL_CATEGORY_LABELS.get(key, key.title()),
            count=count,
            amount=float(amount),
        )
        for key, (count, amount) in sorted(
            category_totals.items(), key=lambda pair: pair[1][1], reverse=True
        )
    ]

    documents = db.execute(select(Document)).scalars().all()
    buckets = {"expired": 0, "in_7_days": 0, "in_30_days": 0, "later": 0}
    for doc in documents:
        remaining = (doc.expiry_date - today).days
        if remaining < 0:
            buckets["expired"] += 1
        elif remaining <= 7:
            buckets["in_7_days"] += 1
        elif remaining <= 30:
            buckets["in_30_days"] += 1
        else:
            buckets["later"] += 1

    return DashboardCharts(
        generated_at=local_now(),
        hydration_weekly=hydration_weekly,
        medication_weekly=medication_weekly,
        bills_paid_vs_unpaid={
            "paid": float(total_paid),
            "unpaid": float(total_unpaid),
        },
        bills_by_category=by_category,
        document_expiry_buckets=buckets,
    )


def build_activity(db: Session, limit: int = 12, tz_offset: int = 0) -> ActivityResponse:
    """GET /api/dashboard/activity - a real feed built from stored timestamps.

    Rather than adding an activity table, this reads the ``created_at`` /
    ``payment_date`` / ``taken_at`` columns that already exist on the real
    records, so the feed can never disagree with the data.
    """
    items: list[ActivityItem] = []

    # Bills
    for bill in db.execute(select(Bill).order_by(Bill.updated_at.desc())).scalars().all():
        if bill.payment_date:
            # Build the timestamp from the real payment date, not "now".
            paid_at = combine(bill.payment_date, time.min)
            items.append(
                ActivityItem(
                    id=f"activity:bill-paid:{bill.id}",
                    module="billbell",
                    action="Bill paid",
                    title=f"Paid {bill.bill_name}",
                    detail=f"{bill.currency} {bill.amount} · paid {bill.payment_date.isoformat()}",
                    occurred_at=paid_at,
                    link=f"/bills?bill={bill.id}",
                    accent="coral",
                )
            )
        items.append(
            ActivityItem(
                id=f"activity:bill-created:{bill.id}",
                module="billbell",
                action="Bill added",
                title=f"Added {bill.bill_name}",
                detail=f"{bill.currency} {bill.amount} · due {bill.due_date.isoformat()}",
                # created_at comes back naive from SQLite -> normalise it.
                occurred_at=as_utc(bill.created_at),
                link=f"/bills?bill={bill.id}",
                accent="coral",
            )
        )

    # Documents
    for doc in db.execute(select(Document).order_by(Document.updated_at.desc())).scalars().all():
        items.append(
            ActivityItem(
                id=f"activity:document-updated:{doc.id}",
                module="dateguard",
                action="Document tracked",
                title=f"{doc.document_name}",
                detail=f"Expires {doc.expiry_date.isoformat()}",
                occurred_at=as_utc(doc.updated_at),
                link=f"/documents?document={doc.id}",
                accent="amber",
            )
        )

    # Dose logs that were actually marked taken
    taken_doses = (
        db.execute(
            select(DoseLog, MedicationSchedule.medication_name)
            .join(MedicationSchedule, DoseLog.medication_schedule_id == MedicationSchedule.id)
            .where(DoseLog.status == "taken")
            .order_by(DoseLog.taken_at.desc())
            .limit(limit)
        )
        .all()
    )
    for dose, medication_name in taken_doses:
        items.append(
            ActivityItem(
                id=f"activity:dose-taken:{dose.id}",
                module="dosenote",
                action="Dose marked taken",
                title=f"{medication_name}",
                detail=f"{dose.scheduled_time.strftime('%H:%M')} · {dose.scheduled_date.isoformat()}",
                occurred_at=as_utc(dose.taken_at or dose.updated_at),
                link="/medications",
                accent="violet",
            )
        )

    # Water intake
    intakes = (
        db.execute(select(WaterIntakeRecord).order_by(WaterIntakeRecord.consumed_at.desc()))
        .scalars()
        .all()
    )
    for entry in intakes:
        items.append(
            ActivityItem(
                id=f"activity:water:{entry.id}",
                module="aquahabit",
                action="Water logged",
                title=f"+{entry.amount_ml} ml",
                detail=entry.notes or entry.entry_date.isoformat(),
                occurred_at=as_utc(entry.consumed_at),
                link="/hydration",
                accent="turquoise",
            )
        )

    # Newest first, then trim.
    items.sort(key=lambda item: item.occurred_at, reverse=True)
    trimmed = items[:limit]

    return ActivityResponse(
        generated_at=local_now(),
        total=len(trimmed),
        items=trimmed,
    )