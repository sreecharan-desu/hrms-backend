"""error paths, permission checks, otp verification and the outbox drain."""

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


# ---------------- not found / conflict / forbidden ----------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/employees/nope"),
        ("patch", "/api/v1/employees/nope"),
        ("delete", "/api/v1/employees/nope"),
        ("get", "/api/v1/departments/nope"),
        ("patch", "/api/v1/departments/nope"),
        ("delete", "/api/v1/departments/nope"),
        ("get", "/api/v1/leaves/nope"),
        ("post", "/api/v1/leaves/nope/approve"),
        ("post", "/api/v1/leaves/nope/cancel"),
        ("get", "/api/v1/applications/nope"),
        ("patch", "/api/v1/applications/nope"),
        ("patch", "/api/v1/jobs/nope"),
        ("post", "/api/v1/jobs/nope/publish"),
        ("post", "/api/v1/jobs/nope/close"),
        ("delete", "/api/v1/jobs/nope"),
        ("get", "/api/v1/performance/reviews/nope"),
        ("post", "/api/v1/performance/reviews/nope/submit"),
        ("post", "/api/v1/performance/reviews/nope/approve"),
        ("patch", "/api/v1/attendance/nope"),
        ("post", "/api/v1/documents/nope/confirm"),
        ("delete", "/api/v1/documents/nope"),
        ("get", "/api/v1/users/nope"),
        ("patch", "/api/v1/interviews/nope"),
        ("post", "/api/v1/notifications/nope/read"),
    ],
)
async def test_unknown_ids_return_404(client, method, path):
    h = await _admin(client)
    kw = {"json": {}} if method in ("patch",) else {}
    r = await getattr(client, method)(path, headers=h, **kw)
    assert r.status_code == 404, (path, r.status_code, r.text)
    assert r.json()["success"] is False


@pytest.mark.asyncio
async def test_staff_is_forbidden_from_hr_actions(client):
    h = await _admin(client)
    emp = await _employee(client, h)
    sh = await _token(client, "staff@example.com", "StaffPass123!")
    for method, path, body in [
        ("get", "/api/v1/users", None),
        ("put", f"/api/v1/users/{IDS['admin']}/roles", {"role_names": ["EMPLOYEE"]}),
        ("patch", f"/api/v1/employees/{emp}", {"designation": "x"}),
        ("delete", f"/api/v1/employees/{emp}", None),
        ("patch", f"/api/v1/employees/{emp}/compensation", {"salary": "1", "currency": "INR"}),
        ("post", "/api/v1/departments", {"name": "x", "code": "X"}),
        (
            "post",
            "/api/v1/performance/cycles",
            {"name": "c", "start_date": "2026-01-01", "end_date": "2026-02-01"},
        ),
        ("get", "/api/v1/audit-logs", None),
        ("post", "/api/v1/attendance/manual", {"employee_id": emp, "work_date": "2026-01-02"}),
    ]:
        kw = {"json": body} if body is not None else {}
        r = await getattr(client, method)(path, headers=sh, **kw)
        assert r.status_code == 403, (method, path, r.status_code, r.text)


@pytest.mark.asyncio
async def test_duplicates_and_invalid_updates_conflict(client):
    h = await _admin(client)
    d1 = _data(
        await client.post("/api/v1/departments", headers=h, json={"name": "A", "code": "A"}), 201
    )
    d2 = _data(
        await client.post(
            "/api/v1/departments",
            headers=h,
            json={"name": "B", "code": "B", "parent_id": d1["id"]},
        ),
        201,
    )
    dup = await client.post("/api/v1/departments", headers=h, json={"name": "A2", "code": "A"})
    assert dup.status_code == 409
    # parent cycle: A under its own child B
    cyc = await client.patch(
        f"/api/v1/departments/{d1['id']}", headers=h, json={"parent_id": d2["id"]}
    )
    assert cyc.status_code in (400, 409, 422)
    selfp = await client.patch(
        f"/api/v1/departments/{d1['id']}", headers=h, json={"parent_id": d1["id"]}
    )
    assert selfp.status_code in (400, 409, 422)
    ren = _data(
        await client.patch(
            f"/api/v1/departments/{d2['id']}", headers=h, json={"name": "B2", "code": "B2"}
        )
    )
    assert ren["name"] == "B2"
    kids = _data(await client.get(f"/api/v1/departments/{d1['id']}/children", headers=h))
    assert [k["id"] for k in kids] == [d2["id"]]
    clash = await client.patch(f"/api/v1/departments/{d2['id']}", headers=h, json={"code": "A"})
    assert clash.status_code == 409
    assert (await client.delete(f"/api/v1/departments/{d2['id']}", headers=h)).status_code in (
        200,
        204,
    )

    e1 = await _employee(client, h, code="X1", email="x1@example.com")
    e2 = await _employee(client, h, code="X2", email="x2@example.com", manager_id=e1)
    again = await client.post(
        "/api/v1/employees",
        headers=h,
        json={
            "employee_code": "X1",
            "first_name": "a",
            "last_name": "b",
            "email": "x9@example.com",
            "joining_date": "2024-01-01",
        },
    )
    assert again.status_code == 409
    # manager cycle: e1 reporting to e2 who reports to e1
    loop = await client.patch(f"/api/v1/employees/{e1}", headers=h, json={"manager_id": e2})
    assert loop.status_code in (400, 409, 422)
    taken = await client.patch(
        f"/api/v1/employees/{e2}", headers=h, json={"email": "x1@example.com"}
    )
    assert taken.status_code == 409
    nodept = await client.patch(
        f"/api/v1/employees/{e2}", headers=h, json={"department_id": "missing"}
    )
    assert nodept.status_code in (400, 404, 422)
    ok = _data(
        await client.patch(
            f"/api/v1/employees/{e2}", headers=h, json={"phone": "999", "status": "INACTIVE"}
        )
    )
    assert ok["phone"] == "999"
    assert (
        _data(await client.get("/api/v1/employees", headers=h, params={"status": "INACTIVE"}))[
            "total"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_recruitment_state_rules(client):
    h = await _admin(client)
    job = _data(await client.post("/api/v1/jobs", headers=h, json={"title": "QA"}), 201)
    # cannot apply to a draft job
    r = await client.post(
        "/api/v1/applications",
        headers=h,
        json={"job_id": job["id"], "candidate_name": "a", "candidate_email": "a@example.com"},
    )
    assert r.status_code in (400, 409, 422)
    _data(await client.post(f"/api/v1/jobs/{job['id']}/publish", headers=h))
    assert (await client.post(f"/api/v1/jobs/{job['id']}/publish", headers=h)).status_code in (
        400,
        409,
        422,
    )
    a = _data(
        await client.post(
            "/api/v1/applications",
            headers=h,
            json={"job_id": job["id"], "candidate_name": "a", "candidate_email": "a@example.com"},
        ),
        201,
    )
    bogus = await client.post(
        f"/api/v1/applications/{a['id']}/move-stage", headers=h, json={"stage": "NOPE"}
    )
    assert bogus.status_code in (400, 422)
    for st in ("SCREENING", "INTERVIEW", "TECHNICAL", "HR", "OFFER", "HIRED"):
        _data(
            await client.post(
                f"/api/v1/applications/{a['id']}/move-stage", headers=h, json={"stage": st}
            )
        )
    assert (
        _data(await client.get("/api/v1/applications", headers=h, params={"stage": "HIRED"}))[
            "total"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_attendance_checkout_without_checkin_is_404(client):
    h = await _admin(client)
    emp = await _employee(client, h)
    r = await client.post("/api/v1/attendance/check-out", headers=h, params={"employee_id": emp})
    assert r.status_code == 404


# ---------------- otp ----------------


@pytest.mark.asyncio
async def test_forgot_password_is_silent_and_otp_verifies_once(client, monkeypatch):
    import app.application.auth.forgot_password as fp
    import app.application.auth.verify_otp as vo

    store: dict[str, str] = {}

    async def _store(email, h):
        store[email] = h

    async def _get(email):
        return store.get(email)

    async def _del(email):
        store.pop(email, None)

    monkeypatch.setattr(fp, "store_otp", _store)
    monkeypatch.setattr(vo, "get_stored_otp", _get)
    monkeypatch.setattr(vo, "delete_otp", _del)
    sent: list[str] = []
    real = fp._generate_otp
    monkeypatch.setattr(
        fp, "_generate_otp", lambda length=6: sent.append(real(length)) or sent[-1]
    )

    unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert unknown.status_code == 200 and not sent  # no enumeration, nothing generated
    ok = await client.post("/api/v1/auth/forgot-password", json={"email": "staff@example.com"})
    assert ok.status_code == 200 and len(sent) == 1 and len(sent[0]) == 6

    wrong = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "staff@example.com", "otp": "000000" if sent[0] != "000000" else "111111"},
    )
    assert wrong.status_code == 401
    good = await client.post(
        "/api/v1/auth/verify-otp", json={"email": "staff@example.com", "otp": sent[0]}
    )
    assert good.status_code == 200 and len(good.json()["data"]["reset_token"]) > 40
    # redis entry is consumed; the db fallback only accepts the hash for the right user
    other = await client.post(
        "/api/v1/auth/verify-otp", json={"email": "admin@example.com", "otp": sent[0]}
    )
    assert other.status_code == 401


# ---------------- outbox drain ----------------


@pytest.mark.asyncio
async def test_drain_dispatches_marks_and_retries(monkeypatch):
    from sqlalchemy import select

    from app.infrastructure.database.models.jobs import BackgroundJob
    from app.infrastructure.jobs import drain

    calls: list[dict] = []

    async def ok(payload):
        calls.append(payload)

    async def boom(payload):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(drain, "async_session_factory", _Session)
    monkeypatch.setattr(drain, "HANDLER_MAP", {"ok": ok, "boom": boom})
    now = datetime.now(UTC) - timedelta(seconds=5)
    async with _Session() as s:
        s.add_all(
            [
                BackgroundJob(type="ok", payload={"n": 1}, status="PENDING", available_at=now),
                BackgroundJob(type="boom", payload={}, status="PENDING", available_at=now),
                BackgroundJob(type="mystery", payload={}, status="PENDING", available_at=now),
                BackgroundJob(
                    type="ok",
                    payload={"n": 2},
                    status="PENDING",
                    available_at=now + timedelta(days=1),
                ),
            ]
        )
        await s.commit()

    assert await drain.drain_jobs() == 3
    assert calls == [{"n": 1}]
    async with _Session() as s:
        rows = {
            j.type + str((j.payload or {}).get("n", "")): j
            for j in (await s.execute(select(BackgroundJob))).scalars()
        }
    assert rows["ok1"].status == "DONE"
    assert rows["mystery"].status == "FAILED" and "Unknown job type" in rows["mystery"].last_error
    assert (
        rows["boom"].status == "PENDING"
        and rows["boom"].attempts == 1
        and "smtp down" in rows["boom"].last_error
    )
    assert rows["ok2"].status == "PENDING"  # not yet available

    # two more failures exhaust the retry budget
    assert await drain.drain_jobs() == 1
    assert await drain.drain_jobs() == 1
    async with _Session() as s:
        boom_job = (
            await s.execute(select(BackgroundJob).where(BackgroundJob.type == "boom"))
        ).scalar_one()
    assert boom_job.status == "FAILED" and boom_job.attempts == 3
    assert await drain.drain_jobs() == 0
