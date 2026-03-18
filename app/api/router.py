"""
Top-level API router.

All versioned sub-routers are registered here. Import and
include this router in app/main.py.
"""

from fastapi import APIRouter

from app.api.v1 import router as v1_router
from app.api.v1.pages import router as pages_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/api/v1")
api_router.include_router(pages_router)  # HTML page routes (no prefix)
