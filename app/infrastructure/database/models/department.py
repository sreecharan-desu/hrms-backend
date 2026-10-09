"""Department model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.infrastructure.database.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Department(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("code", name="uq_departments_code"),
        Index("ix_departments_parent_id", "parent_id"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    head_employee_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side="Department.id",
        foreign_keys=[parent_id],
    )
    employees: Mapped[list] = relationship(
        "Employee",
        foreign_keys="Employee.department_id",
        back_populates="department",
    )
