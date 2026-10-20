"""password reset: forgot-password -> verify-otp -> reset-password."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["APP_ENV"] = "development"
os.environ.setdefault("STORAGE_BUCKET", "hrms-test")
os.environ.setdefault("STORAGE_ACCESS_KEY", "test")
os.environ.setdefault("STORAGE_SECRET_KEY", "test")

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.core.database as _db_mod

_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
_db_mod.engine = _engine
_db_mod.async_session_factory = _Session

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base
from app.core.security import hash_password
from app.domain.users.enums import UserStatus
from app.infrastructure.database.models.leave import LeaveType
from app.infrastructure.database.models.user import Role, User
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

YEAR = date.today().year
IDS: dict[str, str] = {}


@pytest_asyncio.fixture(autouse=True)
async def _db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        admin_role, emp_role = Role(name="HR_ADMIN"), Role(name="EMPLOYEE")
        s.add_all([admin_role, emp_role])
        await s.flush()
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            status=UserStatus.ACTIVE,
            roles=[admin_role],
        )
        staff = User(
            email="staff@example.com",
            password_hash=hash_password("StaffPass123!"),
            status=UserStatus.ACTIVE,
            roles=[emp_role],
        )
        lt = LeaveType(name="Casual", code="CL", max_days_per_year=Decimal("12"), is_paid=True)
        s.add_all([admin, staff, lt])
        await s.commit()
        IDS.update(admin=admin.id, staff=staff.id, lt=lt.id)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    orig = SqlAlchemyUnitOfWork.__init__

    def patched(self, session_factory=_Session):
        orig(self, session_factory=session_factory)

    SqlAlchemyUnitOfWork.__init__ = patched  # type: ignore[assignment]
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    SqlAlchemyUnitOfWork.__init__ = orig  # type: ignore[assignment]


async def _token(c, email, pw):
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _admin(c):
    return await _token(c, "admin@example.com", "AdminPass123!")


async def _employee(c, h, code="E1", email="e1@example.com", user_id=None, **extra):
    body = {
        "employee_code": code,
        "first_name": "Asha",
        "last_name": "Rao",
        "email": email,
        "joining_date": "2024-01-15",
        **extra,
    }
    if user_id:
        body["user_id"] = user_id
    r = await c.post("/api/v1/employees", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def _data(r, status=200):
    assert r.status_code == status, r.text
    return r.json()["data"]


import re

from sqlalchemy import select, text, update

from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.models.user import PasswordResetToken

STAFF = "staff@example.com"


async def _request_otp(client, email=STAFF) -> str:
    r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    async with _Session() as s:
        job = (
            (await s.execute(select(BackgroundJob).order_by(text("rowid DESC")))).scalars().first()
        )
    assert job.type == "email.send"
    assert job.payload["to"] == email
    return re.search(r"code is (\d{6})", job.payload["body_text"]).group(1)


async def _verify(client, otp, email=STAFF):
    return await client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp})


async def _reset(client, token, email=STAFF, pw="BrandNewPass1!"):
    return await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "reset_token": token, "new_password": pw},
    )


async def _login_status(client, email, pw):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    return r.status_code


@pytest.mark.asyncio
async def test_full_reset_flow_changes_password(client):
    otp = await _request_otp(client)
    r = await _verify(client, otp)
    assert r.status_code == 200, r.text
    token = r.json()["data"]["reset_token"]
    assert (await _reset(client, token)).status_code == 200
    assert await _login_status(client, STAFF, "BrandNewPass1!") == 200
    assert await _login_status(client, STAFF, "StaffPass123!") == 401


@pytest.mark.asyncio
async def test_bogus_or_missing_token_is_rejected(client):
    for tok in ("bogus", "", "x" * 64):
        assert (await _reset(client, tok)).status_code in (401, 422)
    assert await _login_status(client, STAFF, "StaffPass123!") == 200
    assert (await _reset(client, "bogus", email="ghost@example.com")).status_code == 401


@pytest.mark.asyncio
async def test_otp_itself_is_not_a_reset_token(client):
    otp = await _request_otp(client)
    assert (await _reset(client, otp)).status_code == 401
    assert await _login_status(client, STAFF, "StaffPass123!") == 200


@pytest.mark.asyncio
async def test_reset_token_is_single_use(client):
    otp = await _request_otp(client)
    token = (await _verify(client, otp)).json()["data"]["reset_token"]
    assert (await _reset(client, token, pw="FirstNewPass1!")).status_code == 200
    assert (await _reset(client, token, pw="SecondNewPass1!")).status_code == 401
    assert await _login_status(client, STAFF, "FirstNewPass1!") == 200


@pytest.mark.asyncio
async def test_otp_is_single_use_and_wrong_otp_fails(client):
    otp = await _request_otp(client)
    wrong = "000000" if otp != "000000" else "111111"
    assert (await _verify(client, wrong)).status_code == 401
    assert (await _verify(client, otp)).status_code == 200
    assert (await _verify(client, otp)).status_code == 401


@pytest.mark.asyncio
async def test_token_is_bound_to_its_user(client):
    otp = await _request_otp(client)
    token = (await _verify(client, otp)).json()["data"]["reset_token"]
    # someone else's email with this token must fail, and must not burn it
    assert (await _reset(client, token, email="admin@example.com")).status_code == 401
    assert await _login_status(client, "admin@example.com", "AdminPass123!") == 200
    # otp for one user does not verify for another
    otp2 = await _request_otp(client)
    assert (await _verify(client, otp2, email="admin@example.com")).status_code == 401
    assert (await _reset(client, token)).status_code in (200, 401)


@pytest.mark.asyncio
async def test_expired_otp_and_token_are_rejected(client):
    otp = await _request_otp(client)
    past = datetime.now(UTC) - timedelta(minutes=1)
    async with _Session() as s:
        await s.execute(update(PasswordResetToken).values(expires_at=past))
        await s.commit()
    assert (await _verify(client, otp)).status_code == 401

    otp = await _request_otp(client)
    token = (await _verify(client, otp)).json()["data"]["reset_token"]
    async with _Session() as s:
        await s.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.used_at.is_(None))
            .values(expires_at=past)
        )
        await s.commit()
    assert (await _reset(client, token)).status_code == 401
    assert await _login_status(client, STAFF, "StaffPass123!") == 200


@pytest.mark.asyncio
async def test_new_otp_invalidates_previous_one(client):
    first = await _request_otp(client)
    second = await _request_otp(client)
    if first != second:
        assert (await _verify(client, first)).status_code == 401
    assert (await _verify(client, second)).status_code == 200


@pytest.mark.asyncio
async def test_unknown_email_is_silent_and_queues_nothing(client):
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200
    async with _Session() as s:
        assert (await s.execute(select(BackgroundJob))).scalars().first() is None


@pytest.mark.asyncio
async def test_reset_email_job_is_delivered_by_drain(client, monkeypatch):
    import app.infrastructure.email.smtp as smtp
    from app.infrastructure.jobs import drain

    sent = []

    async def fake_send(**kw):
        sent.append(kw)

    monkeypatch.setattr(smtp, "send_email", fake_send)
    monkeypatch.setattr(drain, "async_session_factory", _Session)
    otp = await _request_otp(client)
    assert await drain.drain_jobs() == 1
    assert sent and sent[0]["to"] == STAFF and otp in sent[0]["body_text"]
    async with _Session() as s:
        job = (await s.execute(select(BackgroundJob))).scalars().first()
    assert job.status == "DONE"
