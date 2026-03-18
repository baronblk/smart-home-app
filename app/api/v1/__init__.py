"""
API v1 router — aggregates all v1 endpoint modules.
"""

from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.automations import router as automations_router
from app.api.v1.devices import router as devices_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.users import router as users_router
from app.api.v1.weather import router as weather_router

router = APIRouter(tags=["v1"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(devices_router, prefix="/devices", tags=["devices"])
router.include_router(schedules_router, prefix="/schedules", tags=["schedules"])
router.include_router(automations_router, prefix="/automations", tags=["automations"])
router.include_router(audit_router, prefix="/audit", tags=["audit"])
router.include_router(weather_router, prefix="/weather", tags=["weather"])
