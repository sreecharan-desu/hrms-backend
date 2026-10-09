"""ARQ worker settings – reuses the same drain logic for local Docker."""

from __future__ import annotations

import structlog
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.infrastructure.jobs.drain import drain_jobs

logger = structlog.stdlib.get_logger(__name__)


async def run_drain(ctx: dict) -> int:
    """ARQ task entry-point – delegates to the shared drain function."""
    return await drain_jobs()


async def startup(ctx: dict) -> None:
    await logger.ainfo("arq_worker_started")


async def shutdown(ctx: dict) -> None:
    await logger.ainfo("arq_worker_stopped")


class WorkerSettings:
    functions = [run_drain]
    on_startup = startup
    on_shutdown = shutdown
    cron_jobs = [
        {"coroutine": run_drain, "minute": {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}},
    ]

    @staticmethod
    def redis_settings() -> RedisSettings:
        settings = get_settings()
        return RedisSettings.from_dsn(settings.REDIS_URL)
