"""AuditLog Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
