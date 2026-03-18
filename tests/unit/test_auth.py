"""
Unit tests for authentication logic.

Tests JWT creation/decoding and password hashing in isolation.
No database access required.
"""

from app.auth.jwt import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.auth.password import hash_password, verify_password
from app.auth.rbac import Role, has_role

# ------------------------------------------------------------------
# Password tests
# ------------------------------------------------------------------


def test_hash_and_verify_password() -> None:
    plain = "securepassword123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_fails_verification() -> None:
    hashed = hash_password("correct_password")
    assert not verify_password("wrong_password", hashed)


# ------------------------------------------------------------------
# JWT tests
# ------------------------------------------------------------------


def test_access_token_round_trip() -> None:
    token = create_access_token("user-123", Role.ADMIN)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == Role.ADMIN
    assert payload["type"] == TOKEN_TYPE_ACCESS


def test_refresh_token_round_trip() -> None:
    token = create_refresh_token("user-456")
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == "user-456"
    assert payload["type"] == TOKEN_TYPE_REFRESH


def test_access_token_rejected_as_refresh() -> None:
    token = create_access_token("user-123", Role.USER)
    assert decode_refresh_token(token) is None


def test_refresh_token_rejected_as_access() -> None:
    token = create_refresh_token("user-123")
    assert decode_access_token(token) is None


def test_invalid_token_returns_none() -> None:
    assert decode_access_token("not.a.valid.token") is None
    assert decode_refresh_token("garbage") is None


# ------------------------------------------------------------------
# RBAC role hierarchy tests
# ------------------------------------------------------------------


def test_admin_satisfies_all_roles() -> None:
    assert has_role(Role.ADMIN, Role.ADMIN)
    assert has_role(Role.ADMIN, Role.USER)
    assert has_role(Role.ADMIN, Role.VIEWER)


def test_user_satisfies_user_and_viewer() -> None:
    assert not has_role(Role.USER, Role.ADMIN)
    assert has_role(Role.USER, Role.USER)
    assert has_role(Role.USER, Role.VIEWER)


def test_viewer_satisfies_only_viewer() -> None:
    assert not has_role(Role.VIEWER, Role.ADMIN)
    assert not has_role(Role.VIEWER, Role.USER)
    assert has_role(Role.VIEWER, Role.VIEWER)
