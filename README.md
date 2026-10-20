# hrms-backend

hr management api built with fastapi, async sqlalchemy 2, postgres (neon), redis and s3, in a clean-architecture layout.

live api docs: https://hrms-backend-silk.vercel.app/docs · frontend contract: [docs/FRONTEND.md](docs/FRONTEND.md)

## features

- auth: login, rotating refresh token (http-only cookie or body), logout, otp password reset
- employees and departments: crud, compensation, department hierarchy with cycle checks
- attendance and leave: check-in/out, manual entries, apply/approve/reject/cancel, balances
- documents: presigned s3 upload (initiate, put, confirm)
- recruitment and performance: jobs, applications, stage pipeline, interviews, review cycles
- notifications, immutable audit log, headcount/attendance/leave reports
- rbac: 8 roles mapped to fine-grained permissions (`app/core/permissions.py`), cached per user in redis

## stack

fastapi · python 3.12 · async sqlalchemy 2 · alembic · postgres · redis · s3/minio · arq worker · deployed as a vercel python function (`api/index.py`) with a cron that drains jobs via `/internal/jobs/drain`.

```
presentation    fastapi routers, pydantic schemas, middleware   /api/v1/*, /internal/*
application     use-cases, policies, audit logging
domain          entities, enums, repository interfaces
infrastructure  sqlalchemy repos + unit of work, redis cache, s3, arq worker, smtp
```

## run locally

needs python 3.12+, [uv](https://docs.astral.sh/uv/), postgres 15+ and redis 7+ (minio/s3 for documents).

```bash
cp .env.example .env
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py            # permissions, roles, dev admin, leave types (refuses APP_ENV=production)
uvicorn app.main:app --reload     # http://localhost:8000, swagger at /docs outside production
```

or `docker compose up -d` (api, worker, redis, minio; `--profile test` adds postgres on 5433).

tests:

```bash
pytest -q                  # unit + api tests on in-memory sqlite, no services needed
ruff check app tests && mypy app
```

measured 19 oct 2026: 199 passed in 9.4 s, 57% line coverage ([raw output](benchmarks/results-2026-10-19/pytest-coverage.txt)).

## env

copy `.env.example` to `.env`. it needs `DATABASE_URL` (pooled), `DATABASE_URL_UNPOOLED` (direct, for alembic) and a jwt secret.

## performance (measured)

single run on one 8 vCPU / 15 GiB VM (Intel Xeon), with **k6 on the same machine as the server**. the server was `uvicorn --workers 4` with local PostgreSQL 17 and Redis 7, and the database held 200 employees. closed-loop VUs, no think time. full method and environment: [benchmarks/README.md](benchmarks/README.md). raw data: [k6 output](benchmarks/results-2026-10-19/k6-output.txt), [summary JSON](benchmarks/results-2026-10-19/k6-summary.json).

| endpoint | concurrency (VUs) | requests | throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | error rate |
|---|---|---|---|---|---|---|---|---|
| `GET /employees` | 50 | 23,950 | 798 | 64.8 | 106.3 | 144.6 | 187.0 | 0.00% |
| `GET /auth/me` | 50 | 38,914 | 1,297 | 34.6 | 71.1 | 89.4 | 143.0 | 0.00% |
| `POST /auth/login` | 20 | 939 | 47 | 427.4 | 623.0 | 715.1 | 894.4 | 0.00% |

- sustained **798 req/s at p95 106 ms** on the paginated employee list (50 VUs) on that hardware.
- login is CPU-bound by design (argon2 password hashing): 47 logins/s at p95 623 ms.
- cold start (process launch to first healthy response, 4 workers): **957 ms**. memory (RSS, master + 4 workers): **445 MB idle, 520 MB under load**.
- these are local numbers. production on Vercel + Neon adds network round-trips and serverless cold starts, which this run didn't measure.

reproduce: `benchmarks/run.sh`.

## auth model

- `POST /api/v1/auth/login` returns a 15-minute jwt access token and sets the `hrmf_refresh` http-only cookie (path `/api/v1/auth`, `SameSite=None`, secure in production).
- refresh tokens are opaque, stored as sha-256 hashes, and rotate on every `/auth/refresh`.
- expo clients send `refresh_token` in the json body and keep it in securestore.

## known issues

- no license file yet. all rights reserved until one is added.
- coverage is uneven: `reports` (43%), `recruitment` (50%) and `leave` (51%) routers are the least tested.
- the benchmark doesn't cover the production setup (vercel + neon) or write-heavy endpoints.
