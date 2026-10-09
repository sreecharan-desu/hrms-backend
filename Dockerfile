# ── Build stage ───────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
RUN uv pip install --system --no-cache .

# ── Runtime stage ─────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="HRMF Team"

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY app ./app

RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
