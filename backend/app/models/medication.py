"""DoseNote - medication schedules and dose log models.

Important: DoseNote is a personal tracking and reminder tool. It does not give
medical advice and it never tells a user to change a prescribed medication.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utc_now

DOSE_STATUSES = ("pending", "taken", "skipped")

DOSAGE_UNITS = ("mg", "g", "ml", "tablet", "tablets", "capsule", "capsules", "drop", "drops", "IU", "unit")


class MedicationSchedule(Base):
    """A repeating medication plan, e.g. 'Vitamin D - 08:00 and 20:00'."""

    __tablename__ = "medication_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medication_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dosage: Mapped[str] = mapped_column(String(40), nullable=False)
    dosage_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="tablet")
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # One-to-many: a schedule owns several daily times.
    schedule_times: Mapped[list["MedicationScheduleTime"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="MedicationScheduleTime.scheduled_time",
    )
    dose_logs: Mapped[list["DoseLog"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="valid_date_range"),
        Index("ix_medication_schedules_active", "active"),
    )

    def is_active_on(self, day: date) -> bool:
        """Return True when this schedule should produce doses on ``day``."""
        if not self.active:
            return False
        if day < self.start_date:
            return False
        if self.end_date is not None and day > self.end_date:
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<MedicationSchedule id={self.id} name={self.medication_name!r}>"


class MedicationScheduleTime(Base):
    """One time-of-day row belonging to a medication schedule.

    A separate table (instead of a comma separated string) means each time can
    be validated and indexed properly.
    """

    __tablename__ = "medication_schedule_times"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medication_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("medication_schedules.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    label: Mapped[str | None] = mapped_column(String(40), nullable=True)

    schedule: Mapped["MedicationSchedule"] = relationship(back_populates="schedule_times")

    __table_args__ = (
        UniqueConstraint(
            "medication_schedule_id", "scheduled_time", name="uq_schedule_time_unique"
        ),
        Index("ix_schedule_times_schedule_id", "medication_schedule_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<MedicationScheduleTime schedule_id={self.medication_schedule_id} t={self.scheduled_time}>"


class DoseLog(Base):
    """The record of one scheduled dose on one particular day."""

    __tablename__ = "dose_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medication_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("medication_schedules.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)

    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    taken_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    schedule: Mapped["MedicationSchedule"] = relationship(back_populates="dose_logs")

    __table_args__ = (
        CheckConstraint("status IN ('pending','taken','skipped')", name="valid_dose_status"),
        # Stops the same schedule+date+time being logged twice.
        UniqueConstraint(
            "medication_schedule_id", "scheduled_date", "scheduled_time", name="uq_dose_log_unique"
        ),
        Index("ix_dose_logs_scheduled_date", "scheduled_date"),
        Index("ix_dose_logs_schedule_date", "medication_schedule_id", "scheduled_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DoseLog id={self.id} date={self.scheduled_date} t={self.scheduled_time} {self.status}>"