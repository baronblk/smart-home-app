"""
Application-level exceptions and FastAPI exception handlers.

All domain-specific exceptions inherit from AppError, which carries
an HTTP status code and machine-readable error code for API responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for all application exceptions."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, detail: str = "An unexpected error occurred.") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"

    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(detail)


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"

    def __init__(self, detail: str = "Resource already exists.") -> None:
        super().__init__(detail)


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"

    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(detail)


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"

    def __init__(self, detail: str = "Insufficient permissions.") -> None:
        super().__init__(detail)


class ProviderConnectionError(AppError):
    status_code = 503
    error_code = "provider_connection_error"

    def __init__(self, detail: str = "Could not connect to device provider.") -> None:
        super().__init__(detail)


class ProviderAuthError(AppError):
    status_code = 503
    error_code = "provider_auth_error"

    def __init__(self, detail: str = "Provider authentication failed.") -> None:
        super().__init__(detail)


class DeviceNotFoundError(NotFoundError):
    error_code = "device_not_found"

    def __init__(self, ain: str = "") -> None:
        detail = f"Device not found: {ain}" if ain else "Device not found."
        super().__init__(detail)


class DeviceCommandError(AppError):
    status_code = 502
    error_code = "device_command_error"

    def __init__(self, detail: str = "Device command failed.") -> None:
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.error_code},
        )
