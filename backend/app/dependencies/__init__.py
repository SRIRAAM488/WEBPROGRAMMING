"""Reusable dependency providers for the routers."""

from fastapi import Header

# The frontend sends the browser's UTC offset (in minutes) on every request so
# that "today" and "due today" match what the user sees on their own clock.
# Example: India (UTC+5:30) -> header value 330.
DEFAULT_TZ_OFFSET = 0


def get_tz_offset(
    x_client_utc_offset: int | None = Header(
        default=None,
        alias="X-Client-Utc-Offset",
        description="Browser UTC offset in minutes (e.g. 330 for UTC+5:30).",
    ),
) -> int:
    """Return the client's UTC offset, clamped to a sane range (-14h..+14h)."""
    if x_client_utc_offset is None:
        return DEFAULT_TZ_OFFSET
    return max(-840, min(840, x_client_utc_offset))


__all__ = ["get_tz_offset", "DEFAULT_TZ_OFFSET"]