# HRMF — Frontend Developer Contract

This document is the **API contract** for the HR web portal and the Expo React Native staff app.

Also read: [`FRONTEND_AGENT.md`](./FRONTEND_AGENT.md) (agent build brief) and root [`AGENTS.md`](../AGENTS.md).

---

## Architecture (what you are talking to)

```
Web / Expo
    → HTTPS JSON
    → FastAPI Presentation (/api/v1/*)
    → Application use cases + RBAC policies
    → Domain rules
    → Infrastructure (SQLAlchemy → Neon Postgres, Redis cache, S3-compatible storage, job outbox)
```

| Concern | Where it lives |
|---|---|
| Public business API | `/api/v1/*` |
| Health / cron / admin ops | `/internal/*` — **never call from clients** |
| Database (source of truth) | Neon Lakebase Postgres |
| Cache / lockout / OTP temp | Redis |
| Files | S3 / R2 / MinIO via **presigned URLs** (not through the API body) |
| Background email/SMS | Postgres outbox drained by Vercel Cron |

Runtime: one Vercel Fluid Python function (FastAPI ASGI). Local: `uvicorn` + Docker Redis/MinIO.

---

## Base URL

| Environment | Base URL |
|---|---|
| Local development | `http://localhost:8000` |
| Production | `PRODUCTION_API_URL` (set after deploy; also in README) |

Client env vars:

- Web: `NEXT_PUBLIC_API_URL`
- Expo: `EXPO_PUBLIC_API_URL`

All business paths are under `/api/v1/`.

OpenAPI / Swagger:

- Development: `/docs`, `/redoc`, `/openapi.json` enabled
- Production: all disabled (404). Use this document + local OpenAPI for types.

---

## Response envelopes

### Success

```json
{
  "success": true,
  "data": {},
  "message": "Employee created successfully"
}
```

### Error

```json
{
  "success": false,
  "error": {
    "code": "LEAVE_INSUFFICIENT_BALANCE",
    "message": "Insufficient leave balance."
  }
}
```

HTTP status codes are real (`401`, `403`, `404`, `409`, `422`, `429`, `500`). Never treat HTTP 200 as the only success signal.

### Validation (422)

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      { "field": "email", "message": "value is not a valid email address" }
    ]
  }
}
```

`details` may be omitted in production.

---

## Pagination, filtering, sorting

Collections use **`offset` + `limit`** (not `page` / `page_size`):

```
GET /api/v1/employees?offset=0&limit=20&search=charan&department_id=<uuid>&status=ACTIVE
```

Typical response `data`:

```json
{
  "items": [],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

Defaults are usually `offset=0`, `limit=50`. Max is typically `100` or `200` depending on the endpoint. Never request unbounded lists.

IDs are UUID strings. Timestamps are ISO-8601 UTC. Attendance work dates use `APP_TIMEZONE` (default `Asia/Kolkata`).

---

## Authentication

### Login

```
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "admin@example.com", "password": "..." }
```

Success `data` includes:

- `access_token` (JWT, ~15 minutes)
- `refresh_token` (opaque; also set as cookie for web)
- `token_type` (`bearer`)
- `expires_in`
- `user_id`, `email`, `roles`

The server also sets cookie:

- Name: `hrmf_refresh`
- HttpOnly, `SameSite=None`, `Secure` in production
- Path: `/api/v1/auth`

### Web portal

1. Keep `access_token` **in memory** only.
2. Call APIs with `Authorization: Bearer <access_token>` and `credentials: "include"`.
3. Refresh: `POST /api/v1/auth/refresh` with credentials (cookie). Response also returns new `refresh_token` / rotates cookie.
4. Logout: `POST /api/v1/auth/logout` with credentials.
5. CORS: backend allowlist (`CORS_ORIGINS`). Ask backend to add your web origin. No `*` with credentials.

### Expo / React Native

Cookies are unreliable on native:

1. Persist `access_token` + `refresh_token` in **Expo SecureStore** (never AsyncStorage).
2. Refresh / logout with JSON body: `{ "refresh_token": "<stored>" }`.
3. After every refresh, replace the stored refresh token (rotation).
4. Still send `Authorization: Bearer <access_token>` on protected calls.

### Current user + UI gating

```
GET /api/v1/auth/me
Authorization: Bearer <access>
```

Use returned `roles` and `permissions` to show/hide nav. Always handle `403` even if the UI is gated.

### Recommended interceptor

1. On `401`, try refresh once.
2. Retry the original request with the new access token.
3. If refresh fails, clear session and route to login.

### Password reset

```
POST /api/v1/auth/forgot-password   { "email" }
POST /api/v1/auth/verify-otp        { "email", "otp" }
POST /api/v1/auth/reset-password    { "email", "new_password" }
```

Reset revokes all refresh sessions for that user.

---

## Permissions (for UI gating)

| Permission | Typical UI |
|---|---|
| `employee.read` / `create` / `update` / `delete` | Employee directory CRUD |
| `employee.compensation.read` / `update` | Salary fields |
| `department.*` | Org structure |
| `attendance.read` / `create` / `update` | Attendance admin / manual |
| `leave.read` / `create` / `approve` / `reject` / `cancel` | Leave workflows |
| `recruitment.read` / `create` / `update` / `manage` | Jobs & pipeline |
| `performance.read` / `create` / `evaluate` | Reviews |
| `document.read` / `upload` / `delete` | Documents |
| `audit.read` | Audit log |
| `admin.manage` | Users & roles |

Roles: `SUPER_ADMIN`, `HR_ADMIN`, `HR_MANAGER`, `HR_EXECUTIVE`, `MANAGER`, `RECRUITER`, `INTERVIEWER`, `EMPLOYEE`.

Resource rules still apply (e.g. employees see self; managers see direct reports).

---

## Module endpoints

All paths below are relative to `/api/v1`.

### Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login` | access + refresh in body; cookie set |
| POST | `/auth/refresh` | cookie and/or body `refresh_token` |
| POST | `/auth/logout` | cookie and/or body |
| POST | `/auth/forgot-password` | |
| POST | `/auth/verify-otp` | |
| POST | `/auth/reset-password` | |
| GET | `/auth/me` | roles + permissions |

### Users (admin)

| Method | Path | Permission |
|---|---|---|
| GET | `/users` | `admin.manage` |
| GET | `/users/{id}` | `admin.manage` |
| POST | `/users/{id}/roles` | `admin.manage` |

### Employees

| Method | Path | Permission |
|---|---|---|
| POST | `/employees` | `employee.create` |
| GET | `/employees` | `employee.read` (+ resource filter) |
| GET | `/employees/{id}` | resource-level |
| PATCH | `/employees/{id}` | `employee.update` |
| DELETE | `/employees/{id}` | `employee.delete` (soft) |
| PATCH | `/employees/{id}/compensation` | `employee.compensation.update` |
| GET | `/employees/{id}/attendance` | authenticated + resource |
| GET | `/employees/{id}/leave` | authenticated + resource |
| GET | `/employees/{id}/documents` | authenticated + resource |
| GET | `/employees/{id}/performance` | authenticated + resource |

List query: `offset`, `limit`, `search`, `department_id`, `status`.

### Departments

| Method | Path | Permission |
|---|---|---|
| POST | `/departments` | `department.create` |
| GET | `/departments` | `department.read` |
| GET | `/departments/{id}` | `department.read` |
| PATCH | `/departments/{id}` | `department.update` |
| DELETE | `/departments/{id}` | `department.delete` (blocked if active employees) |
| GET | `/departments/{id}/children` | `department.read` |

### Attendance

| Method | Path | Permission |
|---|---|---|
| POST | `/attendance/check-in` | authenticated (self) |
| POST | `/attendance/check-out` | authenticated (self) |
| GET | `/attendance` | `attendance.read` |
| GET | `/attendance/{employee_id}` | self or `attendance.read` |
| POST | `/attendance/manual` | `attendance.update` |
| PATCH | `/attendance/{id}` | `attendance.update` |

Duplicate check-in → `409`.

### Leave

| Method | Path | Permission |
|---|---|---|
| POST | `/leaves` | authenticated |
| GET | `/leaves` | self or `leave.read` |
| GET | `/leaves/balances/me` | authenticated |
| GET | `/leaves/{id}` | self or `leave.read` |
| POST | `/leaves/{id}/approve` | `leave.approve` |
| POST | `/leaves/{id}/reject` | `leave.reject` |
| POST | `/leaves/{id}/cancel` | own / authorized |
| GET | `/leave-types` | authenticated |

Statuses are a state machine (`PENDING` → `APPROVED` → `COMPLETED`, plus reject/cancel paths). Do not invent status writes.

### Documents (presigned)

| Method | Path | Permission |
|---|---|---|
| POST | `/documents/upload` | `document.upload` |
| POST | `/documents/{id}/confirm` | `document.upload` |
| GET | `/documents` | `document.read` |
| GET | `/documents/{id}` | `document.read` (+ signed GET URL) |
| DELETE | `/documents/{id}` | `document.delete` |

Flow:

1. `POST /documents/upload` with `{ filename, size_bytes, content_type, employee_id }`
2. Receive `upload_url` + headers
3. `PUT` file bytes directly to storage
4. `POST /documents/{id}/confirm`

Allowed extensions: `pdf`, `png`, `jpg`, `jpeg`, `docx`. Max size ~10MB. Do not trust client MIME alone.

### Recruitment

Jobs: `POST/GET/PATCH/DELETE /jobs`, `POST /jobs/{id}/publish`, `POST /jobs/{id}/close`  
Applications: `POST/GET/PATCH /applications`, `POST /applications/{id}/move-stage`  
Interviews: `POST/GET /applications/{id}/interviews`, `POST /interviews/{id}/feedback`, `PATCH /interviews/{id}`

Stages: `APPLIED → SCREENING → INTERVIEW → TECHNICAL → HR → OFFER → HIRED` (+ `REJECTED`). Invalid moves return `APPLICATION_INVALID_STAGE_TRANSITION`.

### Performance

`POST/GET /performance/cycles`  
`POST/GET /performance/reviews`, `GET /performance/reviews/{id}`  
`POST /performance/reviews/{id}/submit`, `POST /performance/reviews/{id}/approve`  

Approved reviews are immutable.

### Notifications

| Method | Path |
|---|---|
| GET | `/notifications` |
| POST | `/notifications/{id}/read` |
| POST | `/notifications/read-all` |

Scoped to the current user.

### Audit & reports

| Method | Path | Permission |
|---|---|---|
| GET | `/audit-logs` | `audit.read` |
| GET | `/reports/headcount` | `employee.read` |
| GET | `/reports/attendance-summary` | `attendance.read` |
| GET | `/reports/leave-usage` | `leave.read` |

---

## Common error codes

| Code | Meaning |
|---|---|
| `AUTH_INVALID_CREDENTIALS` / auth errors | Bad login / token |
| `AUTH_TOKEN_EXPIRED` | Refresh or re-login |
| `AUTH_FORBIDDEN` | Authenticated but not allowed |
| `EMPLOYEE_NOT_FOUND` | Missing employee |
| `EMPLOYEE_ALREADY_EXISTS` | Unique email/code conflict |
| `LEAVE_INSUFFICIENT_BALANCE` | Cannot approve/apply |
| `LEAVE_INVALID_STATUS` | Illegal leave transition |
| `APPLICATION_INVALID_STAGE_TRANSITION` | Illegal pipeline move |
| `VALIDATION_ERROR` | 422 body/query |
| `RESOURCE_NOT_FOUND` | Generic 404 |
| `INTERNAL_SERVER_ERROR` | 500 |

---

## Type generation

In development:

```bash
# example
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts
```

Do not scrape production `/openapi.json` — it is disabled.
