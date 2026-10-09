"""Authentication endpoints – /api/v1/auth/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response

from app.core.config import get_settings
from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_current_user,
    get_request_context,
    get_uow,
)
from app.core.responses import success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    ResetPasswordRequest,
    VerifyOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_COOKIE_NAME = "hrmf_refresh"
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="none",
        path=_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE_NAME,
        httponly=True,
        samesite="none",
        path=_COOKIE_PATH,
    )


@router.post("/login")
async def login_endpoint(
    body: LoginRequest,
    response: Response,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.auth.login import login

    result = await login(
        email=body.email,
        password=body.password,
        ip=ctx.ip,
        user_agent=ctx.user_agent,
        uow=uow,
    )
    _set_refresh_cookie(response, result.refresh_token)
    return success_response(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "user_id": result.user_id,
            "email": result.email,
            "roles": result.roles,
        },
        message="Login successful.",
    )


@router.post("/refresh")
async def refresh_endpoint(
    response: Response,
    body: LogoutRequest | None = None,
    hrmf_refresh: Annotated[str | None, Cookie()] = None,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)] = None,  # type: ignore[assignment]
):
    from app.application.auth.refresh import rotate_refresh_token
    from app.core.exceptions import AuthError

    raw_token = (body.refresh_token if body and body.refresh_token else None) or hrmf_refresh
    if not raw_token:
        raise AuthError("No refresh token provided.")

    result = await rotate_refresh_token(raw_token, uow)
    _set_refresh_cookie(response, result.refresh_token)
    return success_response(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
        },
        message="Token refreshed.",
    )


@router.post("/logout")
async def logout_endpoint(
    response: Response,
    body: LogoutRequest | None = None,
    hrmf_refresh: Annotated[str | None, Cookie()] = None,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)] = None,  # type: ignore[assignment]
):
    from app.application.auth.logout import logout
    from app.core.exceptions import AuthError

    raw_token = (body.refresh_token if body and body.refresh_token else None) or hrmf_refresh
    if not raw_token:
        raise AuthError("No refresh token provided.")

    await logout(raw_token, uow)
    _delete_refresh_cookie(response)
    return success_response(message="Logged out successfully.")


@router.post("/forgot-password")
async def forgot_password_endpoint(
    body: ForgotPasswordRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.auth.forgot_password import forgot_password

    await forgot_password(email=body.email, uow=uow)
    return success_response(
        message="If the email is registered, a password reset OTP has been sent."
    )


@router.post("/verify-otp")
async def verify_otp_endpoint(
    body: VerifyOTPRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.auth.verify_otp import verify_otp

    result = await verify_otp(email=body.email, otp=body.otp, uow=uow)
    return success_response(
        data={"reset_token": result.reset_token},
        message=result.message,
    )


@router.post("/reset-password")
async def reset_password_endpoint(
    body: ResetPasswordRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.auth.reset_password import reset_password

    await reset_password(
        email=body.email,
        new_password=body.new_password,
        uow=uow,
    )
    return success_response(message="Password has been reset. Please log in again.")


@router.get("/me")
async def me_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.auth.me import get_me

    result = await get_me(user_id=user.id, uow=uow)
    return success_response(
        data={
            "id": result.id,
            "email": result.email,
            "status": result.status,
            "roles": result.roles,
            "permissions": result.permissions,
        }
    )
