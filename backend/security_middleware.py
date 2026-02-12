"""
Security headers middleware
Adds security-related HTTP headers to all responses
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from config import ENVIRONMENT, DEBUG


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    Implements OWASP security best practices
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        enable_csp: bool = True,
        enable_frame_options: bool = True,
        enable_content_type_options: bool = True,
        enable_xss_protection: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.enable_frame_options = enable_frame_options
        self.enable_content_type_options = enable_content_type_options
        self.enable_xss_protection = enable_xss_protection
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_permissions_policy = enable_permissions_policy
        
        # HSTS should only be enabled in production with HTTPS
        self.is_production = ENVIRONMENT == "production"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Strict-Transport-Security (HSTS)
        # Forces HTTPS for future connections (only enable in production with HTTPS)
        if self.enable_hsts and self.is_production:
            # max-age=31536000 (1 year), includeSubDomains, preload
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content-Security-Policy (CSP)
        # Prevents XSS, clickjacking, and other code injection attacks
        if self.enable_csp:
            # Restrictive policy for API - adjust based on your frontend needs
            csp_directives = [
                "default-src 'self'",  # Only allow resources from same origin
                "script-src 'self'",   # Only allow scripts from same origin
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles for Swagger UI
                "img-src 'self' data: https:",  # Allow images from same origin, data URIs, and HTTPS
                "font-src 'self' data:",  # Allow fonts from same origin and data URIs
                "connect-src 'self'",  # Allow API calls to same origin only
                "frame-ancestors 'none'",  # Prevent embedding in iframes (equivalent to X-Frame-Options: DENY)
                "base-uri 'self'",  # Restrict base tag URLs
                "form-action 'self'",  # Restrict form submissions
                "object-src 'none'",  # Block Flash, Java, etc.
                "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS automatically
            ]
            
            # More lenient CSP in development for better DX
            if DEBUG:
                csp_directives = [
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                    "img-src 'self' data: https:",
                    "connect-src 'self' http://localhost:* ws://localhost:*",  # Allow dev servers
                ]
            
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # X-Frame-Options
        # Prevents clickjacking by not allowing page to be embedded in iframe
        if self.enable_frame_options:
            response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        # Prevents MIME type sniffing
        if self.enable_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        # Enables browser's XSS filter (legacy, but doesn't hurt)
        if self.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        # Controls how much referrer information is sent
        if self.enable_referrer_policy:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        # Disables browser features that aren't needed
        if self.enable_permissions_policy:
            permissions = [
                "geolocation=()",  # Disable geolocation
                "microphone=()",   # Disable microphone
                "camera=()",       # Disable camera
                "payment=()",      # Disable payment API
                "usb=()",         # Disable USB
                "magnetometer=()", # Disable magnetometer
                "gyroscope=()",   # Disable gyroscope
                "accelerometer=()" # Disable accelerometer
            ]
            response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        # X-Permitted-Cross-Domain-Policies
        # Restricts Adobe Flash and PDF cross-domain requests
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Cache-Control for sensitive endpoints
        # Prevent caching of sensitive data
        if request.url.path.startswith(("/auth/", "/clients/", "/sessions/", "/transactions/")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


def create_security_middleware(
    enable_hsts: bool = None,
    enable_csp: bool = None,
    enable_frame_options: bool = None,
    enable_content_type_options: bool = None,
    enable_xss_protection: bool = None,
    enable_referrer_policy: bool = None,
    enable_permissions_policy: bool = None
) -> SecurityHeadersMiddleware:
    """
    Factory function to create security middleware with environment-based defaults
    
    Args:
        enable_hsts: Enable HSTS (default: True in production only)
        enable_csp: Enable CSP (default: True)
        enable_frame_options: Enable X-Frame-Options (default: True)
        enable_content_type_options: Enable X-Content-Type-Options (default: True)
        enable_xss_protection: Enable X-XSS-Protection (default: True)
        enable_referrer_policy: Enable Referrer-Policy (default: True)
        enable_permissions_policy: Enable Permissions-Policy (default: True)
    
    Returns:
        Configured SecurityHeadersMiddleware instance
    """
    return lambda app: SecurityHeadersMiddleware(
        app=app,
        enable_hsts=enable_hsts if enable_hsts is not None else True,
        enable_csp=enable_csp if enable_csp is not None else True,
        enable_frame_options=enable_frame_options if enable_frame_options is not None else True,
        enable_content_type_options=enable_content_type_options if enable_content_type_options is not None else True,
        enable_xss_protection=enable_xss_protection if enable_xss_protection is not None else True,
        enable_referrer_policy=enable_referrer_policy if enable_referrer_policy is not None else True,
        enable_permissions_policy=enable_permissions_policy if enable_permissions_policy is not None else True
    )
