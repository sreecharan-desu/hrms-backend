"""API-level employee tests using httpx ASGITransport + aiosqlite override."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!!"
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
        # HR_ADMIN role = broad permissions incl. employee.*
        admin_role = Role(name="HR_ADMIN")
        employee_role = Role(name="EMPLOYEE")
        session.add_all([admin_role, employee_role])
        await session.flush()

        admin_user = User(
            email="admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            status=UserStatus.ACTIVE,
            roles=[admin_role],
        )
        normal_user = User(
            email="user@example.com",
            password_hash=hash_password("UserPass123!"),
            status=UserStatus.ACTIVE,
            roles=[employee_role],
        )
        session.add_all([admin_user, normal_user])
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


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_employee_as_admin(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP001",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "joining_date": "2024-01-15",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["employee_code"] == "EMP001"
    assert body["data"]["email"] == "john.doe@example.com"
    assert body["data"]["id"]


@pytest.mark.asyncio
async def test_create_employee_unauthorized_without_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/employees",
        json={
            "employee_code": "EMP002",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "joining_date": "2024-01-15",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_employee_forbidden_for_normal_user(client: AsyncClient):
    token = await _login(client, "user@example.com", "UserPass123!")
    resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP003",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "joining_date": "2024-01-15",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_employees(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    # Create one first
    await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP010",
            "first_name": "List",
            "last_name": "Test",
            "email": "list@example.com",
            "joining_date": "2024-01-15",
        },
    )
    resp = await client.get(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_employee(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    create_resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP020",
            "first_name": "Get",
            "last_name": "Test",
            "email": "get@example.com",
            "joining_date": "2024-02-01",
        },
    )
    emp_id = create_resp.json()["data"]["id"]
    resp = await client.get(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == emp_id


@pytest.mark.asyncio
async def test_update_employee(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    create_resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP030",
            "first_name": "Patch",
            "last_name": "Test",
            "email": "patch@example.com",
            "joining_date": "2024-03-01",
        },
    )
    emp_id = create_resp.json()["data"]["id"]
    resp = await client.patch(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"designation": "Senior Engineer"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["designation"] == "Senior Engineer"


@pytest.mark.asyncio
async def test_delete_employee(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    create_resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP040",
            "first_name": "Delete",
            "last_name": "Test",
            "email": "delete@example.com",
            "joining_date": "2024-04-01",
        },
    )
    emp_id = create_resp.json()["data"]["id"]
    resp = await client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # After delete, get should return 404
    resp = await client.get(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_email_conflict(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP050",
            "first_name": "Dup",
            "last_name": "Email",
            "email": "dup@example.com",
            "joining_date": "2024-05-01",
        },
    )
    resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP051",
            "first_name": "Dup2",
            "last_name": "Email",
            "email": "dup@example.com",
            "joining_date": "2024-05-01",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_nested_attendance_empty(client: AsyncClient):
    token = await _login(client, "admin@example.com", "AdminPass123!")
    create_resp = await client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_code": "EMP060",
            "first_name": "Nested",
            "last_name": "Test",
            "email": "nested@example.com",
            "joining_date": "2024-06-01",
        },
    )
    emp_id = create_resp.json()["data"]["id"]
    resp = await client.get(
        f"/api/v1/employees/{emp_id}/attendance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0
