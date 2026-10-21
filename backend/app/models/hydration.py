"""AquaHabit - hydration settings and water intake models.

Millilitres (ml) is the canonical storage unit everywhere in DailyFlow.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now


class HydrationSettings(Base):
    """The single settings row that controls hydration goals.

    Only one row is ever expected (id = 1); the app creates it automatically.
    """

    __tablename__ = "hydration_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    daily_goal_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    default_serving_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=250)
    reminder_enabled: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("daily_goal_ml > 0 AND daily_goal_ml <= 10000", name="valid_daily_goal"),
        CheckConstraint(
            "default_serving_ml > 0 AND default_serving_ml <= 5000", name="valid_serving_size"
        ),
        CheckConstraint("reminder_enabled IN (0,1)", name="valid_reminder_flag"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<HydrationSettings goal={self.daily_goal_ml}ml serving={self.default_serving_ml}ml>"


class WaterIntakeRecord(Base):
    """One glass / bottle of water that the user logged."""

    __tablename__ = "water_intake_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    # Denormalised copy of the local date so day grouping is a simple indexed lookup.
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("amount_ml > 0 AND amount_ml <= 5000", name="positive_amount_ml"),
        Index("ix_water_intake_entry_date", "entry_date"),
        Index("ix_water_intake_consumed_at", "consumed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<WaterIntakeRecord id={self.id} {self.amount_ml}ml on {self.entry_date}>"