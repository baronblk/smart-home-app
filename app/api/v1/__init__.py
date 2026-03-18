"""
API v1 router — aggregates all v1 endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.devices import router as devices_router
from app.api.v1.users import router as users_router

router = APIRouter(tags=["v1"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(devices_router, prefix="/devices", tags=["devices"])
