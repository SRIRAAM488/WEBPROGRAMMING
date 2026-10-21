"""Small date / time helpers shared across services.

All stored datetimes are UTC. "Today" for the user is computed in the user's
local timezone (which is what the browser reports), so that a dose logged at
11pm is not filed under the wrong day.
"""

from datetime import date, datetime, time, timedelta, timezone


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc(value: datetime, offset_minutes: int = 0) -> datetime:
    """Attach UTC to a naive datetime, or convert an aware one to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def local_today(offset_minutes: int = 0) -> date:
    """Today's date in the user's local timezone.

    ``offset_minutes`` lets the API work for a user who is ahead of or behind
    UTC (for example UTC+5:30 for India).
    """
    if offset_minutes == 0:
        return datetime.now(timezone.utc).date()
    shifted = utc_now() + timedelta(minutes=offset_minutes)
    return shifted.date()


def local_now(offset_minutes: int = 0) -> datetime:
    """Current local wall-clock time (timezone-aware UTC or UTC+offset)."""
    if offset_minutes == 0:
        return utc_now()
    return utc_now() + timedelta(minutes=offset_minutes)


def as_utc(value: datetime | None) -> datetime | None:
    """Normalise any datetime to a timezone-aware UTC datetime.

    SQLite does not store timezone information, so a datetime read back from the
    database is *naive*. Comparing a naive value with an aware one raises
    ``TypeError``. Every datetime read from the database passes through this
    helper before it is compared or sorted.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def days_between(start: date, end: date) -> int:
    """Whole days from ``start`` to ``end`` (negative if ``end`` is in the past).

    Uses timedelta on real calendar dates, so leap years (29 Feb) and month
    boundaries are handled correctly without any special-casing.
    """
    return (end - start).days


def add_months(source: date, months: int) -> date:
    """Add months to a date, clamping to the last valid day of the target month.

    Example: 31 Jan + 1 month -> 28/29 Feb (not a crash, not 3 March).
    """
    if months == 0:
        return source
    total_month = source.month - 1 + months
    year = source.year + total_month // 12
    month = total_month % 12 + 1

    # Last day of the target month.
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = (next_month_first - timedelta(days=1)).day

    return date(year, month, min(source.day, last_day))


def week_start(day: date) -> date:
    """Monday of the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def month_start(day: date) -> date:
    """First day of the month containing ``day``."""
    return day.replace(day=1)


def month_end(day: date) -> date:
    """Last day of the month containing ``day``."""
    if day.month == 12:
        next_month_first = date(day.year + 1, 1, 1)
    else:
        next_month_first = date(day.year, day.month + 1, 1)
    return next_month_first - timedelta(days=1)


def parse_time_string(value: str) -> time:
    """Parse 'HH:MM' or 'HH:MM:SS' into a ``time`` object."""
    cleaned = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: {value!r}. Use HH:MM (24 hour).")


def combine(day: date, at_time: time, offset_minutes: int = 0) -> datetime:
    """Build a UTC datetime for a local date + local time."""
    local = datetime.combine(day, at_time)
    if offset_minutes:
        local = local + timedelta(minutes=offset_minutes)
    return local.replace(tzinfo=timezone.utc)


def format_minutes(total_minutes: int) -> str:
    """Render a minute count like '2h 15m' (used by reminders)."""
    if total_minutes < 60:
        return f"{total_minutes}m"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"