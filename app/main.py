"""
FastAPI application factory and lifespan.

The 'lifespan' context manager is the single place where startup
and shutdown side-effects are registered. Each feature phase adds
its own startup/shutdown logic here (DB pool, scheduler, provider).
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import api_router
from app.config import settings
from app.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context.

    Startup logic runs before yield; shutdown logic runs after.
    """
    # --- Startup ---
    from app.scheduler.engine import start_scheduler
    start_scheduler()

    yield

    # --- Shutdown ---
    from app.scheduler.engine import stop_scheduler
    stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="smart-home-app",
        description="Production-ready FRITZ!Box smart home controller",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Static files
    app.mount(
        "/static",
        StaticFiles(directory="app/static"),
        name="static",
    )

    # API routes
    app.include_router(api_router)

    # Exception handlers
    register_exception_handlers(app)

    return app


app = create_app()

# ------------------------------------------------------------------
# System endpoints (not versioned)
# ------------------------------------------------------------------
from fastapi import Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


@app.get("/health", tags=["system"])
async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint.

    Returns 200 OK when the application is running.
    Used by Docker healthcheck and load balancers.
    """
    return JSONResponse(content={"status": "ok", "version": "0.1.0"})
