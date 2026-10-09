"""Application error hierarchy with structured codes for the API envelope."""

from __future__ import annotations


class AppError(Exception):
    """Base application error – all domain/app exceptions inherit from this."""

    code: str = "APP_ERROR"
    message: str = "An unexpected error occurred."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class AuthError(AppError):
    code = "AUTH_ERROR"
    message = "Authentication failed."
    status_code = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."
    status_code = 403


class NotFoundError(AppError):
    code = "NOT_FOUND"
    message = "The requested resource was not found."
    status_code = 404


class ConflictError(AppError):
    code = "CONFLICT"
    message = "The resource already exists or conflicts with current state."
    status_code = 409


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    message = "Validation failed."
    status_code = 422


class RateLimitError(AppError):
    code = "RATE_LIMIT"
    message = "Too many requests. Please try again later."
    status_code = 429
