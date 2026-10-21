"""Unified reminder centre.

How reminders work
------------------
Reminders are **derived, never stored**. Every call rebuilds the list from the
current state of bills, documents, medication schedules and hydration. That
means a reminder can never disagree with the record it came from, and there is
no separate reminder table to keep in sync.

Each reminder gets a stable ``id`` made from the real-world event it describes
(for example ``bill:12:2026-11-05``). Sorting by ``id`` after sorting by due
date guarantees the same event never appears twice in one response.

Reminder centre scope: these are **in-app reminders**. They work while the
DailyFlow page is open. DailyFlow does not send push notifications, email or
SMS, and nothing runs in the background after the browser tab is closed.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.bill import Bill
from app.models.document import Document
from app.models.medication import DoseLog, MedicationSchedule
from app.schemas.reminder import ReminderGroup, ReminderItem, ReminderListResponse, ReminderSummary
from app.services.hydration_service import today_summary
from app.services.medication_service import expected_times_for_day, generate_doses_for_day
from app.services.settings_service import get_app_settings, get_hydration_settings
from app.utils.dates import combine, days_between, local_now, local_today

UPCOMING_WINDOW_DAYS = 14
DUE_SOON_DAYS = 3


def _sort_key(item: ReminderItem):
    """Sort by due moment, then by priority, then by id (which kills duplicates)."""
    priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    return (
        item.due_at or datetime.max,
        priority_rank.get(item.priority, 9),
        item.id,
    )


def _bucket_for(days_remaining: int) -> str:
    if days_remaining < 0:
        return "overdue"
    if days_remaining == 0:
        return "today"
    return "upcoming"


def build_bill_reminders(db: Session, today: date) -> list[ReminderItem]:
    """Bill overdue + bill due soon."""
    settings = get_app_settings(db)
    lead_days = max(settings.bill_reminder_days_before, DUE_SOON_DAYS)

    bills = db.execute(
        select(Bill).where(Bill.status.in_(("unpaid", "overdue")))
    ).scalars().all()

    reminders: list[ReminderItem] = []
    for bill in bills:
        remaining = days_between(today, bill.due_date)
        if remaining > lead_days:
            continue

        overdue = remaining < 0
        if overdue:
            title = f"{bill.bill_name} is overdue"
            description = (
                f"Was due {abs(remaining)} day(s) ago"
                f"{f' to {bill.provider}' if bill.provider else ''}."
            )
            priority = "urgent"
            category = "bill_overdue"
        elif remaining == 0:
            title = f"{bill.bill_name} is due today"
            description = "Pay today to avoid late fees."
            priority = "high"
            category = "bill_due"
        else:
            title = f"{bill.bill_name} due in {remaining} day(s)"
            description = (
                f"Scheduled for {bill.due_date.isoformat()}"
                f"{f' from {bill.provider}' if bill.provider else ''}."
            )
            priority = "high" if remaining <= 1 else "medium"
            category = "bill_due"

        reminders.append(
            ReminderItem(
                id=f"bill:{bill.id}:{bill.due_date.isoformat()}",
                module="billbell",
                category=category,
                priority=priority,
                bucket=_bucket_for(remaining),
                title=title,
                description=description,
                due_date=bill.due_date,
                due_at=combine(bill.due_date, datetime.min.time()),
                link=f"/bills?bill={bill.id}",
                reference_id=bill.id,
                amount_label=f"{bill.currency} {bill.amount}",
            )
        )
    return reminders


def build_document_reminders(db: Session, today: date) -> list[ReminderItem]:
    """Document expiring soon + documents already expired."""
    documents = db.execute(
        select(Document).where(Document.archived.is_(False))
    ).scalars().all()

    reminders: list[ReminderItem] = []
    for doc in documents:
        remaining = days_between(today, doc.expiry_date)
        expired = remaining < 0

        if expired:
            category, priority = "document_expired", "urgent"
            title = f"{doc.document_name} has expired"
            description = (
                f"Expired {abs(remaining)} day(s) ago on {doc.expiry_date.isoformat()}. "
                "Renew it as soon as possible."
            )
            bucket = "overdue"
        elif remaining <= max(doc.reminder_days_before, 0):
            category = "document_expiring"
            priority = "high" if remaining <= 7 else "medium"
            title = f"{doc.document_name} expires in {remaining} day(s)"
            description = (
                f"Valid until {doc.expiry_date.isoformat()}"
                f"{f' · issued by {doc.issuing_authority}' if doc.issuing_authority else ''}."
            )
            bucket = "today" if remaining == 0 else "upcoming"
        else:
            continue  # outside this document's own reminder window

        reminders.append(
            ReminderItem(
                id=f"document:{doc.id}:{doc.expiry_date.isoformat()}",
                module="dateguard",
                category=category,
                priority=priority,
                bucket=bucket,
                title=title,
                description=description,
                due_date=doc.expiry_date,
                due_at=combine(doc.expiry_date, datetime.min.time()),
                link=f"/documents?document={doc.id}",
                reference_id=doc.id,
            )
        )
    return reminders


def build_medication_reminders(db: Session, today: date, tz_offset: int = 0) -> list[ReminderItem]:
    """Doses due today that are still pending, plus missed ones.

    Uses the stored dose logs (which are generated as 'pending'), so a dose the
    user marked 'taken' never shows up as a reminder again.
    """
    settings = get_app_settings(db)
    grace = settings.dose_grace_minutes
    now_local = local_now()
    horizon_end = today + timedelta(days=1)

    schedules = {
        s.id: s
        for s in db.execute(
            select(MedicationSchedule).options(selectinload(MedicationSchedule.schedule_times))
        )
        .scalars()
        .unique()
        .all()
    }
    if not schedules:
        return []

    # Materialise today's expected doses first, otherwise a schedule the user has
    # never opened would produce no reminders at all. Generation only ever
    # creates 'pending' logs, so this is safe to call on every request.
    generate_doses_for_day(db, today, grace_minutes=grace, flush_only=False)

    doses = db.execute(
        select(DoseLog).where(
            DoseLog.scheduled_date >= today,
            DoseLog.scheduled_date <= horizon_end,
            DoseLog.status == "pending",
        )
    ).scalars().all()

    reminders: list[ReminderItem] = []
    for dose in doses:
        schedule = schedules.get(dose.medication_schedule_id)
        if schedule is None or not schedule.is_active_on(dose.scheduled_date):
            continue

        due = combine(dose.scheduled_date, dose.scheduled_time)
        is_missed = now_local > due + timedelta(minutes=grace)
        is_upcoming = now_local < due - timedelta(minutes=grace)

        if is_missed:
            category, priority = "dose_missed", "high"
            title = f"Missed dose: {schedule.medication_name}"
            description = (
                f"{dose.scheduled_time.strftime('%H:%M')} dose "
                f"({schedule.dosage} {schedule.dosage_unit}) is still pending."
            )
            bucket = "overdue"
        elif is_upcoming:
            # Only remind within the reminder window so we do not spam all day.
            if (due - combine(today, datetime.min.time())) > timedelta(hours=6):
                continue
            category, priority = "dose_due", "medium"
            title = f"Upcoming dose: {schedule.medication_name}"
            description = f"Scheduled for {dose.scheduled_time.strftime('%H:%M')}."
            bucket = "today"
        else:
            category, priority = "dose_due", "high"
            title = f"Time for {schedule.medication_name}"
            description = (
                f"Take {schedule.dosage} {schedule.dosage_unit}"
                f"{f' — {schedule.instructions}' if schedule.instructions else ''}."
            )
            bucket = "today"

        reminders.append(
            ReminderItem(
                id=(
                    f"dose:{dose.medication_schedule_id}:"
                    f"{dose.scheduled_date.isoformat()}:{dose.scheduled_time.strftime('%H%M')}"
                ),
                module="dosenote",
                category=category,
                priority=priority,
                bucket=bucket,
                title=title,
                description=description,
                due_date=dose.scheduled_date,
                due_at=due,
                link=f"/medications?dose={dose.id}",
                reference_id=dose.id,
            )
        )
    return reminders


def build_hydration_reminder(db: Session, today: date, tz_offset: int = 0) -> list[ReminderItem]:
    """One gentle nudge when the day is still far from the hydration goal.

    Deliberately quiet by default:
      * not shown at all if the user has already reached the goal,
      * not shown when nothing has been logged yet (the dashboard card already
        shows 0% clearly, so a reminder would just be noise),
      * not shown before midday, so it cannot nag first thing in the morning.
    """
    hydration_settings = get_hydration_settings(db)
    if not hydration_settings.reminder_enabled:
        return []

    app_settings = get_app_settings(db)
    summary = today_summary(db, tz_offset)

    if summary.goal_ml <= 0 or summary.goal_reached:
        return []
    if summary.total_ml <= 0:
        return []

    threshold = (summary.goal_ml * app_settings.hydration_reminder_percent) / 100
    if summary.total_ml >= threshold:
        return []
    if local_now().hour < 12:
        return []

    remaining = max(0, summary.goal_ml - summary.total_ml)
    return [
        ReminderItem(
            id=f"hydration:{today.isoformat()}",
            module="aquahabit",
            category="hydration_progress",
            priority="low",
            bucket="today",
            title=f"Log your water — {remaining} ml to reach today's goal",
            description=(
                f"Consumed {summary.total_ml} ml of {summary.goal_ml} ml so far. "
                "AquaHabit goals are a personal preference, not medical advice."
            ),
            due_date=today,
            due_at=combine(today, datetime.min.time()),
            link="/hydration",
            is_actionable=True,
            amount_label=f"{summary.total_ml} / {summary.goal_ml} ml",
        )
    ]


def build_all_reminders(
    db: Session,
    *,
    modules: list[str] | None = None,
    tz_offset: int = 0,
    limit: int | None = None,
) -> list[ReminderItem]:
    """Generate every reminder from current database state."""
    today = local_today(tz_offset)

    builders = {
        "billbell": lambda: build_bill_reminders(db, today),
        "dateguard": lambda: build_document_reminders(db, today),
        "dosenote": lambda: build_medication_reminders(db, today, tz_offset),
        "aquahabit": lambda: build_hydration_reminder(db, today, tz_offset),
    }

    selected = modules or list(builders.keys())
    collected: list[ReminderItem] = []
    for name in selected:
        builder = builders.get(name)
        if builder is None:
            continue
        collected.extend(builder())

    # De-duplicate on the stable id, then sort.
    unique: dict[str, ReminderItem] = {item.id: item for item in collected}
    ordered = sorted(unique.values(), key=_sort_key)

    return ordered[:limit] if limit else ordered


def reminder_list(
    db: Session,
    *,
    modules: list[str] | None = None,
    categories: list[str] | None = None,
    priorities: list[str] | None = None,
    buckets: list[str] | None = None,
    limit: int = 200,
    tz_offset: int = 0,
) -> ReminderListResponse:
    """Full reminder centre payload, grouped into overdue / today / upcoming."""
    items = build_all_reminders(db, modules=modules, tz_offset=tz_offset, limit=limit)

    if categories:
        wanted = set(categories)
        items = [i for i in items if i.category in wanted]
    if priorities:
        wanted = set(priorities)
        items = [i for i in items if i.priority in wanted]
    if buckets:
        wanted = set(buckets)
        items = [i for i in items if i.bucket in wanted]

    # Never show the same real-world event twice.
    deduped: dict[str, ReminderItem] = {item.id: item for item in items}
    items = sorted(deduped.values(), key=_sort_key)

    groups = ReminderGroup(
        overdue=[i for i in items if i.bucket == "overdue"],
        today=[i for i in items if i.bucket == "today"],
        upcoming=[i for i in items if i.bucket == "upcoming"],
    )

    return ReminderListResponse(
        generated_at=local_now(),
        total=len(items),
        overdue_count=len(groups.overdue),
        today_count=len(groups.today),
        upcoming_count=len(groups.upcoming),
        modules=["billbell", "dateguard", "dosenote", "aquahabit"],
        groups=groups,
        items=items,
    )


def reminder_summary(db: Session, tz_offset: int = 0) -> ReminderSummary:
    """Small counts for the sidebar badge - no grouping needed."""
    items = build_all_reminders(db, tz_offset=tz_offset)

    by_module: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for item in items:
        by_module[item.module] = by_module.get(item.module, 0) + 1
        by_priority[item.priority] = by_priority.get(item.priority, 0) + 1

    rank = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
    highest = "low"
    if items:
        highest = max((i.priority for i in items), key=lambda p: rank.get(p, 0))

    return ReminderSummary(
        total=len(items),
        overdue=len([i for i in items if i.bucket == "overdue"]),
        today=len([i for i in items if i.bucket == "today"]),
        upcoming=len([i for i in items if i.bucket == "upcoming"]),
        by_module=by_module,
        by_priority=by_priority,
        highest_priority=highest,
    )


def reminder_link_for(record_type: str, record_id: int) -> str:
    """Frontend route for a module record (used when jumping to a reminder)."""
    return {
        "bill": f"/bills?bill={record_id}",
        "document": f"/documents?document={record_id}",
        "dose": f"/medications?dose={record_id}",
        "hydration": "/hydration",
    }.get(record_type, "/")