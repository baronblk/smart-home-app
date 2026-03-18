"""
API v1 router — aggregates all v1 endpoint modules.
"""
from fastapi import APIRouter

router = APIRouter(tags=["v1"])

# Sub-routers are added here as features are implemented.
# Example (Phase 2):
# from app.api.v1.auth import router as auth_router
# router.include_router(auth_router, prefix="/auth", tags=["auth"])
