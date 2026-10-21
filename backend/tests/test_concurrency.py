"""Tests for concurrent access to the shared SQLite database.

Why this file exists
--------------------
The dashboard fires several API requests at the same moment (JavaScript
``Promise.all``). Two of them - /api/medications/today and /api/reminders -
both ask the database to generate today's dose logs. A naive
"SELECT then INSERT" would let both decide the dose log does not exist yet, and
the second INSERT would fail the UNIQUE constraint and return a 500.

These tests reproduce that situation directly.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.main import app
from app.models.medication import DoseLog, MedicationSchedule, MedicationScheduleTime

TODAY = date.today()


def _seed_schedule(session) -> None:
    """Insert one active schedule with two daily times."""
    schedule = MedicationSchedule(
        medication_name="Race Condition Test",
        dosage="1",
        dosage_unit="tablet",
        start_date=TODAY,
        active=True,
    )
    schedule.schedule_times.append(MedicationScheduleTime(scheduled_time=time_from(8)))
    schedule.schedule_times.append(MedicationScheduleTime(scheduled_time=time_from(20)))
    session.add(schedule)
    session.commit()


def time_from(hour: int):
    from datetime import time as _time

    return _time(hour, 0)


def test_concurrent_dose_generation_does_not_duplicate(client):
    """Two threads generating the same day's doses must produce 2 rows, not 4."""
    session = SessionLocal()
    try:
        _seed_schedule(session)
    finally:
        session.close()

    def hit_endpoint():
        # Each thread gets its own client so they do not share state.
        with TestClient(app) as local_client:
            response = local_client.get("/api/medications/today")
            return response.status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(lambda _: hit_endpoint(), range(4)))

    assert all(code == 200 for code in codes), f"some requests failed: {codes}"

    session = SessionLocal()
    try:
        rows = session.execute(
            select(DoseLog).where(DoseLog.scheduled_date == TODAY)
        ).scalars().all()
    finally:
        session.close()

    # Two scheduled times, and exactly one log for each of them.
    assert len(rows) == 2, f"expected 2 dose logs, got {len(rows)}"

    keys = {(r.medication_schedule_id, r.scheduled_date, r.scheduled_time) for r in rows}
    assert len(keys) == len(rows), "duplicate dose logs were created"


def test_concurrent_reminders_and_today_both_succeed(client):
    """The exact pair the dashboard requests in parallel."""
    session = SessionLocal()
    try:
        _seed_schedule(session)
    finally:
        session.close()

    def call(path):
        with TestClient(app) as local_client:
            return path, local_client.get(path).status_code

    paths = [
        "/api/medications/today",
        "/api/reminders",
        "/api/medications/adherence",
        "/api/dashboard/summary",
    ]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(call, paths))

    failures = [(path, code) for path, code in results if code != 200]
    assert not failures, f"these requests failed under concurrency: {failures}"


def test_repeated_generation_is_stable(client):
    """Calling generation many times in a row never multiplies the rows."""
    session = SessionLocal()
    try:
        _seed_schedule(session)
    finally:
        session.close()

    for _ in range(6):
        assert client.get("/api/medications/today").status_code == 200

    session = SessionLocal()
    try:
        count = session.execute(
            select(func.count(DoseLog.id)).where(DoseLog.scheduled_date == TODAY)
        ).scalar()
    finally:
        session.close()

    assert count == 2


def test_generated_doses_are_never_auto_marked_taken(client):
    """The whole point of generation is a 'pending' row the user ticks off."""
    session = SessionLocal()
    try:
        _seed_schedule(session)
    finally:
        session.close()

    for _ in range(3):
        client.get("/api/medications/today")

    session = SessionLocal()
    try:
        rows = session.execute(
            select(DoseLog).where(DoseLog.scheduled_date == TODAY)
        ).scalars().all()
    finally:
        session.close()

    assert rows, "no dose logs were generated"
    assert all(r.status == "pending" for r in rows), "generation must not mark doses taken"
    assert all(r.taken_at is None for r in rows)