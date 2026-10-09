"""Base mixins shared by all ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Provides a UUID v4 primary key column named ``id``."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        sort_order=-10,
    )


class TimestampMixin:
    """Provides ``created_at`` and ``updated_at`` columns (UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=900,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=901,
    )


class SoftDeleteMixin:
    """Provides ``deleted_at`` and ``deleted_by`` for soft-delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        sort_order=910,
    )
    deleted_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        default=None,
        sort_order=911,
    )
