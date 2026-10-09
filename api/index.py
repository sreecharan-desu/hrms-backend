"""Vercel Python entrypoint re-exporting the FastAPI application."""

from app.main import app

__all__ = ["app"]
