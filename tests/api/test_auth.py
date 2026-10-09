"""API-level auth tests using httpx ASGITransport + aiosqlite override."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["APP_ENV"] = "development"

# Patch core.database before anything imports the module-level engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database as _db_mod

_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_db_mod.engine = _test_engine
_db_mod.async_session_factory = _TestSession

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base
from app.core.security import hash_password
from app.domain.users.enums import UserStatus
from app.infrastructure.database.models.user import Role, User
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create all tables in an in-memory SQLite DB for each test."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _TestSession() as session:
        role = Role(name="EMPLOYEE")
        session.add(role)
        await session.flush()
        user = User(
            email="test@example.com",
            password_hash=hash_password("TestPass123!"),
            status=UserStatus.ACTIVE,
            roles=[role],
        )
        session.add(user)
        await session.commit()

    yield

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """httpx AsyncClient wired to the ASGI app with DB overridden."""
    _orig_init = SqlAlchemyUnitOfWork.__init__

    def _patched_init(self, session_factory=_TestSession):
        _orig_init(self, session_factory=session_factory)

    SqlAlchemyUnitOfWork.__init__ = _patched_init  # type: ignore[assignment]

    from app.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    SqlAlchemyUnitOfWork.__init__ = _orig_init  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "WrongPass123!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )
    token = login_resp.json()["data"]["access_token"]
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "test@example.com"
    assert "EMPLOYEE" in data["roles"]


@pytest.mark.asyncio
async def test_validation_error_format(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"email": "bad"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"].get("details"), list)
    assert body["error"]["details"][0]["field"]
    assert body["error"]["details"][0]["message"]
