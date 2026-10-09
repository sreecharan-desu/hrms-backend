"""API-level department tests using httpx ASGITransport + aiosqlite override."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["APP_ENV"] = "development"

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
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _TestSession() as session:
        admin_role = Role(name="HR_ADMIN")
        session.add(admin_role)
        await session.flush()

        admin_user = User(
            email="admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            status=UserStatus.ACTIVE,
            roles=[admin_role],
        )
        session.add(admin_user)
        await session.commit()

    yield

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    _orig_init = SqlAlchemyUnitOfWork.__init__

    def _patched_init(self, session_factory=_TestSession):
        _orig_init(self, session_factory=session_factory)

    SqlAlchemyUnitOfWork.__init__ = _patched_init  # type: ignore[assignment]

    from app.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    SqlAlchemyUnitOfWork.__init__ = _orig_init  # type: ignore[assignment]


async def _login(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Engineering", "code": "ENG"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["code"] == "ENG"


@pytest.mark.asyncio
async def test_list_departments(client: AsyncClient):
    token = await _login(client)
    await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "HR", "code": "HR"},
    )
    resp = await client.get(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_delete_department_blocked_with_employees(client: AsyncClient):
    token = await _login(client)
    dept_resp = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Sales", "code": "SALES"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    # Create employee in that department
    await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP-SALES-1",
            "first_name": "Sales",
            "last_name": "Person",
            "email": "sales@example.com",
            "joining_date": "2024-01-01",
            "department_id": dept_id,
        },
    )

    resp = await client.delete(
        f"/api/v1/departments/{dept_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_children(client: AsyncClient):
    token = await _login(client)
    parent_resp = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Tech", "code": "TECH"},
    )
    parent_id = parent_resp.json()["data"]["id"]
    await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Frontend", "code": "FE", "parent_id": parent_id},
    )
    resp = await client.get(
        f"/api/v1/departments/{parent_id}/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    children = resp.json()["data"]
    assert len(children) == 1
    assert children[0]["code"] == "FE"


@pytest.mark.asyncio
async def test_duplicate_department_code_conflict(client: AsyncClient):
    token = await _login(client)
    await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Finance", "code": "FIN"},
    )
    resp = await client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Finance 2", "code": "FIN"},
    )
    assert resp.status_code == 409
