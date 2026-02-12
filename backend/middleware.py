"""
Request tracking middleware
Adds unique request IDs for tracing and logging
"""

import uuid
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request IDs and track request duration
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user ID if available (set by auth dependency)
        request.state.user_id = None
        
        # Track request start time
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"Incoming request | ID: {request_id} | "
            f"Method: {request.method} | Path: {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                f"Request completed | ID: {request_id} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration_ms:.2f}ms"
            )
            
            return response
            
        except Exception as exc:
            # Log exception (will also be caught by exception handlers)
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed | ID: {request_id} | "
                f"Error: {type(exc).__name__} | "
                f"Duration: {duration_ms:.2f}ms"
            )
            raise
