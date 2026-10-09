"""Attendance model."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.attendance.enums import AttendanceSource, AttendanceStatus
from app.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Attendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_attendances_employee_date"),
        Index("ix_attendances_employee_id", "employee_id"),
        Index("ix_attendances_work_date", "work_date"),
        Index("ix_attendances_status", "status"),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AttendanceStatus.PRESENT,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AttendanceSource.SYSTEM,
    )
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
