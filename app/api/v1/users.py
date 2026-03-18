"""
User management endpoints.

GET  /api/v1/users/me     — get own profile
PUT  /api/v1/users/me     — update own profile
POST /api/v1/users/me/password — change password
GET  /api/v1/users        — list all users (admin)
POST /api/v1/users        — create user (admin)
PUT  /api/v1/users/{id}   — update user role (admin)
DELETE /api/v1/users/{id} — delete user (admin)
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.users.models import User
from app.users.schemas import (
    PasswordChange,
    UserCreate,
    UserRead,
    UserUpdate,
    UserUpdateRole,
)
from app.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(require_role(Role.VIEWER))) -> User:
    return current_user


@router.put("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> User:
    service = UserService(session)
    return await service.update_profile(current_user, data)


@router.post("/me/password", status_code=204)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = UserService(session)
    await service.change_password(current_user, data)


@router.get("", response_model=list[UserRead])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> list[User]:
    service = UserService(session)
    return list(await service.list_users(limit=limit, offset=offset))


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> User:
    service = UserService(session)
    return await service.create_user(data)


@router.put("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserUpdateRole,
    current_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> User:
    service = UserService(session)
    user = await service.get_by_id(user_id)
    return await service.set_role(user, data.role, current_user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = UserService(session)
    await service.delete(user_id)
