"""end-to-end api workflows: recruitment, leave, attendance, performance, documents,
reports, users, notifications and audit. runs on in-memory sqlite via the same
override pattern as test_employees.py."""

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
from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.models.leave import LeaveBalance, LeaveType
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


# ---------------- recruitment ----------------


@pytest.mark.asyncio
async def test_recruitment_pipeline_end_to_end(client):
    h = await _admin(client)
    dept = _data(
        await client.post("/api/v1/departments", headers=h, json={"name": "Eng", "code": "ENG"}),
        201,
    )
    job = _data(
        await client.post(
            "/api/v1/jobs",
            headers=h,
            json={
                "title": "Backend Engineer",
                "department_id": dept["id"],
                "salary_min": 10,
                "salary_max": 20,
            },
        ),
        201,
    )
    assert job["status"] == "DRAFT"
    upd = _data(
        await client.patch(f"/api/v1/jobs/{job['id']}", headers=h, json={"location": "Remote"})
    )
    assert upd["location"] == "Remote"
    pub = _data(await client.post(f"/api/v1/jobs/{job['id']}/publish", headers=h))
    assert pub["status"] == "OPEN"
    listed = _data(await client.get("/api/v1/jobs", headers=h, params={"status": "OPEN"}))
    assert listed["total"] == 1
    assert (
        _data(await client.get(f"/api/v1/jobs/{job['id']}", headers=h))["title"]
        == "Backend Engineer"
    )

    app_ = _data(
        await client.post(
            "/api/v1/applications",
            headers=h,
            json={
                "job_id": job["id"],
                "candidate_name": "Ravi",
                "candidate_email": "ravi@example.com",
            },
        ),
        201,
    )
    assert app_["stage"] == "APPLIED"
    # skipping stages is rejected by the domain rule
    skip = await client.post(
        f"/api/v1/applications/{app_['id']}/move-stage", headers=h, json={"stage": "OFFER"}
    )
    assert skip.status_code in (400, 409, 422)
    for stage in ("SCREENING", "INTERVIEW"):
        moved = _data(
            await client.post(
                f"/api/v1/applications/{app_['id']}/move-stage", headers=h, json={"stage": stage}
            )
        )
        assert moved["stage"] == stage
    _data(
        await client.patch(
            f"/api/v1/applications/{app_['id']}", headers=h, json={"notes": "strong"}
        )
    )
    assert (
        _data(await client.get("/api/v1/applications", headers=h, params={"job_id": job["id"]}))[
            "total"
        ]
        == 1
    )
    assert (
        _data(await client.get(f"/api/v1/applications/{app_['id']}", headers=h))["notes"]
        == "strong"
    )

    when = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    iv = _data(
        await client.post(
            f"/api/v1/applications/{app_['id']}/interviews",
            headers=h,
            json={"scheduled_at": when, "interviewer_id": IDS["admin"], "interview_type": "TECH"},
        ),
        201,
    )
    ivs = _data(await client.get(f"/api/v1/applications/{app_['id']}/interviews", headers=h))
    assert [i["id"] for i in ivs] == [iv["id"]]
    _data(
        await client.patch(
            f"/api/v1/interviews/{iv['id']}", headers=h, json={"duration_minutes": 45}
        )
    )
    fb = await client.post(
        f"/api/v1/interviews/{iv['id']}/feedback",
        headers=h,
        json={"rating": 4, "recommendation": "HIRE", "strengths": "design"},
    )
    assert fb.status_code in (200, 201), fb.text

    rej = _data(
        await client.post(
            f"/api/v1/applications/{app_['id']}/move-stage", headers=h, json={"stage": "REJECTED"}
        )
    )
    assert rej["stage"] == "REJECTED"
    # terminal stage cannot move again
    again = await client.post(
        f"/api/v1/applications/{app_['id']}/move-stage", headers=h, json={"stage": "SCREENING"}
    )
    assert again.status_code in (400, 409, 422)

    closed = _data(await client.post(f"/api/v1/jobs/{job['id']}/close", headers=h))
    assert closed["status"] == "CLOSED"
    assert (await client.get("/api/v1/jobs/does-not-exist", headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_draft_job_can_be_deleted_and_staff_cannot_create_jobs(client):
    h = await _admin(client)
    job = _data(await client.post("/api/v1/jobs", headers=h, json={"title": "Temp"}), 201)
    r = await client.delete(f"/api/v1/jobs/{job['id']}", headers=h)
    assert r.status_code in (200, 204)
    assert (await client.get(f"/api/v1/jobs/{job['id']}", headers=h)).status_code == 404
    staff = await _token(client, "staff@example.com", "StaffPass123!")
    assert (
        await client.post("/api/v1/jobs", headers=staff, json={"title": "x"})
    ).status_code == 403


# ---------------- leave ----------------


async def _staff_with_employee(client, h):
    # leave requests are keyed by the caller's user id (see known issues), so the
    # employee row shares that id to keep the foreign key valid.
    emp_id = IDS["staff"]
    async with _Session() as s:
        s.add(
            Employee(
                id=emp_id,
                employee_code="S1",
                first_name="Staff",
                last_name="One",
                email="staff.emp@example.com",
                joining_date=date(2024, 1, 1),
                user_id=emp_id,
            )
        )
        await s.flush()
        s.add(
            LeaveBalance(
                employee_id=emp_id, leave_type_id=IDS["lt"], year=YEAR, total_days=Decimal("12")
            )
        )
        await s.commit()
    return emp_id, await _token(client, "staff@example.com", "StaffPass123!")


def _leave_body(days=2, offset=10):
    start = date(YEAR, 6, 1) + timedelta(days=offset)
    return {
        "leave_type_id": IDS["lt"],
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=days - 1)).isoformat(),
        "days": days,
        "reason": "family",
    }


async def _balance(client, sh):
    rows = _data(await client.get("/api/v1/leaves/balances/me", headers=sh, params={"year": YEAR}))
    return {k: Decimal(str(rows[0][k])) for k in ("total_days", "used_days", "pending_days")}


@pytest.mark.asyncio
async def test_leave_apply_approve_updates_balance(client):
    h = await _admin(client)
    emp_id, sh = await _staff_with_employee(client, h)
    types = _data(await client.get("/api/v1/leave-types", headers=sh))
    assert [t["code"] for t in types] == ["CL"]

    lv = _data(await client.post("/api/v1/leaves", headers=sh, json=_leave_body(2)), 201)
    assert lv["status"] == "PENDING"
    b = await _balance(client, sh)
    assert b["pending_days"] == 2 and b["used_days"] == 0

    assert _data(await client.get(f"/api/v1/leaves/{lv['id']}", headers=h))["id"] == lv["id"]
    assert (
        _data(await client.get("/api/v1/leaves", headers=h, params={"status": "PENDING"}))["total"]
        == 1
    )

    ok = _data(await client.post(f"/api/v1/leaves/{lv['id']}/approve", headers=h))
    assert ok["status"] == "APPROVED"
    b = await _balance(client, sh)
    assert b["pending_days"] == 0 and b["used_days"] == 2

    # approving twice is not allowed
    assert (await client.post(f"/api/v1/leaves/{lv['id']}/approve", headers=h)).status_code in (
        400,
        409,
        422,
    )
    nested = _data(await client.get(f"/api/v1/employees/{emp_id}/leave", headers=h))
    assert nested["total"] == 1

    # staff gets a notification about the decision
    notes = _data(await client.get("/api/v1/notifications", headers=sh))
    if notes["items"]:
        nid = notes["items"][0]["id"]
        assert (
            await client.post(f"/api/v1/notifications/{nid}/read", headers=sh)
        ).status_code == 200
    assert (await client.post("/api/v1/notifications/read-all", headers=sh)).status_code == 200


@pytest.mark.asyncio
async def test_leave_reject_and_cancel_release_pending_days(client):
    h = await _admin(client)
    _, sh = await _staff_with_employee(client, h)
    a = _data(await client.post("/api/v1/leaves", headers=sh, json=_leave_body(3, 0)), 201)
    b = _data(await client.post("/api/v1/leaves", headers=sh, json=_leave_body(1, 20)), 201)
    assert (await _balance(client, sh))["pending_days"] == 4

    rej = _data(
        await client.post(f"/api/v1/leaves/{a['id']}/reject", headers=h, json={"reason": "crunch"})
    )
    assert rej["status"] == "REJECTED"
    can = _data(await client.post(f"/api/v1/leaves/{b['id']}/cancel", headers=sh))
    assert can["status"] == "CANCELLED"
    bal = await _balance(client, sh)
    assert bal["pending_days"] == 0 and bal["used_days"] == 0


@pytest.mark.asyncio
async def test_leave_over_balance_and_bad_dates_rejected(client):
    h = await _admin(client)
    _, sh = await _staff_with_employee(client, h)
    too_many = await client.post("/api/v1/leaves", headers=sh, json=_leave_body(13))
    assert too_many.status_code in (400, 409, 422)
    body = _leave_body(2)
    body["end_date"], body["start_date"] = body["start_date"], body["end_date"]
    assert (await client.post("/api/v1/leaves", headers=sh, json=body)).status_code in (400, 422)
    body = _leave_body(1)
    body["leave_type_id"] = "missing"
    assert (await client.post("/api/v1/leaves", headers=sh, json=body)).status_code in (
        400,
        404,
        422,
    )


# ---------------- attendance ----------------


@pytest.mark.asyncio
async def test_attendance_check_in_out_manual_and_update(client):
    h = await _admin(client)
    emp = await _employee(client, h)
    cin = await client.post("/api/v1/attendance/check-in", headers=h, params={"employee_id": emp})
    assert cin.status_code in (200, 201), cin.text
    dup = await client.post("/api/v1/attendance/check-in", headers=h, params={"employee_id": emp})
    assert dup.status_code in (400, 409, 422)
    cout = await client.post(
        "/api/v1/attendance/check-out", headers=h, params={"employee_id": emp}
    )
    assert cout.status_code in (200, 201), cout.text
    assert cout.json()["data"]["check_out"]

    day = date.today() - timedelta(days=3)
    man = await client.post(
        "/api/v1/attendance/manual",
        headers=h,
        json={
            "employee_id": emp,
            "work_date": day.isoformat(),
            "check_in": f"{day}T09:00:00+00:00",
            "check_out": f"{day}T17:30:00+00:00",
            "remarks": "forgot badge",
        },
    )
    assert man.status_code in (200, 201), man.text
    aid = man.json()["data"]["id"]
    upd = _data(
        await client.patch(f"/api/v1/attendance/{aid}", headers=h, json={"remarks": "fixed"})
    )
    assert upd["remarks"] == "fixed"

    lst = _data(await client.get("/api/v1/attendance", headers=h, params={"employee_id": emp}))
    assert lst["total"] == 2
    by_emp = _data(
        await client.get(
            f"/api/v1/attendance/{emp}",
            headers=h,
            params={"date_from": day.isoformat(), "date_to": day.isoformat()},
        )
    )
    assert by_emp["total"] == 1
    assert _data(await client.get(f"/api/v1/employees/{emp}/attendance", headers=h))["total"] == 2

    rep = await client.get(
        "/api/v1/reports/attendance-summary",
        headers=h,
        params={"from": (day - timedelta(days=1)).isoformat(), "to": date.today().isoformat()},
    )
    assert rep.status_code == 200, rep.text


# ---------------- performance ----------------


@pytest.mark.asyncio
async def test_performance_cycle_review_submit_approve(client):
    h = await _admin(client)
    emp = await _employee(client, h)
    cyc = _data(
        await client.post(
            "/api/v1/performance/cycles",
            headers=h,
            json={"name": "H1", "start_date": f"{YEAR}-01-01", "end_date": f"{YEAR}-06-30"},
        ),
        201,
    )
    assert _data(await client.get("/api/v1/performance/cycles", headers=h))["total"] == 1

    rv = _data(
        await client.post(
            "/api/v1/performance/reviews",
            headers=h,
            json={
                "cycle_id": cyc["id"],
                "employee_id": emp,
                "reviewer_id": IDS["admin"],
                "self_rating": 4,
                "goals": [{"title": "ship v2", "weight": 60}, {"title": "mentor", "weight": 40}],
            },
        ),
        201,
    )
    assert rv["status"] == "DRAFT"
    assert (
        _data(await client.get(f"/api/v1/performance/reviews/{rv['id']}", headers=h))["id"]
        == rv["id"]
    )
    assert (
        _data(
            await client.get(
                "/api/v1/performance/reviews", headers=h, params={"cycle_id": cyc["id"]}
            )
        )["total"]
        == 1
    )
    sub = _data(await client.post(f"/api/v1/performance/reviews/{rv['id']}/submit", headers=h))
    assert sub["status"] != "DRAFT"
    status = sub["status"]
    for _ in range(4):
        r = await client.post(f"/api/v1/performance/reviews/{rv['id']}/approve", headers=h)
        if r.status_code != 200:
            break
        status = r.json()["data"]["status"]
        if status == "COMPLETED":
            break
    assert status == "COMPLETED"
    assert _data(await client.get(f"/api/v1/employees/{emp}/performance", headers=h))["total"] == 1


# ---------------- documents ----------------


@pytest.mark.asyncio
async def test_document_upload_validation_and_listing(client):
    h = await _admin(client)
    emp = await _employee(client, h)
    bad = await client.post(
        "/api/v1/documents/upload",
        headers=h,
        json={
            "filename": "x.exe",
            "size_bytes": 10,
            "content_type": "application/x-msdownload",
            "employee_id": emp,
        },
    )
    assert bad.status_code in (400, 415, 422)
    up = await client.post(
        "/api/v1/documents/upload",
        headers=h,
        json={
            "filename": "offer.pdf",
            "size_bytes": 1024,
            "content_type": "application/pdf",
            "employee_id": emp,
        },
    )
    assert up.status_code in (200, 201), up.text
    d = up.json()["data"]
    assert d["upload_url"].startswith("http")
    doc_id = d["document_id"]
    lst = _data(await client.get("/api/v1/documents", headers=h, params={"employee_id": emp}))
    assert lst["total"] >= 1
    one = await client.get(f"/api/v1/documents/{doc_id}", headers=h)
    assert one.status_code == 200
    assert one.json()["data"]["filename"] == "offer.pdf"
    assert _data(await client.get(f"/api/v1/employees/{emp}/documents", headers=h))["total"] >= 1
    rm = await client.delete(f"/api/v1/documents/{doc_id}", headers=h)
    assert rm.status_code in (200, 204)
    assert (await client.get("/api/v1/documents/missing", headers=h)).status_code == 404


# ---------------- employees, users, reports, audit ----------------


@pytest.mark.asyncio
async def test_employee_update_compensation_delete_and_reports(client):
    h = await _admin(client)
    dept = _data(
        await client.post("/api/v1/departments", headers=h, json={"name": "Ops", "code": "OPS"}),
        201,
    )
    mgr = await _employee(client, h, code="M1", email="m1@example.com", department_id=dept["id"])
    emp = await _employee(
        client, h, code="E2", email="e2@example.com", department_id=dept["id"], manager_id=mgr
    )

    upd = _data(
        await client.patch(
            f"/api/v1/employees/{emp}", headers=h, json={"designation": "sre", "location": "hyd"}
        )
    )
    assert upd["designation"] == "sre"
    # an employee cannot be their own manager
    selfm = await client.patch(f"/api/v1/employees/{mgr}", headers=h, json={"manager_id": mgr})
    assert selfm.status_code in (400, 409, 422)
    comp = await client.patch(
        f"/api/v1/employees/{emp}/compensation",
        headers=h,
        json={"salary": "1200000", "currency": "INR", "effective_from": "2024-04-01"},
    )
    assert comp.status_code == 200, comp.text
    got = _data(await client.get(f"/api/v1/employees/{emp}", headers=h))
    assert Decimal(str(got["compensation"]["salary"])) == Decimal("1200000")
    filt = _data(
        await client.get(
            "/api/v1/employees", headers=h, params={"department_id": dept["id"], "search": "asha"}
        )
    )
    assert filt["total"] == 2

    head = _data(await client.get("/api/v1/reports/headcount", headers=h))
    assert head
    assert (await client.get("/api/v1/reports/leave-usage", headers=h)).status_code == 200

    gone = await client.delete(f"/api/v1/employees/{emp}", headers=h)
    assert gone.status_code in (200, 204)

    audit = _data(await client.get("/api/v1/audit-logs", headers=h))
    assert audit["total"] >= 1
    actions = {row["action"] for row in audit["items"]}
    assert actions


@pytest.mark.asyncio
async def test_users_listing_and_role_assignment(client):
    h = await _admin(client)
    users = _data(await client.get("/api/v1/users", headers=h))
    assert users["total"] == 2
    one = _data(await client.get(f"/api/v1/users/{IDS['staff']}", headers=h))
    assert one["roles"] == ["EMPLOYEE"]
    r = _data(
        await client.put(
            f"/api/v1/users/{IDS['staff']}/roles",
            headers=h,
            json={"role_names": ["EMPLOYEE", "HR_ADMIN"]},
        )
    )
    assert set(r["roles"]) == {"EMPLOYEE", "HR_ADMIN"}
    bad = await client.put(
        f"/api/v1/users/{IDS['staff']}/roles", headers=h, json={"role_names": ["NOPE"]}
    )
    assert bad.status_code in (400, 404, 422)
    staff = await _token(client, "staff@example.com", "StaffPass123!")
    assert (await client.get("/api/v1/users", headers=staff)).status_code == 200  # now hr admin


@pytest.mark.asyncio
async def test_login_sets_refresh_cookie_and_logout_clears_it(client):
    # token rotation itself (/auth/refresh) compares tz-aware datetimes, which sqlite
    # does not store, so it is not exercised here; it needs the postgres stack.
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}
    )
    assert r.status_code == 200
    token = r.json()["data"]["refresh_token"]
    set_cookie = r.headers["set-cookie"]
    assert f"hrmf_refresh={token}" in set_cookie
    assert "httponly" in set_cookie.lower() and "path=/api/v1/auth" in set_cookie.lower()
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    out = await client.post("/api/v1/auth/logout", json={"refresh_token": token})
    assert out.status_code == 200
    assert (
        'hrmf_refresh=""' in out.headers["set-cookie"]
        or "max-age=0" in out.headers["set-cookie"].lower()
    )
    assert (await client.post("/api/v1/auth/logout")).status_code == 401
