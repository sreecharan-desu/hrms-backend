"""Document model."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.documents.enums import DocumentStatus
from app.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_employee_id", "employee_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )

    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
