"""Seed realistic but FICTIONAL demo data into DailyFlow.

Run it with:   python -m scripts.seed_data

Important properties
--------------------
1. **Idempotent** - every insert checks for an existing row first, so running
   the script twice (or restarting the server) never duplicates demo data.
2. **Relative dates** - everything is computed from today's real date, so the
   demo always looks current no matter when it is run.
3. **Fictional** - no real names, numbers, accounts or medical details. The
   medication examples are placeholders the user is meant to edit; they are not
   medical recommendations.

To wipe the demo database and start fresh, delete ``backend/dailyflow.db`` and
run the two commands above again.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.bill import Bill
from app.models.document import Document
from app.models.hydration import WaterIntakeRecord
from app.models.medication import DoseLog, MedicationSchedule, MedicationScheduleTime
from app.services.settings_service import get_app_settings, get_hydration_settings


# --------------------------------------------------------------- BillBell demo

DEMO_BILLS = [
    # (name, category, provider, amount, due_in_days, status, recurring, interval, notes)
    ("Electricity Bill", "electricity", "BESCOM", "1250.00", 3, "unpaid", True, "monthly",
     "Demo record — switch off the appliance you are not using."),
    ("Internet Bill", "internet", "DemoNet Fiber", "799.00", 1, "unpaid", True, "monthly",
     "Demo record — broadband plan renewal."),
    ("Mobile Recharge", "mobile", "DemoMobile", "399.00", -2, "paid", False, "none",
     "Demo record — already paid."),
    ("House Rent", "rent", "Demo Property Manager", "15000.00", 9, "unpaid", True, "monthly",
     "Demo record — monthly rent."),
    ("Music Subscription", "subscription", "DemoTunes", "179.00", -5, "paid", True, "monthly",
     "Demo record — streaming subscription."),
    ("Course Fee", "education", "Demo Academy", "6500.00", 6, "unpaid", False, "none",
     "Demo record — certification course."),
]


def seed_bills(db, today: date) -> int:
    """Insert demo bills that do not already exist."""
    created = 0
    for name, category, provider, amount, due_offset, status, recurring, interval, notes in DEMO_BILLS:
        exists = db.scalar(
            select(func.count(Bill.id)).where(Bill.bill_name == name, Bill.provider == provider)
        )
        if exists:
            continue

        due_date = today + timedelta(days=due_offset)
        paid = status == "paid"

        db.add(
            Bill(
                bill_name=name,
                category=category,
                provider=provider,
                amount=amount,
                currency="INR",
                due_date=due_date,
                status=status,
                payment_date=(due_date - timedelta(days=1)) if paid else None,
                recurring=recurring,
                recurrence_interval=interval if recurring else "none",
                notes=notes,
            )
        )
        created += 1

    db.commit()
    return created


# -------------------------------------------------------------- DateGuard demo

DEMO_DOCUMENTS = [
    # (name, type, number, issue_offset, expiry_offset, authority, reminder_days, notes)
    ("Driving Licence", "driving_licence", "DL-DEMO-2024-8842", -700, 45,
     "Demo RTO Office", 30, "Demo record — renew at the regional office."),
    ("Vehicle Insurance", "vehicle_insurance", "POL-DEMO-551209", -353, 12,
     "Demo Insurance Ltd", 30, "Demo record — policy renewal."),
    ("Passport", "passport", "P-DEMO-771203", -1100, 210,
     "Demo Passport Office", 60, "Demo record — check visa rules before travel."),
    ("Health Insurance", "health_insurance", "HI-DEMO-300991", -690, 30,
     "Demo Health Insurance", 15, "Demo record — family floater policy."),
    ("Laptop Warranty", "warranty", "WT-DEMO-441207", -500, -6,
     "Demo Electronics Store", 30, "Demo record — already expired, needs service."),
    ("Course Certificate", "certificate", "CERT-DEMO-11902", -400, 95,
     "Demo Academy", 14, "Demo record — professional certification."),
]


def seed_documents(db, today: date) -> int:
    """Insert demo documents that do not already exist."""
    created = 0
    for name, doc_type, number, issue_offset, expiry_offset, authority, reminder, notes in DEMO_DOCUMENTS:
        exists = db.scalar(
            select(func.count(Document.id)).where(
                Document.document_name == name, Document.document_number == number
            )
        )
        if exists:
            continue

        db.add(
            Document(
                document_name=name,
                document_type=doc_type,
                document_number=number,
                issue_date=today + timedelta(days=issue_offset),
                expiry_date=today + timedelta(days=expiry_offset),
                issuing_authority=authority,
                reminder_days_before=reminder,
                notes=notes,
            )
        )
        created += 1

    db.commit()
    return created


# --------------------------------------------------------------- DoseNote demo

# Placeholder schedules only. Replace them with your own medication information.
# These are NOT medical recommendations.
DEMO_MEDICATIONS = [
    {
        "medication_name": "Vitamin D3 (demo)",
        "dosage": "1",
        "dosage_unit": "tablet",
        "instructions": "Demo entry — replace with your own instructions.",
        "start_offset": -14,
        "times": [time(8, 0), time(20, 0)],
        "notes": "Fictional demo schedule, not a medical recommendation.",
    },
    {
        "medication_name": "Mineral Water Tablet (demo)",
        "dosage": "1",
        "dosage_unit": "tablet",
        "instructions": "Demo entry — taken after food as per your own routine.",
        "start_offset": -30,
        "times": [time(14, 0)],
        "notes": "Fictional demo schedule, not a medical recommendation.",
    },
]


def _schedule_exists(db, name: str) -> bool:
    return bool(
        db.scalar(
            select(func.count(MedicationSchedule.id)).where(
                MedicationSchedule.medication_name == name
            )
        )
    )


def seed_medications(db, today: date) -> int:
    """Insert demo medication schedules and a week of historical dose logs."""
    created = 0
    schedules: list[MedicationSchedule] = []

    for spec in DEMO_MEDICATIONS:
        if _schedule_exists(db, spec["medication_name"]):
            existing = db.scalar(
                select(MedicationSchedule).where(
                    MedicationSchedule.medication_name == spec["medication_name"]
                )
            )
            if existing is not None:
                schedules.append(existing)
            continue

        schedule = MedicationSchedule(
            medication_name=spec["medication_name"],
            dosage=spec["dosage"],
            dosage_unit=spec["dosage_unit"],
            instructions=spec["instructions"],
            start_date=today + timedelta(days=spec["start_offset"]),
            end_date=None,
            active=True,
            notes=spec["notes"],
        )
        for value in spec["times"]:
            schedule.schedule_times.append(MedicationScheduleTime(scheduled_time=value))

        db.add(schedule)
        db.flush()
        schedules.append(schedule)
        created += 1

    db.commit()

    # Historical dose logs for the last 7 days (today included).
    dose_created = 0
    now_local = datetime.now(timezone.utc)

    for schedule in schedules:
        schedule_times = sorted(item.scheduled_time for item in schedule.schedule_times)
        if not schedule_times:
            continue

        for days_ago in range(6, -1, -1):
            day = today - timedelta(days=days_ago)
            if day < schedule.start_date:
                continue

            for scheduled_time in schedule_times:
                exists = db.scalar(
                    select(func.count(DoseLog.id)).where(
                        DoseLog.medication_schedule_id == schedule.id,
                        DoseLog.scheduled_date == day,
                        DoseLog.scheduled_time == scheduled_time,
                    )
                )
                if exists:
                    continue

                # Older days are mostly 'taken'; today is left mostly pending
                # so the dashboard shows real 'Mark Taken' actions to click.
                if days_ago > 0:
                    # Skip roughly one dose in ten, deterministically.
                    if (days_ago + scheduled_time.hour) % 10 == 0:
                        db.add(
                            DoseLog(
                                medication_schedule_id=schedule.id,
                                scheduled_date=day,
                                scheduled_time=scheduled_time,
                                status="skipped",
                                notes="Demo history entry (skipped).",
                            )
                        )
                    else:
                        due = datetime.combine(day, scheduled_time, tzinfo=timezone.utc)
                        db.add(
                            DoseLog(
                                medication_schedule_id=schedule.id,
                                scheduled_date=day,
                                scheduled_time=scheduled_time,
                                status="taken",
                                taken_at=due + timedelta(minutes=5),
                            )
                        )
                else:
                    # Today: mark earlier doses as taken, leave the rest pending.
                    if scheduled_time <= now_local.time():
                        due = datetime.combine(day, scheduled_time, tzinfo=timezone.utc)
                        db.add(
                            DoseLog(
                                medication_schedule_id=schedule.id,
                                scheduled_date=day,
                                scheduled_time=scheduled_time,
                                status="taken",
                                taken_at=due + timedelta(minutes=3),
                            )
                        )
                    else:
                        db.add(
                            DoseLog(
                                medication_schedule_id=schedule.id,
                                scheduled_date=day,
                                scheduled_time=scheduled_time,
                                status="pending",
                            )
                        )
                dose_created += 1

    db.commit()
    return created + dose_created


# -------------------------------------------------------------- AquaHabit demo

# Today's entries, as (minutes after local midnight, amount_ml, note).
TODAY_INTAKE = [
    (7 * 60 + 30, 250, "Morning glass"),
    (9 * 60 + 15, 350, "With breakfast"),
    (11 * 60 + 0, 150, "Desk bottle"),
    (13 * 60 + 30, 250, "After lunch"),
    (16 * 60 + 0, 350, "Afternoon top-up"),
]

# The last six days, as (total_ml, number_of_entries).
HISTORY_INTAKE = [
    (1750, 6),
    (2100, 7),
    (1400, 5),
    (2250, 8),
    (1900, 6),
    (2000, 7),
]


def seed_hydration(db, today: date) -> int:
    """Set the demo goal and add water entries for today plus the last 6 days."""
    created = 0

    # Illustrative demo goal of 2000 ml with a 250 ml serving. This is a user
    # preference the demo sets, not a medical recommendation.
    settings_row = get_hydration_settings(db)
    if settings_row.daily_goal_ml != 2000 or settings_row.default_serving_ml != 250:
        settings_row.daily_goal_ml = 2000
        settings_row.default_serving_ml = 250
        db.commit()

    for minutes, amount, note in TODAY_INTAKE:
        consumed_at = datetime.combine(today, time(0, 0), tzinfo=timezone.utc) + timedelta(minutes=minutes)
        exists = db.scalar(
            select(func.count(WaterIntakeRecord.id)).where(
                WaterIntakeRecord.entry_date == today,
                WaterIntakeRecord.consumed_at == consumed_at,
            )
        )
        if exists:
            continue
        db.add(
            WaterIntakeRecord(
                amount_ml=amount,
                consumed_at=consumed_at,
                entry_date=today,
                notes=note,
            )
        )
        created += 1

    db.commit()

    for days_ago, (total_ml, entry_count) in enumerate(HISTORY_INTAKE, start=1):
        day = today - timedelta(days=days_ago)

        exists = db.scalar(
            select(func.count(WaterIntakeRecord.id)).where(WaterIntakeRecord.entry_date == day)
        )
        if exists:
            continue

        # Spread the day's total evenly across its entries.
        per_entry = max(1, total_ml // entry_count)
        for index in range(entry_count):
            minutes = 8 * 60 + index * (14 * 60 // max(1, entry_count))
            consumed_at = datetime.combine(day, time(0, 0), tzinfo=timezone.utc) + timedelta(minutes=minutes)
            db.add(
                WaterIntakeRecord(
                    amount_ml=per_entry,
                    consumed_at=consumed_at,
                    entry_date=day,
                    notes=None if index else "Demo history entry.",
                )
            )
            created += 1

    db.commit()
    return created


# --------------------------------------------------------------------- runner


def seed_all(force: bool = False) -> dict[str, int]:
    """Run every seeder and return a dict of how many rows each one added.

    Each seeder checks for existing rows before inserting, so calling this twice
    adds nothing the second time. ``--force`` is only needed if you want to
    restore a demo row that you deleted by hand.
    """
    init_db()
    db = SessionLocal()
    today = date.today()
    try:
        get_app_settings(db)  # ensure the settings row exists
        return {
            "bills": seed_bills(db, today),
            "documents": seed_documents(db, today),
            "medications": seed_medications(db, today),
            "hydration": seed_hydration(db, today),
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed DailyFlow demo data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Insert demo rows even when records with the same name already exist.",
    )
    args = parser.parse_args()

    results = seed_all(force=args.force)

    print("DailyFlow demo data seeding finished.")
    for name, count in results.items():
        state = f"added {count} row(s)" if count else "already present (nothing duplicated)"
        print(f"  - {name:<12} {state}")
    print("\nAll demo records are fictional and for demonstration only.")


if __name__ == "__main__":
    main()