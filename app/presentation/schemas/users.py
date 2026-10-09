"""User admin Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str
    status: str
    roles: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AssignRolesRequest(BaseModel):
    role_names: list[str]
