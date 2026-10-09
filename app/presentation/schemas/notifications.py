"""Notification Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    title: str
    body: str | None = None
    channel: str
    is_read: bool
    read_at: datetime | None = None
    link: str | None = None
    created_at: datetime | None = None
