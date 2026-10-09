"""Employee and EmployeeCompensation models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.employees.enums import EmploymentStatus
from app.infrastructure.database.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("employee_code", name="uq_employees_employee_code"),
        UniqueConstraint("email", name="uq_employees_email"),
        UniqueConstraint("user_id", name="uq_employees_user_id"),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_status", "status"),
        Index("ix_employees_created_at", "created_at"),
    )

    employee_code: Mapped[str] = mapped_column(String(30), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
    )
    department_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    emergency_contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    department: Mapped[Department | None] = relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="employees",
    )
    manager: Mapped[Employee | None] = relationship(
        "Employee",
        remote_side="Employee.id",
        foreign_keys=[manager_id],
    )
    compensation: Mapped[EmployeeCompensation | None] = relationship(
        back_populates="employee",
        uselist=False,
    )


class EmployeeCompensation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_compensations"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_employee_compensations_employee_id"),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="compensation")


# Avoid circular import – forward ref resolved via string in relationship above
from app.infrastructure.database.models.department import Department  # noqa: E402
