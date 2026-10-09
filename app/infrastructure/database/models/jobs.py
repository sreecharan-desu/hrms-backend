"""BackgroundJob (transactional outbox) model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class BackgroundJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        Index("ix_background_jobs_status", "status"),
        Index("ix_background_jobs_available_at", "available_at"),
        Index("ix_background_jobs_type", "type"),
    )

    type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
