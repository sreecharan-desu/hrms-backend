# HRMF: HR Management Framework (backend)

HR API built with FastAPI, async SQLAlchemy 2, PostgreSQL (Neon), Redis and S3. It uses a clean-architecture layout: presentation, application, domain, infrastructure.

**Live API:** https://hrms-backend-silk.vercel.app · **Frontend contract:** [docs/FRONTEND.md](docs/FRONTEND.md)

## Features

| Module | Scope |
|---|---|
| Auth | Login, rotating refresh token (HttpOnly cookie or body), logout, forgot/reset password with OTP |
| Employees, Departments | CRUD, compensation, department hierarchy with cycle checks |
| Attendance, Leave | Check-in/out, manual entries, leave apply/approve/reject/cancel, balances |
| Documents | Presigned S3 upload (initiate, PUT, confirm) |
| Recruitment, Performance | Jobs, applications, stage pipeline, interviews; review cycles |
| Notifications, Audit, Reports | Read/unread, immutable audit log, headcount/attendance/leave reports |
| RBAC | 8 roles mapped to fine-grained permissions (`app/core/permissions.py`), cached per user in Redis |

## Architecture

```
presentation    FastAPI routers, Pydantic schemas, middleware   /api/v1/*, /internal/*
application     use-cases, policies, audit logging
domain          entities, enums, repository interfaces
infrastructure  SQLAlchemy repos + unit of work, Redis cache, S3, ARQ worker, SMTP
```

Deployed as a Vercel Python function (`api/index.py`). A Vercel cron drains background jobs every 5 minutes via `/internal/jobs/drain`.

## Setup

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), PostgreSQL 15+ and Redis 7+ (MinIO/S3 for documents).

```bash
cp .env.example .env              # DATABASE_URL (pooled), DATABASE_URL_UNPOOLED (direct, for Alembic), JWT secret, ...
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py            # permissions, roles, dev admin, leave types (refuses APP_ENV=production)
uvicorn app.main:app --reload     # http://localhost:8000, Swagger at /docs outside production
```

Or use `docker compose up -d` (API, worker, Redis, MinIO; `--profile test` adds Postgres on 5433).

## Tests

```bash
pytest -q                  # unit + API tests on in-memory SQLite, no services needed
ruff check app tests && mypy app
```

Measured 19 Oct 2026: **199 passed in 9.4 s, 57% line coverage** (`pytest --cov=app`, [raw output](benchmarks/results-2026-10-19/pytest-coverage.txt)). CI (`.github/workflows/ci.yml`) runs lint, mypy, migrations against Postgres, tests and a Docker build.

## Performance (measured)

Single run on one 8 vCPU / 15 GiB VM (Intel Xeon), with **k6 on the same machine as the server**. The server was `uvicorn --workers 4` with local PostgreSQL 17 and Redis 7, and the database held 200 employees. Closed-loop VUs, no think time. Full method and environment: [benchmarks/README.md](benchmarks/README.md). Raw data: [k6 output](benchmarks/results-2026-10-19/k6-output.txt), [summary JSON](benchmarks/results-2026-10-19/k6-summary.json).

| Endpoint | Concurrency (VUs) | Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Error rate |
|---|---|---|---|---|---|---|---|---|
| `GET /employees` | 50 | 23,950 | 798 | 64.8 | 106.3 | 144.6 | 187.0 | 0.00% |
| `GET /auth/me` | 50 | 38,914 | 1,297 | 34.6 | 71.1 | 89.4 | 143.0 | 0.00% |
| `POST /auth/login` | 20 | 939 | 47 | 427.4 | 623.0 | 715.1 | 894.4 | 0.00% |

- Sustained **798 req/s at p95 106 ms** on the paginated employee list (50 VUs) on that hardware.
- Login is CPU-bound by design (argon2 password hashing): 47 logins/s at p95 623 ms.
- Cold start (process launch to first healthy response, 4 workers): **957 ms**. Memory (RSS, master + 4 workers): **445 MB idle, 520 MB under load**.
- These are local numbers. Production on Vercel + Neon adds network round-trips and serverless cold starts, which this run didn't measure.

Reproduce: `benchmarks/run.sh`.

## Auth model

- `POST /api/v1/auth/login` returns a 15-minute JWT access token and sets the `hrmf_refresh` HttpOnly cookie (path `/api/v1/auth`, SameSite=None, Secure in production).
- Refresh tokens are opaque and stored as SHA-256 hashes. They rotate on every `/auth/refresh`.
- Mobile (Expo) clients use `refresh_token` from the JSON body and keep it in SecureStore.

## Known issues

- No LICENSE file yet. All rights reserved until one is added.
- Coverage is uneven: `reports` (43%), `recruitment` (50%) and `leave` (51%) routers are the least tested ([coverage report](benchmarks/results-2026-10-19/pytest-coverage.txt)).
- The benchmark doesn't cover the production setup (Vercel + Neon) or write-heavy endpoints beyond the 200-row seed.
- Every request is logged at INFO level through structlog. That's included in the numbers above.
