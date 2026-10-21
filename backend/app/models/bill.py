"""BillBell - bill payment tracking model."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now

# Allowed values are duplicated here (as CHECK constraints) and in the Pydantic
# schemas. The database is the final guard, the schemas give friendly errors.
BILL_CATEGORIES = (
    "electricity",
    "water",
    "internet",
    "mobile",
    "rent",
    "subscription",
    "education",
    "insurance",
    "other",
)

BILL_STATUSES = ("unpaid", "paid", "overdue")

RECURRENCE_INTERVALS = ("none", "weekly", "monthly", "quarterly", "yearly", "yearly_2", "custom")

SUPPORTED_CURRENCIES = ("INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "CAD")


class Bill(Base):
    """A single bill that the user has to pay (one-time or recurring)."""

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Numeric -> stored as SQLite DECIMAL, exposed to Python as Decimal (no float errors).
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="unpaid")
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_interval: Mapped[str] = mapped_column(String(20), nullable=False, default="none")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint(
            "category IN ('electricity','water','internet','mobile','rent',"
            "'subscription','education','insurance','other')",
            name="valid_category",
        ),
        CheckConstraint("status IN ('unpaid','paid','overdue')", name="valid_status"),
        CheckConstraint(
            "recurrence_interval IN ('none','weekly','monthly','quarterly',"
            "'yearly','yearly_2','custom')",
            name="valid_recurrence",
        ),
        CheckConstraint("length(currency) = 3", name="currency_three_chars"),
        Index("ix_bills_due_date", "due_date"),
        Index("ix_bills_status", "status"),
        Index("ix_bills_category", "category"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Bill id={self.id} name={self.bill_name!r} status={self.status!r}>"