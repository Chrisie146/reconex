"""
Error handling middleware and utilities for FastAPI
Provides standardized error responses and logging
"""

import logging
import traceback
from typing import Union, Dict, Any
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from exceptions import AppException, RateLimitError
from config import DEBUG, ENVIRONMENT, Config

# Sentry integration
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response structure"""
    
    @staticmethod
    def create(
        message: str,
        status_code: int,
        error_code: str = "INTERNAL_ERROR",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Create a standardized error response
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details (only in DEBUG mode)
            request_id: Request tracking ID
        
        Returns:
            Dictionary with standardized error structure
        """
        response = {
            "error": {
                "message": message,
                "code": error_code,
                "status": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Only include details in debug mode or for certain error types
        if details and (DEBUG or status_code < 500):
            response["error"]["details"] = details
        
        if request_id:
            response["error"]["request_id"] = request_id
        
        return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Global handler for custom AppException errors
    
    Args:
        request: FastAPI request object
        exc: AppException instance
    
    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Capture in Sentry if enabled and it's a server error
    if SENTRY_AVAILABLE and Config.SENTRY_ENABLED and exc.status_code >= 500:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_type", "app_exception")
            scope.set_tag("error_code", exc.error_code)
            scope.set_tag("status_code", exc.status_code)
            scope.set_context("request", {
                "request_id": request_id,
                "url": str(request.url),
                "method": request.method,
            })
            if exc.details:
                scope.set_context("error_details", exc.details)
            sentry_sdk.capture_exception(exc)
    
    # Log the error
    log_error(
        exc=exc,
        request=request,
        level=logging.WARNING if exc.status_code < 500 else logging.ERROR
    )
    
    # Create standardized response
    response_data = ErrorResponse.create(
        message=exc.message,
        status_code=exc.status_code,
        error_code=exc.error_code,
        details=exc.details if exc.details else None,
        request_id=request_id
    )
    
    # Add Retry-After header for rate limit errors
    headers = {}
    if isinstance(exc, RateLimitError) and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for Pydantic validation errors
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError instance
    
    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    log_error(
        exc=exc,
        request=request,
        level=logging.WARNING,
        extra_info={"validation_errors": errors}
    )
    
    response_data = ErrorResponse.create(
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handler for Starlette HTTP exceptions
    
    Args:
        request: FastAPI request object
        exc: StarletteHTTPException instance
    
    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Capture in Sentry if enabled and it's a server error (500+)
    if SENTRY_AVAILABLE and Config.SENTRY_ENABLED and exc.status_code >= 500:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_type", "http_exception")
            scope.set_tag("status_code", exc.status_code)
            scope.set_context("request", {
                "request_id": request_id,
                "url": str(request.url),
                "method": request.method,
            })
            sentry_sdk.capture_exception(exc)
    
    log_error(
        exc=exc,
        request=request,
        level=logging.WARNING if exc.status_code < 500 else logging.ERROR
    )
    
    # Map common HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    response_data = ErrorResponse.create(
        message=str(exc.detail),
        status_code=exc.status_code,
        error_code=error_code,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unhandled exceptions
    
    Args:
        request: FastAPI request object
        exc: Exception instance
    
    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Capture ALL unhandled exceptions in Sentry
    if SENTRY_AVAILABLE and Config.SENTRY_ENABLED:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_type", "unhandled_exception")
            scope.set_tag("exception_class", type(exc).__name__)
            scope.set_context("request", {
                "request_id": request_id,
                "url": str(request.url),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            })
            # Add user context if available
            if hasattr(request.state, "user_id"):
                scope.set_user({"id": request.state.user_id})
            sentry_sdk.capture_exception(exc)
    
    # Log the full exception with traceback
    log_error(
        exc=exc,
        request=request,
        level=logging.ERROR,
        include_traceback=True
    )
    
    # In production, hide internal error details
    if ENVIRONMENT == "production":
        message = "An internal server error occurred"
        details = None
    else:
        message = str(exc) or "An unexpected error occurred"
        details = {
            "type": type(exc).__name__,
            "traceback": traceback.format_exc() if DEBUG else None
        }
    
    response_data = ErrorResponse.create(
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        details=details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data
    )


def log_error(
    exc: Exception,
    request: Request,
    level: int = logging.ERROR,
    extra_info: Dict[str, Any] = None,
    include_traceback: bool = False
) -> None:
    """
    Log an error with contextual information
    
    Args:
        exc: Exception instance
        request: FastAPI request object
        level: Logging level
        extra_info: Additional information to log
        include_traceback: Whether to include full traceback
    """
    # Extract request context
    request_id = getattr(request.state, "request_id", "unknown")
    user_id = getattr(request.state, "user_id", None)
    
    log_data = {
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else "unknown",
        "user_id": user_id,
        "error_type": type(exc).__name__,
        "error_message": str(exc)
    }
    
    if extra_info:
        log_data.update(extra_info)
    
    # Format log message
    log_message = (
        f"[{log_data['error_type']}] {log_data['error_message']} | "
        f"Request: {log_data['method']} {log_data['url']} | "
        f"Client: {log_data['client']}"
    )
    
    if user_id:
        log_message += f" | User: {user_id}"
    
    # Log with appropriate level
    if include_traceback:
        logger.log(level, log_message, exc_info=True, extra=log_data)
    else:
        logger.log(level, log_message, extra=log_data)


def setup_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    logger.info("Exception handlers registered successfully")
