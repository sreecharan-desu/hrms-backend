"""Concrete SQLAlchemy user repository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.user import User


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(User).options(
            selectinload(User.roles),
        )

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(
            self._base_query().where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            self._base_query().where(User.email == email)
        )
        return result.scalars().first()

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> Sequence[User]:
        result = await self._session.execute(
            self._base_query()
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        result = await self._session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        await self._session.flush()
        return user
