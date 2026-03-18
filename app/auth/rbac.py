"""
Role-Based Access Control.

Three roles are defined as a string enum so they are stored
as readable strings in the database.

Enforcement: FastAPI route handlers declare:
    current_user: User = Depends(require_role(Role.ADMIN))
"""

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.exceptions import ForbiddenError, UnauthorizedError

if TYPE_CHECKING:
    from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# Role hierarchy: admins can do everything users can, users everything viewers can.
_ROLE_HIERARCHY: dict[str, int] = {
    Role.VIEWER: 0,
    Role.USER: 1,
    Role.ADMIN: 2,
}


def has_role(user_role: str, required_role: str) -> bool:
    """Return True if user_role satisfies the required_role level."""
    return _ROLE_HIERARCHY.get(user_role, -1) >= _ROLE_HIERARCHY.get(required_role, 999)


def require_role(minimum_role: Role) -> Any:
    """
    FastAPI dependency factory.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(Role.ADMIN))):
            ...
    """

    async def dependency(
        token: str = Depends(oauth2_scheme),
    ) -> "User":
        # Import here to avoid circular imports
        from app.auth.jwt import decode_access_token
        from app.db.session import async_session_factory
        from app.users.repository import UserRepository

        payload = decode_access_token(token)
        if payload is None:
            raise UnauthorizedError("Invalid or expired token.")

        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Token missing subject.")

        async with async_session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(user_id)

        if user is None:
            raise UnauthorizedError("User not found.")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated.")
        if not has_role(user.role, minimum_role):
            raise ForbiddenError(f"Role '{minimum_role}' or higher required, got '{user.role}'.")
        return user

    return dependency
