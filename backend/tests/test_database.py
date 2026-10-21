"""Tests for database initialization and the pure date/utility helpers."""

from datetime import date, datetime, time

from sqlalchemy import inspect

from app.db.base import Base
from app.utils.dates import (
    add_months,
    combine,
    days_between,
    month_end,
    month_start,
    parse_time_string,
    week_start,
)
from app.utils.masking import mask_document_number

EXPECTED_TABLES = {
    "bills",
    "documents",
    "document_renewals",
    "medication_schedules",
    "medication_schedule_times",
    "dose_logs",
    "hydration_settings",
    "water_intake_records",
    "app_settings",
}


def test_all_expected_tables_exist(db):
    """Every table listed in the design document is really created."""
    inspector = inspect(db.bind)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {missing}"


def test_init_db_is_repeatable():
    """Running create_all twice must not raise (no duplicate table error)."""
    from app.db.init_db import init_db

    init_db()
    init_db()  # second call must be a no-op
    assert "bills" in Base.metadata.tables


def test_foreign_keys_are_enforced(db):
    """SQLite must have PRAGMA foreign_keys switched on per connection."""
    from sqlalchemy import text

    result = db.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1


def test_days_between_handles_leap_year():
    """2024 is a leap year: 29 Feb exists, so the gap is one day shorter."""
    assert days_between(date(2024, 2, 28), date(2024, 3, 1)) == 2
    # 2023 is not a leap year.
    assert days_between(date(2023, 2, 28), date(2023, 3, 1)) == 1


def test_days_between_month_boundary():
    assert days_between(date(2026, 1, 31), date(2026, 2, 28)) == 28
    assert days_between(date(2026, 10, 15), date(2026, 10, 15)) == 0
    assert days_between(date(2026, 10, 15), date(2026, 10, 10)) == -5


def test_add_months_clamps_to_end_of_month():
    """31 Jan + 1 month must land on the last day of Feb, not crash."""
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    # Leap year February.
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    # Year rollover.
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert add_months(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_month_and_week_helpers():
    assert month_start(date(2026, 3, 17)) == date(2026, 3, 1)
    assert month_end(date(2026, 2, 5)) == date(2026, 2, 28)
    assert month_end(date(2024, 2, 5)) == date(2024, 2, 29)  # leap year
    assert month_end(date(2026, 12, 5)) == date(2026, 12, 31)
    # 2026-10-15 is a Thursday; Monday of that week is the 12th.
    assert week_start(date(2026, 10, 15)) == date(2026, 10, 12)


def test_parse_time_string():
    assert parse_time_string("08:00") == time(8, 0)
    assert parse_time_string("20:45") == time(20, 45)
    assert parse_time_string("07:05:30") == time(7, 5, 30)
    assert parse_time_string("  09:10 ") == time(9, 10)


def test_parse_time_string_rejects_bad_input():
    for bad in ["25:00", "abc", "8pm", "", "12:75"]:
        try:
            parse_time_string(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should have raised ValueError")


def test_combine_is_timezone_aware():
    moment = combine(date(2026, 10, 15), time(8, 30))
    assert moment.tzinfo is not None
    assert moment.hour == 8 and moment.minute == 30


def test_mask_document_number():
    number = "DL-1234-9876543"
    masked = mask_document_number(number)
    # Everything except the final 4 characters is hidden.
    assert masked.endswith("6543")
    assert masked == "*" * (len(number) - 4) + "6543"
    assert number not in masked

    assert mask_document_number("abc") == "***"
    assert mask_document_number(None) is None
    assert mask_document_number("") == ""