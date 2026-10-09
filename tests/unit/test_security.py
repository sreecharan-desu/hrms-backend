"""Unit tests for password hashing and JWT round-trip."""

import os

# Ensure a JWT secret is available during tests
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-bytes-long!!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///")

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_and_verify():
    plain = "MySecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(
        subject="user-123",
        extra={"email": "a@b.com", "roles": ["EMPLOYEE"]},
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.com"
    assert payload["roles"] == ["EMPLOYEE"]
    assert payload["type"] == "access"


def test_refresh_token_generation():
    t1 = generate_refresh_token()
    t2 = generate_refresh_token()
    assert t1 != t2
    assert len(t1) > 32


def test_refresh_token_hash_deterministic():
    token = "abc123"
    h1 = hash_refresh_token(token)
    h2 = hash_refresh_token(token)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest
