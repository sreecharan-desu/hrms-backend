# Frontend Agent Brief — Build the HRMF Clients

Copy this file into a frontend repo or paste it at the start of an agent session.

## Product

Build **two** clients against this backend only (no second BFF):

1. **HR Web Portal** — desktop-first admin/HR/manager experience.
2. **Staff Mobile App** — Expo React Native for employees (attendance, leave, notifications, profile).

Backend repo (source of truth): this HRMF backend. Read [`FRONTEND.md`](./FRONTEND.md) for every endpoint, envelope, and auth rule.

## Stack (do not invent alternatives unless the user overrides)

### Web

- Next.js (App Router)
- TypeScript strict
- TanStack Query
- Typed API client generated from `/openapi.json` (dev backend) or handwritten types matching `FRONTEND.md`
- Env: `NEXT_PUBLIC_API_URL`

### Mobile

- Expo + Expo Router
- TypeScript strict
- TanStack Query
- Expo SecureStore for tokens
- Env: `EXPO_PUBLIC_API_URL`

## Design direction

- One coherent visual system across web and mobile.
- Sleek, calm HR product — strong hierarchy, generous whitespace, readable tables/lists.
- Avoid generic “AI dashboard” looks (purple gradients, glow, pill spam, dense stat strips in the hero).
- Role-aware navigation: only show modules the user’s permissions allow.
- Empty states and error states must be intentional, not blank screens.

## Auth implementation (critical)

### Web

1. `POST /api/v1/auth/login` with `{ email, password }`, `credentials: "include"`.
2. Store `access_token` **in memory** (React state / module variable). Never `localStorage` for refresh.
3. Always send `Authorization: Bearer <access_token>` and `credentials: "include"`.
4. On 401: `POST /api/v1/auth/refresh` with credentials; update access token; retry original request once.
5. Logout: `POST /api/v1/auth/logout` with credentials.

### Expo / React Native

1. Cookies are unreliable — **do not depend on them**.
2. Login response includes `refresh_token` in JSON `data`. Store **access + refresh** in **Expo SecureStore**.
3. Refresh: `POST /api/v1/auth/refresh` with body `{ "refresh_token": "<stored>" }`.
4. Persist the rotated `refresh_token` from every refresh response.
5. Never use AsyncStorage for tokens.

After login (both clients), call `GET /api/v1/auth/me` and cache roles + permissions for nav gating.

## Screen map by role

| Role | Primary surfaces |
|---|---|
| `SUPER_ADMIN` / `HR_ADMIN` | Org setup, users/roles, employees, departments, audit, reports, all HR modules |
| `HR_MANAGER` / `HR_EXECUTIVE` | Employees, attendance, leave approvals, recruitment, documents, reports |
| `MANAGER` | Team roster, leave approve/reject for reports, performance reviews, team attendance |
| `RECRUITER` | Jobs, applications, stage moves, interviews |
| `INTERVIEWER` | Assigned interviews + feedback only |
| `EMPLOYEE` | Self profile, check-in/out, leave apply/cancel, own documents, own performance, notifications |

## Hard rules

1. Never call `/internal/*` from clients.
2. Never invent endpoints or query shapes — use `offset` + `limit` (not `page`/`page_size`).
3. Always unwrap `{ success, data, message }` / `{ success, error }`.
4. Gate UI by permissions from `/auth/me`, but still handle HTTP 403.
5. Document uploads: initiate → PUT to presigned URL → confirm. Do not POST file bytes to the API.
6. Compensation fields may be omitted unless `employee.compensation.read` — do not assume salary is present.
7. Attendance “work date” is timezone-aware (`APP_TIMEZONE`, default `Asia/Kolkata`); store/display ISO UTC timestamps correctly.
8. Production API has **no** `/docs` — rely on this contract + local OpenAPI.

## Suggested web information architecture

- `/login`
- `/dashboard` (role-aware)
- `/employees`, `/employees/[id]`
- `/departments`
- `/attendance`
- `/leaves`
- `/recruitment/jobs`, `/recruitment/applications/[id]`
- `/performance`
- `/documents`
- `/notifications`
- `/reports`
- `/admin/users` (admin.manage)
- `/audit` (audit.read)

## Suggested mobile information architecture

- Auth stack: login, forgot/reset password
- Tabs: Home, Attendance, Leave, Notifications, Profile
- Deep links for leave status / notifications when possible

## Acceptance checklist

- [ ] Login works on web with cookie refresh + credentials
- [ ] Login works on Expo with SecureStore refresh body
- [ ] 401 interceptor refreshes once then retries
- [ ] `/auth/me` drives nav visibility
- [ ] Employee list paginates with `offset`/`limit`
- [ ] Leave apply → manager approve path works end-to-end
- [ ] Attendance check-in rejects duplicate with clear error
- [ ] Document upload uses presigned flow
- [ ] Unauthorized compensation access does not crash UI
- [ ] Production base URL configured; no calls to `/docs` in prod

## API source of truth

[`FRONTEND.md`](./FRONTEND.md) and development `/openapi.json`.
