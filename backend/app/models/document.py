"""DateGuard - important document expiry tracking model."""

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utc_now

DOCUMENT_TYPES = (
    "driving_licence",
    "passport",
    "aadhaar",
    "pan",
    "vehicle_insurance",
    "health_insurance",
    "certificate",
    "warranty",
    "other",
)

# Status values are *derived* at read time from expiry_date vs today, so they are
# never stored as stale permanent truth. These are the three buckets used.
DOCUMENT_STATUSES = ("expired", "expiring_soon", "valid")


class Document(Base):
    """A document with an expiry date (licence, passport, insurance, ...)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_name: Mapped[str] = mapped_column(String(120), nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    document_number: Mapped[str | None] = mapped_column(String(60), nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # How many days before expiry the user wants to start being reminded.
    reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional convenience flag: set by the user when they no longer care.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Renewal history: keeps the previous expiry date after a renewal.
    renewals: Mapped[list["DocumentRenewal"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentRenewal.renewed_at"
    )

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('driving_licence','passport','aadhaar','pan',"
            "'vehicle_insurance','health_insurance','certificate','warranty','other')",
            name="valid_document_type",
        ),
        CheckConstraint(
            "reminder_days_before >= 0 AND reminder_days_before <= 365",
            name="valid_reminder_days",
        ),
        Index("ix_documents_expiry_date", "expiry_date"),
        Index("ix_documents_document_type", "document_type"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Document id={self.id} name={self.document_name!r} expiry={self.expiry_date}>"


class DocumentRenewal(Base):
    """A simple renewal history row for one document.

    Why a new table? When a document is renewed we overwrite ``expiry_date``.
    Without history the user loses the old expiry, which matters for tracking
    things like insurance continuity. One small table solves that.
    """

    __tablename__ = "document_renewals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    previous_expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    renewed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="renewals")

    __table_args__ = (
        CheckConstraint("new_expiry_date > previous_expiry_date", name="renewal_moves_forward"),
        Index("ix_document_renewals_document_id", "document_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DocumentRenewal doc={self.document_id} {self.previous_expiry_date}->{self.new_expiry_date}>"