"""Leave models: LeaveType, LeaveBalance, LeaveRequest."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.leave.enums import LeaveRequestStatus
from app.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class LeaveType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_types"

    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_days_per_year: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LeaveBalance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        Index("ix_leave_balances_employee_id", "employee_id"),
        Index("ix_leave_balances_leave_type_id", "leave_type_id"),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    leave_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leave_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(nullable=False)
    total_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False, default=0)
    used_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False, default=0)
    pending_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False, default=0)


class LeaveRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        Index("ix_leave_requests_employee_id", "employee_id"),
        Index("ix_leave_requests_status", "status"),
        Index("ix_leave_requests_leave_type_id", "leave_type_id"),
        Index("ix_leave_requests_created_at", "created_at"),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    leave_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leave_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LeaveRequestStatus.PENDING,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
