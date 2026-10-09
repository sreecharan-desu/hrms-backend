# HRMF — Human Resource Management Framework (Backend)

A production-grade HR management API built with **FastAPI**, **SQLAlchemy 2 (async)**, **Neon Postgres**, and a clean-architecture domain layer.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                       Presentation                         │
│  FastAPI routers · Pydantic schemas · Middleware           │
│  /api/v1/*  (versioned)   /internal/*  (health, cron)     │
├────────────────────────────────────────────────────────────┤
│                       Application                          │
│  Use-cases · Policies · Audit logging                      │
├────────────────────────────────────────────────────────────┤
│                         Domain                             │
│  Entities · Enums · Repository interfaces                  │
├────────────────────────────────────────────────────────────┤
│                      Infrastructure                        │
│  SQLAlchemy repos · Redis cache · S3 storage · ARQ worker  │
│  SMTP email · Database session/UoW                         │
└────────────────────────────────────────────────────────────┘
        │               │              │
   Neon Postgres      Redis         MinIO / S3
```

### Modules

| Module | Description |
|---|---|
| **Auth** | Login, refresh (cookie), logout, forgot/reset password, OTP |
| **Employees** | CRUD, compensation, nested attendance/leave/docs/perf |
| **Departments** | CRUD with parent hierarchy |
| **Attendance** | Check-in/out, manual entry, date-range queries |
| **Leave** | Apply, approve/reject/cancel, balances, leave types |
| **Documents** | Presigned S3 upload flow (initiate → PUT → confirm) |
| **Recruitment** | Jobs, applications, stage pipeline, interviews, feedback |
| **Performance** | Cycles, reviews, submit/approve workflow |
| **Notifications** | List, mark read, mark all read |
| **Audit** | Immutable audit log with actor/entity/diff tracking |
| **Users** | Admin user management, role assignment |
| **Reports** | Headcount, attendance summary, leave usage |

## Requirements

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Neon Postgres (or any PostgreSQL 15+)
- Redis 7+
- MinIO or S3-compatible storage (for documents)

## Environment Setup

```bash
cp .env.example .env
# Edit .env with your Neon connection strings, JWT secret, etc.
```

### Neon Database Notes

- **`DATABASE_URL`** — Use the **pooled** connection string from Neon (`-pooler` host). Used by the app at runtime.
- **`DATABASE_URL_UNPOOLED`** — Use the **direct** (unpooled) connection string. Used by Alembic migrations (pgbouncer doesn't support DDL well).
- Both URLs should include `?sslmode=require`. The app auto-configures SSL for Neon hosts.
- The async driver `postgresql+asyncpg://` prefix is added automatically if you provide `postgresql://` or `postgres://`.

## Installation

```bash
# Create virtual environment and install
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Docker

```bash
# Start API + worker + Redis + MinIO
docker compose up -d

# Start with local Postgres for testing
docker compose --profile test up -d
```

Services exposed:
| Service | Port |
|---|---|
| API | 8000 |
| Redis | 6379 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| Postgres (test profile) | 5433 |

## Database Migrations

Migrations use Alembic against the **unpooled** connection:

```bash
# Apply all migrations
DATABASE_URL_UNPOOLED=<your-direct-neon-url> alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

## Seed Data

Seeds permissions, roles, a dev admin user, and default leave types:

```bash
uv run python scripts/seed.py
```

> Refuses to run when `APP_ENV=production`.

## Run Locally

```bash
uv run uvicorn app.main:app --reload
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs (development only)
```

## Testing

```bash
# All tests
uv run pytest -q

# Unit tests only
uv run pytest tests/unit -q

# API tests only
uv run pytest tests/api -q
```

Tests use SQLite (in-memory via aiosqlite) so no external database is needed for unit/API tests.

## Linting & Type Checking

```bash
# Lint
uv run ruff check app tests

# Auto-fix
uv run ruff check app tests --fix

# Format
uv run ruff format app tests

# Type check
uv run mypy app
```

Mypy is configured with `strict = true` and the `pydantic.mypy` plugin. SQLAlchemy and third-party stubs that are missing are ignored via `[[tool.mypy.overrides]]` in `pyproject.toml`.

## Vercel Deployment

The app deploys to Vercel as a serverless Python function:

```bash
vercel --prod
```

- Entry point: `app/main.py` → `app` (ASGI)
- Cron job drains background tasks every 5 minutes via `/internal/jobs/drain`
- Configuration in `vercel.json`

Set all `.env` variables in the Vercel dashboard under **Settings → Environment Variables**.

## API Versioning

All public endpoints are prefixed with `/api/v1/`. Internal endpoints (`/internal/*`) are excluded from the OpenAPI schema.

## Authentication & Cookie Model

- **Login** (`POST /api/v1/auth/login`): Returns `access_token` in the response body and sets `hrmf_refresh` as an HttpOnly cookie.
- **Access token**: Short-lived JWT (15 min default), sent as `Authorization: Bearer <token>`.
- **Refresh token**: Opaque token stored as SHA-256 hash in the DB. Rotated on each `/auth/refresh` call.
- **Cookie**: `hrmf_refresh`, HttpOnly, SameSite=None, Secure in production, path `/api/v1/auth`.

## RBAC (Role-Based Access Control)

Roles: `SUPER_ADMIN`, `HR_ADMIN`, `HR_MANAGER`, `HR_EXECUTIVE`, `MANAGER`, `RECRUITER`, `INTERVIEWER`, `EMPLOYEE`

Each role maps to a set of fine-grained permissions (e.g. `employee.read`, `leave.approve`). Permissions are cached in Redis per user. See `app/core/permissions.py` for the full mapping.

## Production: Swagger Disabled

In production (`APP_ENV=production`), `/docs`, `/redoc`, and `/openapi.json` are all disabled. This is verified by tests in `tests/api/test_internal_docs_hidden.py`.

## For frontend developers (web + Expo)

This backend is shared by:

1. **HR web portal** (recommended: Next.js App Router)
2. **Staff mobile app** (recommended: Expo Router + SecureStore)

### Must-read docs

| Doc | Audience |
|---|---|
| **[docs/FRONTEND.md](docs/FRONTEND.md)** | Full API contract: envelopes, auth, pagination (`offset`/`limit`), endpoints, permissions, uploads |
| **[docs/FRONTEND_AGENT.md](docs/FRONTEND_AGENT.md)** | Copy-paste brief for coding agents to build a sleek web + Expo UI against this API |
| **[AGENTS.md](AGENTS.md)** | Short rules for any agent opened on this repo |

### Client env

```bash
# Web
NEXT_PUBLIC_API_URL=http://localhost:8000

# Expo
EXPO_PUBLIC_API_URL=http://localhost:8000
```

After production deploy, point both at the live Vercel URL (see **Deployed URLs** below).

### Auth differences

- **Web:** access token in memory; refresh via HttpOnly `hrmf_refresh` cookie; always `credentials: "include"`. Ask backend owners to add your origin to `CORS_ORIGINS`.
- **Expo:** cookies are unreliable; use `refresh_token` from the login/refresh **JSON body** and store both tokens in **Expo SecureStore**.

Login/refresh responses include `refresh_token` in `data` for mobile. Web can ignore the body field and rely on the cookie.

### Local API docs

```text
http://localhost:8000/docs
```

Production disables `/docs`, `/redoc`, and `/openapi.json`. Generate TypeScript types from local OpenAPI, not from production.

### Do not

- Call `/internal/*` from any client
- Invent endpoints not listed in OpenAPI / `docs/FRONTEND.md`
- Store refresh tokens in `localStorage` (web) or AsyncStorage (mobile)

## Deployed URLs

| Resource | URL |
|---|---|
| GitHub | https://github.com/sreecharan-desu/hrms-backend |
| Production API | https://hrms-backend-silk.vercel.app |
| Neon project | `still-block-57656607` (branch `production`) |

Frontend clients should set:

```bash
NEXT_PUBLIC_API_URL=https://hrms-backend-silk.vercel.app
EXPO_PUBLIC_API_URL=https://hrms-backend-silk.vercel.app
```

Then ask a backend owner to add the web origin to Vercel env `CORS_ORIGINS`.
