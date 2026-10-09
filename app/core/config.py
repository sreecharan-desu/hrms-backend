"""Application settings loaded from environment variables via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "HRMF"
    APP_VERSION: str = "0.1.0"
    APP_TIMEZONE: str = "Asia/Kolkata"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_UNPOOLED: str | None = None

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            import json

            return json.loads(v) if v.startswith("[") else [s.strip() for s in v.split(",")]
        return v

    # ── Object Storage (S3-compatible) ───────────────────────────────
    STORAGE_BUCKET: str = ""
    STORAGE_REGION: str = "us-east-1"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_ENDPOINT: str | None = None

    # ── SMTP / Email ─────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "HRMF"

    # ── Internal / Cron ──────────────────────────────────────────────
    INTERNAL_API_TOKEN: str = ""
    CRON_SECRET: str = ""

    # ── Dev Seed Admin ───────────────────────────────────────────────
    DEV_ADMIN_EMAIL: str = "admin@example.com"
    DEV_ADMIN_PASSWORD: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton – import this wherever settings are needed."""
    return Settings()  # type: ignore[call-arg]
