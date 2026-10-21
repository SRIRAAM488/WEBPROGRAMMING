"""Shared SQLAlchemy base class and common column helpers."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase

# A shared naming convention keeps Alembic-style migrations predictable and
# avoids clashes between automatically generated constraint names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class that every SQLAlchemy model inherits from."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Reusable column type: always stored as UTC.
UTCDateTime = DateTime(timezone=True)