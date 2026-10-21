"""Application-wide settings (theme, currency, reminder lead times).

DailyFlow is a single-user local prototype, so there is exactly one settings
row (id = 1). It is created automatically the first time the app runs.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now

SUPPORTED_CURRENCIES = ("INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "CAD")
SUPPORTED_THEMES = ("light", "dark")


class AppSettings(Base):
    """Preferences that affect how DailyFlow behaves and looks."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="light")

    # Global reminder lead times in days (per-module overrides also exist).
    bill_reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    document_reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    hydration_reminder_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # How many minutes after the scheduled time a pending dose becomes "missed".
    dose_grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # A demo disclaimer that the UI shows near medication features.
    show_medical_disclaimer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("length(default_currency) = 3", name="currency_three_chars"),
        CheckConstraint("theme IN ('light','dark')", name="valid_theme"),
        CheckConstraint(
            "bill_reminder_days_before >= 0 AND bill_reminder_days_before <= 90",
            name="valid_bill_reminder_days",
        ),
        CheckConstraint(
            "document_reminder_days_before >= 0 AND document_reminder_days_before <= 365",
            name="valid_document_reminder_days",
        ),
        CheckConstraint(
            "hydration_reminder_percent >= 10 AND hydration_reminder_percent <= 100",
            name="valid_hydration_reminder_percent",
        ),
        CheckConstraint(
            "dose_grace_minutes >= 0 AND dose_grace_minutes <= 1440",
            name="valid_dose_grace_minutes",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AppSettings currency={self.default_currency} theme={self.theme}>"