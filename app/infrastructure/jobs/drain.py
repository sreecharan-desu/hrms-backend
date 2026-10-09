"""Outbox drain – claim PENDING jobs, dispatch to handlers, mark DONE/FAILED."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update

from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.jobs.handlers import HANDLER_MAP

logger = structlog.stdlib.get_logger(__name__)

_MAX_ATTEMPTS = 3
_BATCH_SIZE = 20


async def drain_jobs(batch_size: int = _BATCH_SIZE) -> int:
    """Claim and process a batch of PENDING jobs. Returns count processed."""
    processed = 0
    async with async_session_factory() as session:
        stmt = (
            select(BackgroundJob)
            .where(
                BackgroundJob.status == "PENDING",
                BackgroundJob.available_at <= datetime.now(UTC),
                BackgroundJob.attempts < _MAX_ATTEMPTS,
            )
            .order_by(BackgroundJob.available_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        jobs = result.scalars().all()

        for job in jobs:
            handler = HANDLER_MAP.get(job.type)
            if handler is None:
                await logger.awarning("unknown_job_type", job_id=job.id, type=job.type)
                await session.execute(
                    update(BackgroundJob)
                    .where(BackgroundJob.id == job.id)
                    .values(
                        status="FAILED",
                        last_error=f"Unknown job type: {job.type}",
                        attempts=job.attempts + 1,
                    )
                )
                processed += 1
                continue

            try:
                await handler(job.payload or {})
                await session.execute(
                    update(BackgroundJob)
                    .where(BackgroundJob.id == job.id)
                    .values(status="DONE", attempts=job.attempts + 1)
                )
            except Exception as exc:
                await logger.aerror(
                    "job_failed",
                    job_id=job.id,
                    type=job.type,
                    attempt=job.attempts + 1,
                    exc_info=exc,
                )
                new_status = "FAILED" if job.attempts + 1 >= _MAX_ATTEMPTS else "PENDING"
                await session.execute(
                    update(BackgroundJob)
                    .where(BackgroundJob.id == job.id)
                    .values(
                        status=new_status,
                        attempts=job.attempts + 1,
                        last_error=str(exc)[:500],
                    )
                )
            processed += 1

        await session.commit()

    if processed:
        await logger.ainfo("drain_complete", processed=processed)
    return processed
