"""Performance models: PerformanceCycle, PerformanceReview, PerformanceGoal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.performance.enums import ReviewStatus
from app.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class PerformanceCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_cycles"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    reviews: Mapped[list[PerformanceReview]] = relationship(back_populates="cycle")


class PerformanceReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_reviews"
    __table_args__ = (
        Index("ix_performance_reviews_employee_id", "employee_id"),
        Index("ix_performance_reviews_cycle_id", "cycle_id"),
        Index("ix_performance_reviews_status", "status"),
    )

    cycle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("performance_cycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReviewStatus.DRAFT,
    )
    self_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    manager_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    final_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    self_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    cycle: Mapped[PerformanceCycle] = relationship(back_populates="reviews")
    goals: Mapped[list[PerformanceGoal]] = relationship(back_populates="review")


class PerformanceGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_goals"
    __table_args__ = (Index("ix_performance_goals_review_id", "review_id"),)

    review_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("performance_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    achievement: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    review: Mapped[PerformanceReview] = relationship(back_populates="goals")
