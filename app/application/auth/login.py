"""Login use case – verify credentials, issue tokens."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.exceptions import AuthError, RateLimitError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.domain.users.enums import UserStatus
from app.infrastructure.cache.redis import (
    check_login_lockout,
    clear_login_lockout,
    record_failed_login,
)
from app.infrastructure.database.models.user import RefreshToken
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user_id: str = ""
    email: str = ""
    roles: list[str] | None = None


async def login(
    email: str,
    password: str,
    ip: str,
    user_agent: str,
    uow: SqlAlchemyUnitOfWork,
) -> LoginResult:
    """Authenticate user with email + password and return token pair."""
    if await check_login_lockout(email, ip):
        raise RateLimitError("Too many login attempts. Try again in 15 minutes.")

    user = await uow.users.get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        await record_failed_login(email, ip)
        raise AuthError("Invalid email or password.")

    if user.status == UserStatus.LOCKED:
        raise AuthError("Account is locked. Contact your administrator.")

    if user.status != UserStatus.ACTIVE:
        raise AuthError("Account is not active.")

    await clear_login_lockout(email, ip)

    settings = get_settings()
    role_names = [r.name for r in user.roles]

    access_token = create_access_token(
        subject=user.id,
        extra={"email": user.email, "roles": role_names},
    )

    raw_refresh = generate_refresh_token()
    family_id = str(uuid.uuid4())
    refresh_row = RefreshToken(
        token_hash=hash_refresh_token(raw_refresh),
        user_id=user.id,
        family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await uow.refresh_tokens.create(refresh_row)
    await uow.commit()

    return LoginResult(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        roles=role_names,
    )
