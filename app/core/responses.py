"""Standardised API response helpers.

Success envelope:  {"success": true,  "data": ..., "message": "..."}
Error   envelope:  {"success": false, "error": {"code": "...", "message": "..."}}
"""

from __future__ import annotations

from typing import Any

import orjson
from starlette.responses import JSONResponse


class ORJSONResponse(JSONResponse):
    """Faster JSON response using orjson."""

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
) -> ORJSONResponse:
    return ORJSONResponse(
        content={"success": True, "data": data, "message": message},
        status_code=status_code,
    )


def created_response(data: Any = None, message: str = "Created") -> ORJSONResponse:
    return success_response(data=data, message=message, status_code=201)


def no_content_response() -> ORJSONResponse:
    return ORJSONResponse(content=None, status_code=204)


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
) -> ORJSONResponse:
    return ORJSONResponse(
        content={
            "success": False,
            "error": {"code": code, "message": message},
        },
        status_code=status_code,
    )
