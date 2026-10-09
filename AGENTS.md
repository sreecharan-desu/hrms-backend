# Agent notes — HRMF Backend

This repository is the **HRMF backend only** (FastAPI + Neon Postgres).

## Before generating any frontend UI

1. Read [`docs/FRONTEND.md`](docs/FRONTEND.md) — API contract (envelopes, auth, endpoints, permissions).
2. Read [`docs/FRONTEND_AGENT.md`](docs/FRONTEND_AGENT.md) — build brief for the HR web portal and Expo staff app.
3. Prefer live OpenAPI at `http://localhost:8000/openapi.json` in **development** as the machine-readable source of truth.
4. **Do not invent endpoints.** If it is not in OpenAPI / `docs/FRONTEND.md`, it does not exist.
5. **Never call `/internal/*` from a client app.** Those routes are for health, cron, and ops only.

## Backend rules for agents working in this repo

- Clean Architecture: Presentation → Application → Domain ← Infrastructure.
- Domain must not import FastAPI, SQLAlchemy, Redis, or boto.
- Secrets live in env / Vercel — never commit `.env` or `.env.local`.
- Neon agent skills under `.agents/skills/` are for database/infra guidance only. This app keeps custom JWT auth and S3-compatible document storage (not Neon Auth / Neon Object Storage unless explicitly requested).

## Clients expected

| Client | Stack (recommended) | Auth storage |
|---|---|---|
| HR web portal | Next.js App Router + TanStack Query | Access token in memory; refresh via HttpOnly cookie |
| Staff mobile | Expo Router + TanStack Query | Access + refresh in Expo SecureStore (JSON body refresh) |
