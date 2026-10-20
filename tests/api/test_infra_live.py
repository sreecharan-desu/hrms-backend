"""infrastructure: redis helpers against a real local redis-server, smtp sender,
internal cron/readiness endpoints and login lockout."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["APP_ENV"] = "development"
os.environ.setdefault("STORAGE_BUCKET", "hrms-test")
os.environ.setdefault("STORAGE_ACCESS_KEY", "test")
os.environ.setdefault("STORAGE_SECRET_KEY", "test")

from datetime import date
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


import shutil
import socket
import subprocess
import time

import app.infrastructure.cache.redis as rc
from app.core.config import get_settings


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def redis_url():
    exe = shutil.which("redis-server")
    if not exe:
        pytest.skip("redis-server not installed")
    port = _free_port()
    proc = subprocess.Popen(
        [exe, "--port", str(port), "--save", "", "--appendonly", "no"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    yield f"redis://127.0.0.1:{port}/0"
    proc.terminate()
    proc.wait(timeout=5)


@pytest_asyncio.fixture
async def live_redis(redis_url, monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", redis_url)
    rc._client = None
    r = await rc.get_redis()
    assert r is not None
    await r.flushdb()
    yield r
    await rc.close_redis()


@pytest.mark.asyncio
async def test_redis_unavailable_degrades_to_noop(monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", f"redis://127.0.0.1:{_free_port()}/0")
    rc._client = None
    assert await rc.get_redis() is None
    await rc.cache_user_permissions("u", {"a"})
    assert await rc.get_cached_permissions("u") is None
    assert await rc.check_login_lockout("e", "ip") is False
    await rc.record_failed_login("e", "ip")
    await rc.store_otp("e", "h")
    assert await rc.get_stored_otp("e") is None


@pytest.mark.asyncio
async def test_permission_cache_and_otp_roundtrip(live_redis):
    await rc.cache_user_permissions("u1", {"b", "a"})
    assert await rc.get_cached_permissions("u1") == {"a", "b"}
    assert 0 < await live_redis.ttl("user:u1:permissions") <= 300
    await rc.invalidate_user_permissions("u1")
    assert await rc.get_cached_permissions("u1") is None
    await rc.store_otp("a@x.com", "hash")
    assert await rc.get_stored_otp("a@x.com") == "hash"
    await rc.delete_otp("a@x.com")
    assert await rc.get_stored_otp("a@x.com") is None


@pytest.mark.asyncio
async def test_login_lockout_after_five_failures(live_redis, client):
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-pass"}
        )
        assert r.status_code == 401
    locked = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}
    )
    assert locked.status_code in (401, 423, 429)
    assert len(await live_redis.keys("login_lockout:admin@example.com:*")) == 1
    await live_redis.flushdb()
    ok = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_admin_cache_clear_and_readiness(live_redis, client, monkeypatch):
    monkeypatch.setattr(get_settings(), "INTERNAL_API_TOKEN", "itok")
    import app.presentation.api.internal.ready as ready

    monkeypatch.setattr(ready, "async_session_factory", _Session)
    h = await _admin(client)
    await rc.cache_user_permissions("x1", {"p"})
    await rc.cache_user_permissions("x2", {"p"})
    assert (await client.post("/internal/admin/cache/clear", headers=h)).status_code == 401
    r = await client.post("/internal/admin/cache/clear", headers={**h, "X-Internal-Token": "itok"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["cleared"] >= 2
    assert await live_redis.keys("user:*:permissions") == []

    assert (await client.get("/internal/ready")).status_code == 401
    ok = await client.get("/internal/ready", headers={"X-Internal-Token": "itok"})
    assert ok.status_code == 200 and ok.json()["data"]["checks"] == {
        "postgres": "ok",
        "redis": "ok",
    }


@pytest.mark.asyncio
async def test_readiness_reports_degraded_without_redis(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "INTERNAL_API_TOKEN", "itok")
    monkeypatch.setattr(get_settings(), "REDIS_URL", f"redis://127.0.0.1:{_free_port()}/0")
    import app.presentation.api.internal.ready as ready

    monkeypatch.setattr(ready, "async_session_factory", _Session)
    rc._client = None
    r = await client.get("/internal/ready", headers={"X-Internal-Token": "itok"})
    assert r.status_code == 503
    assert r.json()["data"]["checks"]["redis"] == "unavailable"


@pytest.mark.asyncio
async def test_cron_drain_requires_secret(client, monkeypatch):
    import app.infrastructure.jobs.drain as drain

    monkeypatch.setattr(drain, "async_session_factory", _Session)
    monkeypatch.setattr(get_settings(), "CRON_SECRET", "")
    assert (await client.post("/internal/jobs/drain")).status_code == 401
    monkeypatch.setattr(get_settings(), "CRON_SECRET", "s3cret")
    assert (
        await client.post("/internal/jobs/drain", headers={"Authorization": "Bearer nope"})
    ).status_code == 401
    a = await client.post("/internal/jobs/drain", headers={"Authorization": "Bearer s3cret"})
    b = await client.post("/internal/jobs/drain", headers={"X-Cron-Secret": "s3cret"})
    assert a.status_code == b.status_code == 200
    assert a.json()["data"] == {"processed": 0}


class _FakeSMTP:
    sent: list = []
    fail = False

    def __init__(self, host, port, timeout):
        self.host, self.port = host, port
        self.logged_in = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, pw):
        self.logged_in = user

    def send_message(self, msg):
        if _FakeSMTP.fail:
            raise OSError("connection reset")
        _FakeSMTP.sent.append((self.host, self.logged_in, msg))


@pytest.mark.asyncio
async def test_smtp_send_stub_real_and_failure(monkeypatch):
    import app.infrastructure.email.smtp as smtp

    s = get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "")
    await smtp.send_email(to="a@x.com", subject="hi", body_text="t")  # logged only

    monkeypatch.setattr(smtp.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(s, "SMTP_USER", "mailer")
    _FakeSMTP.sent.clear()
    await smtp.send_email(to="a@x.com", subject="hello", body_text="plain", body_html="<b>x</b>")
    host, user, msg = _FakeSMTP.sent[0]
    assert host == "smtp.test" and user == "mailer"
    assert msg["To"] == "a@x.com" and msg["Subject"] == "hello"
    assert msg.is_multipart()

    _FakeSMTP.fail = True
    with pytest.raises(OSError):
        await smtp.send_email(to="a@x.com", subject="x", body_text="y")
    _FakeSMTP.fail = False

    # the email.send job handler routes payloads to the same sender
    from app.infrastructure.jobs.handlers import HANDLER_MAP

    await HANDLER_MAP["email.send"]({"to": "b@x.com", "subject": "s", "body_text": "b"})
    assert _FakeSMTP.sent[-1][2]["To"] == "b@x.com"
    await HANDLER_MAP["sms.send"]({"phone": "1", "message": "m"})


@pytest.mark.asyncio
async def test_otp_attempts_are_limited_per_email(live_redis, client):
    await client.post("/api/v1/auth/forgot-password", json={"email": "staff@example.com"})
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/verify-otp", json={"email": "staff@example.com", "otp": "abcdef"}
        )
        assert r.status_code == 401
    blocked = await client.post(
        "/api/v1/auth/verify-otp", json={"email": "staff@example.com", "otp": "abcdef"}
    )
    assert blocked.status_code == 401 and "Too many" in blocked.text
    assert await live_redis.get("otp_fail:staff@example.com") == "5"
    # other emails are unaffected
    assert await rc.otp_attempts_exceeded("admin@example.com") is False
