"""
Bank Statement Analyzer - FastAPI Backend
Production-ready MVP for small business bank statement analysis

Refactored: Routes split into modular router files under backend/routers/
"""

import sys
import os
import logging
import json
import math
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add local lib folder to path so OCR dependencies are found
lib_path = os.path.join(os.path.dirname(__file__), "lib")
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from config import ALLOWED_ORIGINS, DEBUG

from models import init_db, get_db
from error_handler import setup_exception_handlers
from middleware import RequestTrackingMiddleware
from security_middleware import SecurityHeadersMiddleware
from config import Config
from services.cache import get_cache

# Initialize Sentry Error Monitoring
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

if Config.SENTRY_ENABLED:
    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        environment=Config.SENTRY_ENVIRONMENT,
        traces_sample_rate=Config.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=Config.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=Config.SENTRY_SEND_DEFAULT_PII,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        before_send=lambda event, hint: _before_send_sentry(event, hint),
        debug=False,
    )
    logger.info("✅ Sentry error monitoring initialized")
    logger.info(f"   Environment: {Config.SENTRY_ENVIRONMENT}")
    logger.info(f"   Traces Sample Rate: {Config.SENTRY_TRACES_SAMPLE_RATE * 100:.0f}%")
else:
    logger.info("ℹ️  Sentry error monitoring disabled (SENTRY_DSN not configured)")


def _before_send_sentry(event, hint):
    """Filter and modify events before sending to Sentry."""
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, HTTPException) and exc_value.status_code == 404:
            return None
        if isinstance(exc_value, HTTPException) and exc_value.status_code in [401, 403]:
            return None
    event.setdefault("tags", {})
    event["tags"]["environment"] = Config.SENTRY_ENVIRONMENT
    return event


# =============================================================================
# API METADATA
# =============================================================================

api_description = """
## Bank Statement Analyzer API

A production-ready API for analyzing bank statements with support for multiple banks,
automatic categorization, VAT calculation, and invoice matching.

### Features

* 🔐 **JWT Authentication** - Secure user registration and login
* 🏦 **Multi-Bank Support** - FNB, Standard Bank, Capitec, ABSA
* 📊 **Transaction Analysis** - Automatic categorization and merchant extraction
* 💰 **VAT Calculation** - Automatic VAT detection and reporting
* 📄 **Invoice Matching** - Match transactions to uploaded invoices
* 📈 **Monthly Reports** - Generate Excel reports with summaries
* 🔍 **Smart Categorization** - ML-based transaction categorization with learning
"""

tags_metadata = [
    {"name": "Authentication", "description": "User registration, login, and account management"},
    {"name": "Clients", "description": "Manage business clients and their data"},
    {"name": "Uploads", "description": "Upload bank statements (CSV/PDF) and invoices"},
    {"name": "Column Mapping", "description": "Manual column mapping fallback for unsupported bank formats"},
    {"name": "Transactions", "description": "View, search, and manage transactions"},
    {"name": "Categories", "description": "Manage transaction categories and VAT settings"},
    {"name": "Chart of Accounts", "description": "Per-client Chart of Accounts — accounts, hierarchy, and template seeding"},
    {"name": "Rules", "description": "Create and manage categorization rules"},
    {"name": "Reconciliation", "description": "Monthly and overall account reconciliation"},
    {"name": "Invoices", "description": "Upload and match invoices to transactions"},
    {"name": "Reports", "description": "Generate and export analysis reports"},
    {"name": "Sessions", "description": "Manage upload sessions"},
    {"name": "Background Jobs", "description": "Async task management"},
    {"name": "Admin", "description": "Cache and system administration"},
    {"name": "Financial Years", "description": "Define, archive, and view financial years per client"},
    {"name": "Backups", "description": "Trigger and download full database backups"},
]


# =============================================================================
# CUSTOM JSON ENCODER
# =============================================================================


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that safely handles NaN and infinity values."""

    def encode(self, o):
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return str(0.0)
        return super().encode(o)

    def iterencode(self, o, _one_shot=False):
        for chunk in super().iterencode(o, _one_shot):
            yield chunk

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return 0.0
        return super().default(o)


# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Bank Statement Analyzer API",
    description=api_description,
    version="1.0.0",
    debug=DEBUG,
    openapi_tags=tags_metadata,
    contact={"name": "Reconex Support", "email": "support@reconex.app"},
    license_info={"name": "Proprietary"},
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    json_encoder_class=SafeJSONEncoder,
)

# Custom OpenAPI schema with JWT security
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>",
        }
    }
    for path in openapi_schema["paths"]:
        if not path.startswith("/auth/"):
            for method in openapi_schema["paths"][path]:
                if method != "parameters":
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# =============================================================================
# MIDDLEWARE STACK
# =============================================================================

# CORS
logger.info(f"Configuring CORS for {len(ALLOWED_ORIGINS)} origin(s)")
if "*" not in [origin.strip() for origin in ALLOWED_ORIGINS]:
    logger.info(f"✓ CORS configured for: {ALLOWED_ORIGINS}")
else:
    logger.warning("⚠️ WARNING: CORS allows all origins. Set ALLOWED_ORIGINS environment variable in production!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Content-Disposition"],
    max_age=600,
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request tracking
app.add_middleware(RequestTrackingMiddleware)

# Exception handlers
setup_exception_handlers(app)

# Middleware for JSON sanitization and request size limits
from starlette.middleware.base import BaseHTTPMiddleware


class JSONSanitizationMiddleware(BaseHTTPMiddleware):
    """Sanitize NaN and infinity values in responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValueError as e:
            if "Out of range float values" in str(e):
                logger.error(f"[JSON_SANITIZATION] Caught NaN/infinity serialization error: {str(e)}")
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error: Invalid data values. Please try uploading again."},
                )
            raise


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app, max_size: int = 100 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                from exceptions import ValidationError

                raise ValidationError(
                    f"Request body too large. Maximum size: {self.max_size / 1024 / 1024:.0f}MB",
                    details={"max_size_mb": self.max_size / 1024 / 1024},
                )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware, max_size=100 * 1024 * 1024)

logger.info("✅ Security middleware initialized:")
logger.info("   - Security headers (HSTS, CSP, X-Frame-Options, etc.)")
logger.info("   - Request tracking with UUID")
logger.info("   - Request body size limit: 100MB")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        qs = request.url.query
        print(f"[REQ] {request.method} {request.url.path}{('?' + qs) if qs else ''}")
    except Exception:
        pass
    response = await call_next(request)
    return response


# =============================================================================
# STARTUP EVENT
# =============================================================================


@app.on_event("startup")
def startup_event():
    """Initialize database tables and seed system-shipped data."""
    init_db()
    try:
        from services.system_rules.seed import seed_system_rules
        from models import SessionLocal
        db = SessionLocal()
        try:
            seed_system_rules(db)
        finally:
            db.close()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("System rule seeding skipped: %s", exc)


# =============================================================================
# HEALTH CHECK (kept in main for infrastructure monitoring)
# =============================================================================


@app.get("/health", tags=["Monitoring"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for uptime monitoring.

    Returns status of server, database, and cache connectivity.
    """
    import datetime
    from sqlalchemy import text

    response = {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
    }

    try:
        db.execute(text("SELECT 1"))
        response["database"] = "connected"
    except Exception as e:
        response["database"] = f"error: {str(e)[:50]}"

    if Config.CACHE_ENABLED:
        try:
            cache = get_cache()
            if cache and hasattr(cache, "redis_client") and cache.redis_client:
                cache.redis_client.ping()
                response["cache"] = "connected"
            else:
                response["cache"] = "not_configured"
        except Exception:
            response["cache"] = "unavailable"
    else:
        response["cache"] = "disabled"

    return response


# =============================================================================
# REGISTER ROUTERS
# =============================================================================

from routers.accounts import router as accounts_router
from routers.auth import router as auth_router
from routers.categories import router as categories_router
from routers.clients import router as clients_router
from routers.rules import router as rules_router
from routers.upload import router as upload_router
from routers.ocr import router as ocr_router
from routers.transactions import router as transactions_router
from routers.invoices import router as invoices_router
from routers.sessions import router as sessions_router
from routers.reconciliation import router as reconciliation_router
from routers.reports import router as reports_router
from routers.background_jobs import router as background_jobs_router
from routers.admin import router as admin_router
from routers.column_mapping import router as column_mapping_router
from routers.financial_years import router as financial_years_router
from routers.backups import router as backups_router

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(clients_router)
app.include_router(rules_router)
app.include_router(upload_router)
app.include_router(ocr_router)
app.include_router(transactions_router)
app.include_router(invoices_router)
app.include_router(sessions_router)
app.include_router(reconciliation_router)
app.include_router(reports_router)
app.include_router(background_jobs_router)
app.include_router(admin_router)
app.include_router(column_mapping_router)
app.include_router(financial_years_router)
app.include_router(backups_router)

logger.info("✅ All routers registered successfully")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

