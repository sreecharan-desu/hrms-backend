#!/usr/bin/env bash
# Reproduce the numbers in README "Performance (measured)".
# Needs: local PostgreSQL + Redis, k6 (https://k6.io), the venv from README "Setup".
set -euo pipefail
export APP_ENV=staging   # staging = SQL echo off, docs on; seed.py refuses production
: "${DATABASE_URL:?set DATABASE_URL to a LOCAL postgres, e.g. postgresql+asyncpg://bench:bench@127.0.0.1:5432/hrms}"
: "${DEV_ADMIN_EMAIL:?}"; : "${DEV_ADMIN_PASSWORD:?}"
alembic upgrade head && APP_ENV=development python scripts/seed.py
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 & SP=$!
trap 'kill $SP' EXIT
until curl -sf http://127.0.0.1:8000/internal/health >/dev/null; do sleep 0.1; done
OUT=benchmarks/results-$(date +%F); mkdir -p "$OUT"
k6 run -e BASE=http://127.0.0.1:8000 -e EMAIL="$DEV_ADMIN_EMAIL" -e PASSWORD="$DEV_ADMIN_PASSWORD" \
  --summary-export "$OUT/k6-summary.json" benchmarks/k6-api.js | tee "$OUT/k6-output.txt"
pytest -q --cov=app --cov-report=term | tee "$OUT/pytest-coverage.txt"
