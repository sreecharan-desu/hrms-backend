"""Shared pytest fixtures and environment defaults."""

from __future__ import annotations

import os

# Must be set before Settings() / app imports in test modules.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-bytes-long!!!")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
