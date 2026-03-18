"""
User service — business logic for the User domain.
"""
import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.auth.rbac import Role
from app.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import PasswordChange, UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def create_user(self, data: UserCreate) -> User:
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError(f"Email '{data.email}' is already registered.")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        return await self._repo.create(user)

    async def get_by_id(self, user_id: str | uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found.")
        return user

    async def get_by_email(self, email: str) -> User:
        user = await self._repo.get_by_email(email)
        if user is None:
            raise NotFoundError(f"User '{email}' not found.")
        return user

    async def list_users(self, limit: int = 100, offset: int = 0) -> Sequence[User]:
        return await self._repo.get_all(limit=limit, offset=offset)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        if data.email is not None and data.email != user.email:
            existing = await self._repo.get_by_email(data.email)
            if existing is not None:
                raise ConflictError(f"Email '{data.email}' is already taken.")
            user.email = data.email
        if data.full_name is not None:
            user.full_name = data.full_name
        return await self._repo.update(user)

    async def change_password(self, user: User, data: PasswordChange) -> User:
        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect.")
        user.hashed_password = hash_password(data.new_password)
        return await self._repo.update(user)

    async def set_role(self, user: User, role: Role, requesting_user: User) -> User:
        if requesting_user.role != Role.ADMIN:
            raise ForbiddenError("Only admins can change roles.")
        user.role = role
        return await self._repo.update(user)

    async def deactivate(self, user: User) -> User:
        user.is_active = False
        return await self._repo.update(user)

    async def delete(self, user_id: str | uuid.UUID) -> None:
        user = await self.get_by_id(user_id)
        await self._repo.delete(user)

    async def authenticate(self, email: str, password: str) -> User:
        """Verify credentials and return the user, or raise UnauthorizedError."""
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated.")
        return user
