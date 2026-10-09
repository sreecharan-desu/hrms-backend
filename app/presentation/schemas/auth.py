"""Auth request/response Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

# ── Requests ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    """Body is optional; token may come from cookie."""
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Responses ────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    roles: list[str]


class MeResponse(BaseModel):
    id: str
    email: str
    status: str
    roles: list[str]
    permissions: list[str]
