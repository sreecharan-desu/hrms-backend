"""Verify internal endpoints are hidden from OpenAPI in production mode."""

from __future__ import annotations

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-long!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database as _db_mod

_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)
_db_mod.engine = _test_engine
_db_mod.async_session_factory = _TestSession


from app.core.config import get_settings


def _make_app(app_env: str):
    os.environ["APP_ENV"] = app_env
    get_settings.cache_clear()
    from app.main import create_app

    return create_app()


def _collect_all_paths(application) -> list[str]:
    """Recursively collect all route paths from the app."""
    paths: list[str] = []

    def _walk(routes, prefix: str = "") -> None:
        for route in routes:
            # Standard Route objects
            path = getattr(route, "path", None)
            if path is not None:
                paths.append(prefix + path)
            # FastAPI _IncludedRouter – access via original_router
            orig = getattr(route, "original_router", None)
            if orig is not None and hasattr(orig, "routes"):
                _walk(orig.routes, prefix)
            # Starlette Mount
            elif hasattr(route, "routes"):
                _walk(route.routes, prefix + (path or ""))

    _walk(application.routes)
    return paths


class TestProductionDocsHidden:
    def test_production_docs_url_is_none(self):
        application = _make_app("production")
        assert application.docs_url is None
        assert application.redoc_url is None
        assert application.openapi_url is None

    def test_production_openapi_excludes_internal(self):
        """Internal routes have include_in_schema=False so they won't appear."""
        application = _make_app("development")
        schema = application.openapi()
        paths = list(schema.get("paths", {}).keys())

        internal_paths = [p for p in paths if p.startswith("/internal/")]
        assert internal_paths == [], f"Internal paths leaked into schema: {internal_paths}"

    def test_development_docs_url_present(self):
        application = _make_app("development")
        assert application.docs_url == "/docs"
        assert application.openapi_url == "/openapi.json"


class TestInternalRoutesRegistered:
    """Confirm the internal routes exist on the app even though they
    are excluded from the schema."""

    def _route_paths(self):
        application = _make_app("development")
        return _collect_all_paths(application)

    def test_health_route_exists(self):
        assert "/internal/health" in self._route_paths()

    def test_jobs_drain_route_exists(self):
        assert "/internal/jobs/drain" in self._route_paths()

    def test_ready_route_exists(self):
        assert "/internal/ready" in self._route_paths()

    def test_admin_cache_clear_route_exists(self):
        assert "/internal/admin/cache/clear" in self._route_paths()
