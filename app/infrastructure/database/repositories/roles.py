"""Concrete SQLAlchemy repositories for Role, Permission, RefreshToken, PasswordResetToken."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.user import (
    PasswordResetToken,
    Permission,
    RefreshToken,
    Role,
)


class SqlRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )
        return result.scalars().first()

    async def get_by_id(self, role_id: str) -> Role | None:
        result = await self._session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        return result.scalars().first()

    async def list_all(self) -> Sequence[Role]:
        result = await self._session.execute(
            select(Role).options(selectinload(Role.permissions))
        )
        return result.scalars().all()

    async def create(self, role: Role) -> Role:
        self._session.add(role)
        await self._session.flush()
        return role

    async def upsert_by_name(self, name: str, description: str | None = None) -> Role:
        existing = await self.get_by_name(name)
        if existing:
            if description is not None:
                existing.description = description
            return existing
        role = Role(name=name, description=description)
        self._session.add(role)
        await self._session.flush()
        return role


class SqlPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> Permission | None:
        result = await self._session.execute(
            select(Permission).where(Permission.code == code)
        )
        return result.scalars().first()

    async def list_all(self) -> Sequence[Permission]:
        result = await self._session.execute(select(Permission))
        return result.scalars().all()

    async def upsert_by_code(self, code: str, description: str | None = None) -> Permission:
        existing = await self.get_by_code(code)
        if existing:
            if description is not None:
                existing.description = description
            return existing
        perm = Permission(code=code, description=description)
        self._session.add(perm)
        await self._session.flush()
        return perm


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    async def revoke(self, token_id: str, replaced_by: str | None = None) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(UTC), replaced_by=replaced_by)
        )

    async def revoke_family(self, family_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )


class SqlPasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        return result.scalars().first()

    async def mark_used(self, token_id: str) -> None:
        await self._session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )

    async def invalidate_all_for_user(self, user_id: str) -> None:
        await self._session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
