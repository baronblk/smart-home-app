"""
Authentication endpoints.

POST /api/v1/auth/login   — issue access + refresh tokens
POST /api/v1/auth/refresh — issue new access token via refresh cookie
POST /api/v1/auth/logout  — clear refresh token cookie
"""

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.auth.schemas import LoginRequest, RefreshResponse, TokenResponse
from app.config import settings
from app.dependencies import get_db
from app.exceptions import UnauthorizedError
from app.users.service import UserService

router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email/password and receive JWT tokens."""
    service = UserService(session)
    user = await service.authenticate(data.email, data.password)

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    # Store refresh token in httponly cookie
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth/refresh",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_db),
    # The refresh token is stored as an httponly cookie; FastAPI's Cookie()
    # dependency reads it from the Cookie header automatically.
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> RefreshResponse:
    """Issue a new access token using the refresh token cookie."""

    if refresh_token is None:
        raise UnauthorizedError("Refresh token missing.")

    payload = decode_refresh_token(refresh_token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired refresh token.")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token missing subject.")
    service = UserService(session)
    user = await service.get_by_id(user_id)

    access_token = create_access_token(str(user.id), user.role)
    return RefreshResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth/refresh",
    )
