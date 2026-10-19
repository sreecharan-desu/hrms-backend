# Benchmarks

Raw output from one run on 19 Oct 2026. Nothing here is extrapolated.

| File | What |
|---|---|
| `k6-api.js` | Load script: 3 scenarios run one after another (list employees, `/auth/me`, login) |
| `run.sh` | Reproduces the run: migrate, seed, start 4 uvicorn workers, k6, pytest + coverage |
| `results-2026-10-19/k6-output.txt` | Full k6 console output |
| `results-2026-10-19/k6-summary.json` | k6 `--summary-export` |
| `results-2026-10-19/pytest-coverage.txt` | `pytest -q --cov=app` output |
| `results-2026-10-19/environment.txt` | Hardware, versions, cold start, memory |

## Environment

```
date_ist: 2026-10-19 08:30 UTC
host: single shared VM (load generator and server on the SAME box)
cpu: Intel(R) Xeon(R) Processor x 8 vCPU
ram: 15 GiB
os: Debian GNU/Linux 13 (trixie), kernel 6.12.94+
k6: k6 v0.54.0 (commit/baba871c8a, go1.23.1, linux/amd64)
server: uvicorn app.main:app --workers 4 (APP_ENV=staging: SQL echo off; structlog request logging on, as shipped), Python 3.12.15
db: local PostgreSQL 17 + Redis 7 on the same box (not Neon; no network RTT)
data: seed.py + 200 employees created in k6 setup()
cold_start_ms: 957
idle_rss_total_mb: 444.8 (processes: 6)
under_load_rss_total_mb: 519.8 (processes: 6)
```

## Method

- Throughput = requests in a scenario / scenario duration (30 s for GET, 20 s for login). These are closed-loop VUs with no think time, so this is the saturation rate at that concurrency, not a user count.
- Cold start = wall time from launching `uvicorn --workers 4` to the first `200` from `/internal/health`.
- Memory = summed RSS of the uvicorn master + workers, idle and about 15 s into the list-employees scenario.
- Caveats: k6 and the server shared the same 8 vCPUs, and the DB was local. Production (Vercel serverless + Neon over the network) will behave differently, mostly with higher latency per request.

## Result

| Endpoint | Concurrency (VUs) | Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Error rate |
|---|---|---|---|---|---|---|---|---|
| `GET /employees` | 50 | 23,950 | 798 | 64.8 | 106.3 | 144.6 | 187.0 | 0.00% |
| `GET /auth/me` | 50 | 38,914 | 1,297 | 34.6 | 71.1 | 89.4 | 143.0 | 0.00% |
| `POST /auth/login` | 20 | 939 | 47 | 427.4 | 623.0 | 715.1 | 894.4 | 0.00% |
