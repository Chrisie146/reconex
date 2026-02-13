"""
Bank Statement Analyzer - FastAPI Backend
Production-ready MVP for small business bank statement analysis
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add local lib folder to path so OCR dependencies are found
lib_path = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request, Body, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from config import ALLOWED_ORIGINS, DEBUG, ENVIRONMENT

from models import (
    init_db,
    get_db,
    User,
    Client,
    Transaction,
    Reconciliation,
    OverallReconciliation,
    TransactionMerchant,
    SessionState,
    Rule,
    Invoice,
    InvoiceMatch,
    SessionVATConfig,
)
from auth import (
    get_current_user,
    create_access_token,
    verify_password,
    get_password_hash,
)
from schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ChangePasswordRequest,
)
import json
import re
from sqlalchemy import func, or_, String
from services.parser import validate_csv, normalize_csv
from services.parser import _find_data_start
from services.pdf_parser import pdf_to_csv_bytes, ParserError as PDFParserError
from services.parser import parse_date
from services.bank_detector import BankDetector, BankType
from services.categoriser import categorize_transaction
from services.categoriser import extract_merchant
from services.summary import calculate_monthly_summary, get_category_summary
from services.summary import ExcelExporter
from services.bulk_categorizer import BulkCategorizer
from services.categories_service import CategoriesService
from services.vat_service import VATService
from services import matcher
from services.invoice_parser import extract_invoice_metadata
from services.categorization_learning_service import CategorizationLearningService
from validators import validate_pdf_upload, validate_csv_upload
from rate_limiter import upload_limiter, standard_limiter, read_limiter, add_rate_limit_headers
from exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    FileProcessingError,
    DatabaseError,
)
from error_handler import setup_exception_handlers
from middleware import RequestTrackingMiddleware
from security_middleware import SecurityHeadersMiddleware

# Cloud Storage
from services.storage import get_storage
from config import Config

# Cache Service
from services.cache import get_cache, cached

# Initialize Sentry Error Monitoring
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Configure Sentry if enabled
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
        # Additional options
        before_send=lambda event, hint: _before_send_sentry(event, hint),
        debug=False,  # Enable for Sentry debugging
    )
    logger.info(f"✅ Sentry error monitoring initialized")
    logger.info(f"   Environment: {Config.SENTRY_ENVIRONMENT}")
    logger.info(f"   Traces Sample Rate: {Config.SENTRY_TRACES_SAMPLE_RATE * 100:.0f}%")
else:
    logger.info("ℹ️  Sentry error monitoring disabled (SENTRY_DSN not configured)")


def _before_send_sentry(event, hint):
    """
    Filter and modify events before sending to Sentry
    Use this to filter out noise, add custom tags, or scrub sensitive data
    """
    # Don't send certain expected errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        # Filter out HTTP 404 errors (normal operation)
        if isinstance(exc_value, HTTPException) and exc_value.status_code == 404:
            return None
        # Filter out HTTP 401/403 errors (authentication failures are expected)
        if isinstance(exc_value, HTTPException) and exc_value.status_code in [401, 403]:
            return None
    
    # Add custom tags
    event.setdefault('tags', {})
    event['tags']['environment'] = Config.SENTRY_ENVIRONMENT
    
    return event

# Storage and file access helpers
def generate_file_key(filename: str, prefix: str = "invoices") -> str:
    """Generate a unique object key for cloud storage"""
    unique_id = uuid.uuid4().hex
    safe_filename = filename.replace(" ", "_")
    return f"{prefix}/{unique_id}_{safe_filename}"


def log_file_access(
    db: Session, 
    user_id: int, 
    file_key: str, 
    action: str, 
    request: Request = None, 
    invoice_id: int = None
):
    """Log file access event for audit trail"""
    from models import FileAccessLog
    
    log_entry = FileAccessLog(
        user_id=user_id,
        invoice_id=invoice_id,
        file_key=file_key,
        action=action,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        storage_backend=Config.STORAGE_BACKEND,
    )
    db.add(log_entry)
    db.commit()
    return log_entry


# API Metadata and Documentation
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

### Security

* All endpoints require authentication (except /auth/*)
* Rate limiting on all endpoints
* File upload validation (size, type, MIME)
* Request body size limits (100MB max)
* Security headers (HSTS, CSP, X-Frame-Options, etc.)

### Multi-Tenant Architecture

* Database-level row security
* User-based data isolation
* Client ownership validation on all operations
"""

tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, login, and account management"
    },
    {
        "name": "Clients",
        "description": "Manage business clients and their data"
    },
    {
        "name": "Uploads",
        "description": "Upload bank statements (CSV/PDF) and invoices"
    },
    {
        "name": "Transactions",
        "description": "View, search, and manage transactions"
    },
    {
        "name": "Categories",
        "description": "Manage transaction categories and VAT settings"
    },
    {
        "name": "Rules",
        "description": "Create and manage categorization rules"
    },
    {
        "name": "Reconciliation",
        "description": "Monthly and overall account reconciliation"
    },
    {
        "name": "Invoices",
        "description": "Upload and match invoices to transactions"
    },
    {
        "name": "Reports",
        "description": "Generate and export analysis reports"
    },
]

# Initialize FastAPI app with enhanced documentation
app = FastAPI(
    title="Bank Statement Analyzer API",
    description=api_description,
    version="1.0.0",
    debug=DEBUG,
    openapi_tags=tags_metadata,
    contact={
        "name": "Bank Statement Analyzer Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs" if DEBUG else None,  # Disable Swagger UI in production
    redoc_url="/redoc" if DEBUG else None,  # Disable ReDoc in production
    openapi_url="/openapi.json" if DEBUG else None,  # Disable OpenAPI schema in production
)

# Add JWT security scheme to OpenAPI
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
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>"
        }
    }
    
    # Apply security to all endpoints except auth
    for path in openapi_schema["paths"]:
        if not path.startswith("/auth/"):
            for method in openapi_schema["paths"][path]:
                if method != "parameters":
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Initialize categories service (one per app instance)
categories_service = CategoriesService()

# Initialize VAT service (one per app instance)
vat_service = VATService()

# Initialize categorization learning service
learning_service = CategorizationLearningService()

# CORS Configuration
logger.info(f"Configuring CORS for {len(ALLOWED_ORIGINS)} origin(s)")
if "*" not in [origin.strip() for origin in ALLOWED_ORIGINS]:
    logger.info(f"✓ CORS configured for: {ALLOWED_ORIGINS}")
else:
    logger.warning("⚠️ WARNING: CORS allows all origins. Set ALLOWED_ORIGINS environment variable in production!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add request tracking middleware
app.add_middleware(RequestTrackingMiddleware)

# Register exception handlers
setup_exception_handlers(app)

# Add request body size limit (prevent large payload attacks)
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size"""
    def __init__(self, app, max_size: int = 100 * 1024 * 1024):  # 100MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                from exceptions import ValidationError
                raise ValidationError(
                    f"Request body too large. Maximum size: {self.max_size / 1024 / 1024:.0f}MB",
                    details={"max_size_mb": self.max_size / 1024 / 1024}
                )
        return await call_next(request)

# Add request size limit (100MB max)
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

# Global bulk categorizer (one per session in production)
bulk_categorizer = BulkCategorizer()

# Session-based custom categories storage (in-memory)
# In production, this would be in the database per session
session_custom_categories: dict = {}  # session_id -> [custom_categories]

# In-memory OCR regions store: session_id -> mapping of pages -> regions
# Structure: { session_id: { "pages": { 1: { 'date_region': {...}, ... }, 2: {...} }, "amount_type": "single" } }
ocr_region_store: dict = {}


def ensure_session_access(session_id: str, current_user: User, db: Session) -> None:
    """Validate that the session belongs to the authenticated user via client ownership."""
    if not session_id:
        raise ValidationError("session_id is required")

    client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
    if not client_ids:
        raise NotFoundError("Client", "for user")

    allowed = db.query(Transaction.id).filter(
        Transaction.session_id == session_id,
        Transaction.client_id.in_(client_ids)
    ).first()

    if not allowed:
        raise NotFoundError("Session", session_id)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BulkCategorizeRequest(BaseModel):
    """Request body for bulk categorization"""
    keyword: str
    category: str
    only_uncategorised: bool = True


class CreateCategoryRequest(BaseModel):
    """Request body for creating a custom category"""
    category_name: str
    is_income: bool = False  # True = Income/Sales (VAT Output), False = Expense (VAT Input)


class CreateRuleRequest(BaseModel):
    """Request body for creating a categorization rule"""
    name: str
    category: str
    keywords: List[str]
    priority: int = 10
    auto_apply: bool = True
    match_compound_words: bool = False  # If True, match keywords in compound words


class UpdateRuleRequest(BaseModel):
    """Request body for updating a rule"""
    name: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    auto_apply: Optional[bool] = None
    enabled: Optional[bool] = None
    match_compound_words: Optional[bool] = None


class BulkApplyRulesRequest(BaseModel):
    """Request body for bulk applying rules to transactions"""
    rule_ids: Optional[List[str]] = None
    auto_apply_only: bool = False


class ReconciliationRequest(BaseModel):
    month: str  # YYYY-MM
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None


class OverallReconciliationRequest(BaseModel):
    system_opening_balance: Optional[float] = None
    bank_closing_balance: Optional[float] = None


class BulkDeleteSessionsRequest(BaseModel):
    """Request body for bulk deleting sessions"""
    session_ids: List[str]


class ClearCategoriesRequest(BaseModel):
    """Request body for clearing categories (empty body allowed)"""
    pass


class VATConfigRequest(BaseModel):
    """Request body for VAT configuration"""
    vat_enabled: bool
    default_vat_rate: Optional[float] = 15.0


class UpdateCategoryVATRequest(BaseModel):
    """Request body for updating category VAT settings"""
    vat_applicable: bool
    vat_rate: float = 15.0
    is_income: Optional[bool] = None  # True = Income/Sales (VAT Output), False = Expense (VAT Input)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database tables"""
    init_db()


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/health", tags=["Monitoring"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for uptime monitoring
    
    Returns:
        - status: always "healthy" if server is responding
        - timestamp: current server time (UTC)
        - database: "connected" or "error"
        - cache: "connected" or "error" (if Redis is configured)
        - version: API version
    
    For simple uptime monitoring (UptimeRobot, Pingdom):
    - Monitor this endpoint with 5-minute intervals
    - Expect HTTP 200 status code
    - Alert on any non-200 response or timeout
    """
    import datetime
    from sqlalchemy import text
    
    response = {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }
    
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        response["database"] = "connected"
    except Exception as e:
        response["database"] = f"error: {str(e)[:50]}"
    
    # Check Redis cache if enabled
    if Config.CACHE_ENABLED:
        try:
            cache = get_cache()
            if cache and hasattr(cache, 'redis_client') and cache.redis_client:
                cache.redis_client.ping()
                response["cache"] = "connected"
            else:
                response["cache"] = "not_configured"
        except Exception as e:
            response["cache"] = "unavailable"
    else:
        response["cache"] = "disabled"
    
    return response


# NOTE: Sentry test endpoint removed after successful verification (Feb 12, 2026)
# To test again: @app.get("/debug/sentry-test") -> raise Exception("Test")


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user (accountant)
    
    Args:
        email: User's email address (must be unique)
        password: User's password (plain text, will be hashed)
        full_name: User's full name (optional)
    
    Returns:
        JWT token and user info
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise ConflictError("Email already registered")
        
        # Validate password strength
        if len(request.password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        # Create new user
        hashed_password = get_password_hash(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_password,
            full_name=request.full_name or request.email.split("@")[0]
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create default client for new user
        default_client = Client(
            user_id=new_user.id,
            name="My Business"
        )
        db.add(default_client)
        db.commit()
        db.refresh(default_client)
        
        # Create access token
        access_token = create_access_token(data={"sub": str(new_user.id)})
        
        logger.info(f"✓ New user registered: {request.email} with default client")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name
        )
    
    except (ValidationError, ConflictError):
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise DatabaseError("Failed to register user")


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    
    Args:
        email: User's email
        password: User's password
    
    Returns:
        JWT token and user info
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        
        if not user.is_active:
            raise AuthorizationError("User account is disabled")
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        logger.info(f"✓ User logged in: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name
        )
    
    except (AuthenticationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise DatabaseError("Failed to login")


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile
    
    Requires JWT token in Authorization header
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@app.post("/auth/change-password", tags=["Authentication"])
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    
    Requires JWT token in Authorization header
    """
    try:
        # Verify old password
        if not verify_password(request.old_password, current_user.hashed_password):
            raise AuthenticationError("Old password is incorrect")
        
        # Validate new password
        if len(request.new_password) < 8:
            raise ValidationError("New password must be at least 8 characters")
        
        # Verify passwords match
        if request.new_password != request.new_password_confirm:
            raise ValidationError("Passwords do not match")
        
        # Update password
        current_user.hashed_password = get_password_hash(request.new_password)
        db.commit()
        
        logger.info(f"✓ Password changed for user: {current_user.email}")
        
        return {"success": True, "message": "Password changed successfully"}
    
    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise DatabaseError("Failed to change password")


@app.get("/categories", tags=["Categories"])
def get_categories(session_id: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get list of available transaction categories with transaction counts
    Includes default categories + any custom categories created in this session
    """
    if session_id:
        ensure_session_access(session_id, current_user, db)
        categories = categories_service.get_all_categories(session_id)
        
        # Get transaction counts per category
        from sqlalchemy import func
        category_counts = db.query(
            Transaction.category,
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.session_id == session_id
        ).group_by(Transaction.category).all()
        
        # Create a map of category -> count
        count_map = {cat: count for cat, count in category_counts}
        
        # Build response with counts
        categories_with_counts = [
            {
                "name": cat,
                "transaction_count": count_map.get(cat, 0)
            }
            for cat in categories
        ]
        
        return {"categories": categories_with_counts}
    else:
        # No session - just return category names without counts
        categories = categories_service.get_all_categories()
        categories_with_counts = [
            {
                "name": cat,
                "transaction_count": 0
            }
            for cat in categories
        ]
        return {"categories": categories_with_counts}


@app.post("/categories")
def create_category(request: CreateCategoryRequest, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new custom category for this session
    
    Args:
        category_name: Name of new category
        is_income: True for Income/Sales (VAT Output), False for Expense (VAT Input)
        session_id: Session ID (query param)
    
    Returns:
        Updated list of all categories
    """
    try:
        ensure_session_access(session_id, current_user, db)

        # Use CategoriesService to create category
        success, message = categories_service.create_category(
            session_id, 
            request.category_name,
            is_income=request.is_income
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Return all categories (built-in + custom)
        all_categories = categories_service.get_all_categories(session_id)
        
        return {
            "success": True,
            "message": message,
            "categories": all_categories
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create category: {str(e)}")


# =============================================================================
# VAT MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/vat/config")
def get_vat_config(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get VAT configuration for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        config = vat_service.get_session_vat_config(session_id)
        if config:
            return {
                "vat_enabled": config.vat_enabled == 1,
                "default_vat_rate": config.default_vat_rate
            }
        return {
            "vat_enabled": False,
            "default_vat_rate": 15.0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get VAT config: {str(e)}")


@app.post("/vat/config")
def update_vat_config(session_id: str, request: VATConfigRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enable or disable VAT calculation for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        if request.vat_enabled:
            success, message = vat_service.enable_vat(session_id, request.default_vat_rate)
            if success:
                # Recalculate VAT for all existing transactions
                recalc_success, recalc_msg, stats = vat_service.recalculate_all_transactions(session_id)
                if recalc_success:
                    return {
                        "success": True,
                        "message": message,
                        "recalculation_stats": stats
                    }
                else:
                    return {
                        "success": True,
                        "message": message,
                        "recalculation_error": recalc_msg
                    }
        else:
            success, message = vat_service.disable_vat(session_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update VAT config: {str(e)}")


@app.get("/categories/with-vat")
def get_categories_with_vat(session_id: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all categories with their VAT settings"""
    try:
        if session_id:
            ensure_session_access(session_id, current_user, db)
        categories = categories_service.get_all_categories_with_vat(session_id)
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get categories: {str(e)}")


@app.patch("/categories/{category_name}/vat")
def update_category_vat(category_name: str, request: UpdateCategoryVATRequest, current_user: User = Depends(get_current_user)):
    """Update VAT settings for a custom category"""
    try:
        success, message = vat_service.update_category_vat_settings(
            category_name,
            request.vat_applicable,
            request.vat_rate,
            is_income=request.is_income
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update VAT settings: {str(e)}")


@app.post("/vat/recalculate")
def recalculate_vat(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recalculate VAT for all transactions in a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        success, message, stats = vat_service.recalculate_all_transactions(session_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to recalculate VAT: {str(e)}")


@app.get("/vat/summary")
def get_vat_summary(
    session_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get VAT summary for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        # Parse dates if provided
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        
        summary = vat_service.get_vat_summary(session_id, start, end)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get VAT summary: {str(e)}")


@app.get("/vat/export")
def export_vat_report(
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    export_type: str = "both",
    format: str = "excel",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export VAT report as Excel or CSV
    
    Args:
        session_id: Session ID for transactions
        client_id: Client ID for transactions
        date_from: Start date for filtering (YYYY-MM-DD)
        date_to: End date for filtering (YYYY-MM-DD)
        export_type: Type of export - 'both', 'input_only', or 'output_only'
        format: Output format - 'excel' or 'csv'
    """
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        
        # Validate export_type
        if export_type not in ['both', 'input_only', 'output_only']:
            raise HTTPException(status_code=400, detail="export_type must be 'both', 'input_only', or 'output_only'")
        
        # Parse dates if provided
        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None
        
        # Generate report
        report_bytes = vat_service.export_vat_report(session_id, start, end, format, client_id, export_type)
        
        # Determine filename and content type
        identifier = session_id[:8] if session_id else f"client_{client_id}"
        type_str = export_type.replace('_', '_')
        if format == "csv":
            filename = f"vat_{type_str}_{identifier}.csv"
            media_type = "text/csv"
        else:
            filename = f"vat_{type_str}_{identifier}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return StreamingResponse(
            report_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to export VAT report: {str(e)}")


# =============================================================================
# CLIENTS MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/clients", tags=["Clients"])
def get_clients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all clients for authenticated user with statistics"""
    try:
        # Get clients for authenticated user only
        clients = db.query(Client).filter(Client.user_id == current_user.id).all()
        
        # Build response with statistics
        result = []
        for c in clients:
            # Get distinct session count (statements)
            statement_count = db.query(func.count(func.distinct(Transaction.session_id)))\
                .filter(Transaction.client_id == c.id)\
                .scalar() or 0
            
            # Get total transaction count
            transaction_count = db.query(func.count(Transaction.id))\
                .filter(Transaction.client_id == c.id)\
                .scalar() or 0
            
            # Get last statement date (most recent transaction date)
            last_date = db.query(func.max(Transaction.date))\
                .filter(Transaction.client_id == c.id)\
                .scalar()
            
            result.append({
                "id": c.id,
                "name": c.name,
                "created_at": c.created_at.isoformat(),
                "statement_count": statement_count,
                "transaction_count": transaction_count,
                "last_statement_date": last_date.isoformat() if last_date else None
            })
        
        return {"clients": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch clients: {str(e)}")


@app.post("/clients", tags=["Clients"])
def create_client(name: str = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new client for authenticated user"""
    try:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client = Client(user_id=current_user.id, name=name.strip())
        db.add(client)
        db.commit()
        db.refresh(client)
        
        return {
            "client": {
                "id": client.id,
                "name": client.name,
                "created_at": client.created_at.isoformat(),
                "statement_count": 0,
                "transaction_count": 0,
                "last_statement_date": None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create client: {str(e)}")


@app.put("/clients/{client_id}")
def update_client(client_id: int, name: str = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a client's name (authenticated user only)"""
    try:
        # Verify client belongs to authenticated user
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client.name = name.strip()
        db.commit()
        db.refresh(client)
        
        return {
            "id": client.id,
            "name": client.name,
            "created_at": client.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update client: {str(e)}")


@app.delete("/clients/{client_id}")
def delete_client(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a client and all associated data (authenticated user only)"""
    try:
        # Verify client belongs to authenticated user
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Delete all client data
        db.query(Transaction).filter(Transaction.client_id == client_id).delete()
        db.query(Rule).filter(Rule.client_id == client_id).delete()
        db.query(Invoice).filter(Invoice.client_id == client_id).delete()
        db.query(Reconciliation).filter(Reconciliation.client_id == client_id).delete()
        db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).delete()
        db.query(Client).filter(Client.id == client_id).delete()
        db.commit()
        
        return {"message": "Client deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete client: {str(e)}")


# =============================================================================
# RULES MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/rules", tags=["Rules"])
def get_rules(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all categorization rules for this session"""
    try:
        ensure_session_access(session_id, current_user, db)
        rules = categories_service.get_rules(session_id)
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch rules: {str(e)}")


@app.post("/rules", tags=["Rules"])
def create_rule(request: CreateRuleRequest, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new categorization rule"""
    try:
        ensure_session_access(session_id, current_user, db)
        import uuid
        rule_id = str(uuid.uuid4())
        success, message = categories_service.create_rule(
            session_id=session_id,
            rule_id=rule_id,
            name=request.name,
            category=request.category,
            keywords=request.keywords,
            priority=request.priority,
            auto_apply=request.auto_apply,
            match_compound_words=request.match_compound_words
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message,
            "rule_id": rule_id,
            "rules": categories_service.get_rules(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create rule: {str(e)}")


@app.put("/rules/{rule_id}")
def update_rule(rule_id: str, request: UpdateRuleRequest, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a categorization rule"""
    try:
        ensure_session_access(session_id, current_user, db)
        updates = {k: v for k, v in request.dict().items() if v is not None}
        success, message = categories_service.update_rule(session_id, rule_id, **updates)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message,
            "rules": categories_service.get_rules(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update rule: {str(e)}")


@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a categorization rule"""
    try:
        ensure_session_access(session_id, current_user, db)
        success, message = categories_service.delete_rule(session_id, rule_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message,
            "rules": categories_service.get_rules(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete rule: {str(e)}")


@app.post("/rules/{rule_id}/preview")
def preview_rule(rule_id: str, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Preview which transactions would match a specific rule"""
    try:
        ensure_session_access(session_id, current_user, db)
        # Get transactions for this session
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {
                "id": t.id,
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "category": t.category
            }
            for t in transactions
        ]
        
        preview = categories_service.preview_rule_matches(session_id, rule_id, txn_dicts)
        return preview
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to preview rule: {str(e)}")


@app.post("/rules/apply-bulk")
def apply_rules_bulk(request: BulkApplyRulesRequest, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply rules to all transactions in a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        # Get transactions for this session
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {
                "id": t.id,
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "category": t.category
            }
            for t in transactions
        ]
        
        # Apply rules
        result = categories_service.apply_rules_to_transactions(
            session_id,
            txn_dicts,
            rule_ids=request.rule_ids,
            auto_apply_only=request.auto_apply_only
        )
        
        # Update transactions in database
        updated_ids = []
        for txn_dict in result["transactions"]:
            txn = db.query(Transaction).filter(Transaction.id == txn_dict["id"]).first()
            if txn and txn.category != txn_dict.get("category"):
                txn.category = txn_dict.get("category")
                updated_ids.append(txn.id)
        
        db.commit()
        
        # **RECALCULATE VAT FOR ALL UPDATED TRANSACTIONS**
        for txn_id in updated_ids:
            vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)
        
        return {
            "success": True,
            "message": f"Applied {result['rules_applied']} rule(s) to {result['updated']} transaction(s)",
            "updated_count": result["updated"],
            "rules_applied": result["rules_applied"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to apply rules: {str(e)}")


@app.get("/rules/statistics")
def get_rule_statistics(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get statistics for all rules"""
    try:
        ensure_session_access(session_id, current_user, db)
        # Get transactions for this session
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {
                "id": t.id,
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "category": t.category
            }
            for t in transactions
        ]
        
        stats = categories_service.get_rule_statistics(session_id, txn_dicts)
        return {"statistics": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch statistics: {str(e)}")


# =============================================================================
# LEARNED CATEGORIZATION RULES ENDPOINTS (Auto-Learning)
# =============================================================================

@app.get("/learned-rules")
def get_learned_rules(session_id: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all auto-learned categorization rules for this user
    These rules are created automatically when users assign categories
    """
    try:
        effective_user_id = str(current_user.id)
        
        rules = learning_service.get_learned_rules(effective_user_id, db)
        return {
            "rules": rules,
            "total": len(rules)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch learned rules: {str(e)}")


@app.put("/learned-rules/{rule_id}")
def update_learned_rule(
    rule_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a learned rule (enable/disable, change category, edit pattern)
    """
    try:
        effective_user_id = str(current_user.id)
        
        success, message = learning_service.update_rule(rule_id, effective_user_id, request, db)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")


@app.delete("/learned-rules/{rule_id}")
def delete_learned_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a learned categorization rule"""
    try:
        effective_user_id = str(current_user.id)
        
        success, message = learning_service.delete_rule(rule_id, effective_user_id, db)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


@app.post("/learned-rules/apply")
def apply_learned_rules(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply all learned rules to uncategorized transactions in this session
    Returns the number of transactions auto-categorized
    """
    try:
        ensure_session_access(session_id, current_user, db)
        effective_user_id = str(current_user.id)
        
        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")
        
        # Get uncategorized transactions
        transactions = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        # Apply learned rules
        suggestions = learning_service.apply_learned_rules(effective_user_id, transactions, db)
        
        # Update transactions with suggestions
        updated_count = 0
        updated_ids = []
        for txn_id, category in suggestions.items():
            txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
            if txn:
                txn.category = category
                updated_count += 1
                updated_ids.append(txn_id)
        
        db.commit()
        
        # **RECALCULATE VAT FOR ALL UPDATED TRANSACTIONS**
        for txn_id in updated_ids:
            vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)
        
        return {
            "success": True,
            "message": f"Auto-categorized {updated_count} transaction(s)",
            "updated_count": updated_count,
            "suggestions": suggestions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply learned rules: {str(e)}")


# =============================================================================
# BANK DETECTION ENDPOINT
# =============================================================================

@app.post("/detect-bank")
async def detect_bank_format(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Detect the bank format from an uploaded statement file
    
    Returns:
        - bank_type: Detected bank (standard_bank, absa, capitec, unknown)
        - bank_name: Human-readable bank name
        - confidence: Confidence score (0-1.0)
        - message: Description of detection
    """
    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Parse CSV to get headers and samples
        try:
            df = _find_data_start(file_content)
            if df is None or df.empty:
                raise HTTPException(status_code=400, detail="Could not parse file")
            
            headers_list = list(df.columns)
            sample_rows = df.head(3).values.tolist() if len(df) > 0 else []
            
            bank_type, confidence = BankDetector.detect(headers_list, sample_rows)
            bank_name = BankDetector.get_bank_name(bank_type)
            
            return {
                "bank_type": bank_type.value,
                "bank_name": bank_name,
                "confidence": round(confidence, 3),
                "message": f"Detected {bank_name} with {confidence:.1%} confidence"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Detection failed: {str(e)}")


# =============================================================================
# FILE UPLOAD ENDPOINT
# =============================================================================

@app.post("/upload")
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    preview: bool = False,
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None
):
    """
    Upload and process a bank statement CSV file
    
    Args:
        client_id: Optional client ID for multi-client support
    
    Returns:
        - session_id: Unique identifier for this session
        - transaction_count: Number of transactions processed
        - categories: List of categories found
        - warnings: Any parsing warnings
    """
    # Rate limiting
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    
    # Validate file upload (size, type, content)
    await validate_csv_upload(file)
    
    try:
        # Read file content
        file_content = await file.read()

        # Validate and parse CSV
        is_valid, error_msg = validate_csv(file_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {error_msg}")

        # Parse and normalize CSV (with automatic bank detection)
        normalized_transactions, parse_warnings, skipped_rows, bank_source = normalize_csv(file_content)

        if not normalized_transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in file")
        
        print(f"[UPLOAD] Detected bank source: {bank_source}")

        # Validate client ownership if provided
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # Load enabled rules for potential auto-apply
        try:
            rules_query = db.query(Rule).filter(Rule.enabled == 1)
            if client_id is not None:
                rules_query = rules_query.filter(Rule.client_id == client_id)
            enabled_rules_db = rules_query.order_by(Rule.priority.asc()).all()
            enabled_rules = [
                {
                    "id": r.id,
                    "name": r.name,
                    "priority": r.priority,
                    "conditions": json.loads(r.conditions),
                    "action": json.loads(r.action),
                    "auto_apply": bool(r.auto_apply)
                }
                for r in enabled_rules_db
            ]
        except Exception:
            enabled_rules = []

        # If preview requested, return parsed rows without saving
        if preview:
            # serialize dates to ISO
            serialized = [
                {"date": t["date"].isoformat(), "description": t["description"], "amount": t["amount"]}
                for t in normalized_transactions
            ]
            return {"preview": True, "transactions": serialized, "warnings": parse_warnings or None, "skipped_rows": skipped_rows or None}

        # Create session ID for this upload and save
        session_id = str(uuid.uuid4())
        categories_found = set()
        filename = file.filename or "Statement"

        # Apply enabled rules (auto_apply only) using first-match-wins by priority
        def txn_matches_conditions(txn: dict, conds: dict) -> bool:
            # conds: { match_type: 'all'|'any', conditions: [ {field, op, value} ] }
            match_type = conds.get('match_type', 'all')
            clauses = conds.get('conditions', [])

            def eval_clause(cl):
                f = cl.get('field')
                op = cl.get('op')
                val = cl.get('value')
                v = txn.get(f)
                if v is None:
                    return False
                try:
                    if op == 'contains':
                        return str(val).lower() in str(v).lower()
                    if op == 'equals':
                        return str(v).lower() == str(val).lower()
                    if op == 'regex':
                        return re.search(val, str(v)) is not None
                    if op == 'gt':
                        return float(v) > float(val)
                    if op == 'lt':
                        return float(v) < float(val)
                except Exception:
                    return False
                return False

            results = [eval_clause(c) for c in clauses]
            if match_type == 'any':
                return any(results)
            return all(results)

        for txn_data in normalized_transactions:
            # default categorization from existing logic
            category, is_expense = categorize_transaction(txn_data["description"], txn_data["amount"])

            # wrap txn for evaluation
            tdict = {"description": txn_data["description"], "amount": txn_data["amount"], "date": txn_data.get("date"), "category": category}

            # evaluate rules
            for r in enabled_rules:
                if not r.get('auto_apply'):
                    continue
                try:
                    if txn_matches_conditions(tdict, r.get('conditions', {})):
                        act = r.get('action', {})
                        if act.get('type') == 'set_category' and act.get('category'):
                            category = act.get('category')
                            break  # first-match wins
                        if act.get('type') == 'set_merchant' and act.get('merchant'):
                            # merchant assignment handled later by TransactionMerchant after insert
                            # we can store merchant in txn_data for later
                            txn_data['_merchant'] = act.get('merchant')
                            break
                except Exception:
                    continue

            categories_found.add(category)
            transaction = Transaction(
                client_id=client_id,
                session_id=session_id,
                date=txn_data["date"],
                description=txn_data["description"],
                amount=txn_data["amount"],
                category=category,
                bank_source=bank_source,
                balance_verified=txn_data.get("balance_verified"),
                balance_difference=txn_data.get("balance_difference"),
                validation_message=txn_data.get("validation_message")
            )
            db.add(transaction)
            db.flush()
            # persist merchant if present
            if txn_data.get('_merchant'):
                from models import TransactionMerchant as TM
                tm = TM(transaction_id=transaction.id, session_id=session_id, merchant=txn_data.get('_merchant'))
                db.add(tm)

        db.commit()

        # **APPLY LEARNED CATEGORIZATION RULES**
        # Auto-categorize transactions based on previously learned patterns
        try:
            all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
            effective_user_id = str(current_user.id)
            suggestions = learning_service.apply_learned_rules(effective_user_id, all_transactions, db)
            
            # Update transactions with learned categorizations
            updated_ids = []
            for txn_id, category in suggestions.items():
                txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
                if txn:
                    txn.category = category
                    updated_ids.append(txn_id)
            
            if suggestions:
                db.commit()
                # **RECALCULATE VAT FOR ALL AUTO-CATEGORIZED TRANSACTIONS**
                for txn_id in updated_ids:
                    vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)
                print(f"✓ Auto-categorized {len(suggestions)} transaction(s) using learned rules")
        except Exception as learn_error:
            # Don't fail upload if auto-categorization fails
            print(f"Warning: Failed to apply learned rules: {learn_error}")

        # Create SessionState with friendly name extracted from filename
        # e.g., "FNB_ASPIRE_CURRENT_ACCOUNT_132.csv" -> "FNB Aspire Account 132"
        friendly_name = filename.rsplit('.', 1)[0]  # Remove extension
        friendly_name = friendly_name.replace('_', ' ')  # Replace underscores with spaces
        friendly_name = ' '.join(word.capitalize() for word in friendly_name.split())  # Capitalize
        
        ss = SessionState(session_id=session_id, friendly_name=friendly_name)
        db.add(ss)
        db.commit()

        return {"session_id": session_id, "transaction_count": len(normalized_transactions), "categories": sorted(list(categories_found)), "warnings": parse_warnings or None, "skipped_rows": skipped_rows or None}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Upload error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@app.post("/upload_pdf")
async def upload_pdf_statement(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    preview: bool = False,
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None
):
    """
    Upload a PDF bank statement and attempt to extract transactions.
    
    Args:
        client_id: Optional client ID for multi-client support
    """
    logger.info(f"[PDF_UPLOAD] Starting upload for user {current_user.id}, file: {file.filename}, client_id: {client_id}, preview: {preview}")
    
    # Rate limiting
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    
    # Validate PDF upload (size, type, content)
    try:
        await validate_pdf_upload(file)
    except Exception as e:
        logger.error(f"[PDF_UPLOAD] File validation failed for {file.filename}: {str(e)}")
        raise
    
    try:
        # Read file content
        content = await file.read()
        logger.info(f"[PDF_UPLOAD] File read successfully, size: {len(content)} bytes")

        try:
            csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)
            logger.info(f"[PDF_UPLOAD] PDF parsed successfully, detected year: {statement_year}, bank: {detected_bank}")
        except PDFParserError as pe:
            raise HTTPException(status_code=400, detail=f"PDF parse error: {str(pe)}")

        # Validate generated CSV
        is_valid, error_msg = validate_csv(csv_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Extracted CSV invalid: {error_msg}")

        # Pass detected bank to normalize_csv when available to avoid mis-detection
        normalized_transactions, parse_warnings, skipped_rows, bank_source = normalize_csv(csv_bytes, statement_year, detected_bank if 'detected_bank' in locals() else None)

        if not normalized_transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in PDF")
        
        logger.info(f"[PDF_UPLOAD] Detected bank source: {bank_source}")

        # Validate client ownership if provided
        if client_id is not None:
            logger.info(f"[PDF_UPLOAD] Validating client {client_id} belongs to user {current_user.id}")
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                logger.error(f"[PDF_UPLOAD] Client {client_id} not found or doesn't belong to user {current_user.id}")
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found or doesn't belong to your account")

        # Load enabled rules for potential auto-apply
        try:
            rules_query = db.query(Rule).filter(Rule.enabled == 1)
            if client_id is not None:
                rules_query = rules_query.filter(Rule.client_id == client_id)
            enabled_rules_db = rules_query.order_by(Rule.priority.asc()).all()
            enabled_rules = [
                {
                    "id": r.id,
                    "name": r.name,
                    "priority": r.priority,
                    "conditions": json.loads(r.conditions),
                    "action": json.loads(r.action),
                    "auto_apply": bool(r.auto_apply)
                }
                for r in enabled_rules_db
            ]
        except Exception:
            enabled_rules = []

        # Preview mode: return parsed rows without saving
        if preview:
            serialized = [
                {"date": t["date"].isoformat(), "description": t["description"], "amount": t["amount"]}
                for t in normalized_transactions
            ]
            return {"preview": True, "transactions": serialized, "warnings": parse_warnings or None, "skipped_rows": skipped_rows or None}

        session_id = str(uuid.uuid4())
        categories_found = set()

        # reuse same matching logic as CSV upload
        def txn_matches_conditions(txn: dict, conds: dict) -> bool:
            match_type = conds.get('match_type', 'all')
            clauses = conds.get('conditions', [])
            def eval_clause(cl):
                f = cl.get('field')
                op = cl.get('op')
                val = cl.get('value')
                v = txn.get(f)
                if v is None:
                    return False
                try:
                    if op == 'contains':
                        return str(val).lower() in str(v).lower()
                    if op == 'equals':
                        return str(v).lower() == str(val).lower()
                    if op == 'regex':
                        return re.search(val, str(v)) is not None
                    if op == 'gt':
                        return float(v) > float(val)
                    if op == 'lt':
                        return float(v) < float(val)
                except Exception:
                    return False
                return False
            results = [eval_clause(c) for c in clauses]
            if match_type == 'any':
                return any(results)
            return all(results)

        for txn_data in normalized_transactions:
            category, is_expense = categorize_transaction(txn_data["description"], txn_data["amount"])
            tdict = {"description": txn_data["description"], "amount": txn_data["amount"], "date": txn_data.get("date"), "category": category}
            for r in enabled_rules:
                if not r.get('auto_apply'):
                    continue
                try:
                    if txn_matches_conditions(tdict, r.get('conditions', {})):
                        act = r.get('action', {})
                        if act.get('type') == 'set_category' and act.get('category'):
                            category = act.get('category')
                            break
                        if act.get('type') == 'set_merchant' and act.get('merchant'):
                            txn_data['_merchant'] = act.get('merchant')
                            break
                except Exception:
                    continue

            categories_found.add(category)
            transaction = Transaction(
                session_id=session_id,
                client_id=client_id,
                date=txn_data["date"],
                description=txn_data["description"],
                amount=txn_data["amount"],
                category=category,
                bank_source=bank_source,
                balance_verified=txn_data.get("balance_verified"),
                balance_difference=txn_data.get("balance_difference"),
                validation_message=txn_data.get("validation_message")
            )
            db.add(transaction)
            db.flush()
            if txn_data.get('_merchant'):
                from models import TransactionMerchant as TM
                tm = TM(transaction_id=transaction.id, session_id=session_id, merchant=txn_data.get('_merchant'))
                db.add(tm)

        db.commit()

        # **APPLY LEARNED CATEGORIZATION RULES**
        try:
            all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
            effective_user_id = str(current_user.id)
            suggestions = learning_service.apply_learned_rules(effective_user_id, all_transactions, db)
            
            for txn_id, category in suggestions.items():
                txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
                if txn:
                    txn.category = category
            
            if suggestions:
                db.commit()
                print(f"✓ Auto-categorized {len(suggestions)} transaction(s) using learned rules")
        except Exception as learn_error:
            print(f"Warning: Failed to apply learned rules: {learn_error}")

        # Create SessionState with friendly name from filename
        filename = file.filename or "Statement"
        friendly_name = filename.rsplit('.', 1)[0]  # Remove extension
        friendly_name = friendly_name.replace('_', ' ')  # Replace underscores with spaces
        friendly_name = ' '.join(word.capitalize() for word in friendly_name.split())  # Capitalize
        
        ss = SessionState(session_id=session_id, friendly_name=friendly_name)
        db.add(ss)
        db.commit()

        return {"session_id": session_id, "transaction_count": len(normalized_transactions), "categories": sorted(list(categories_found)), "bank_source": bank_source, "warnings": parse_warnings or None, "skipped_rows": skipped_rows or None}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[PDF_UPLOAD] Unexpected error: {str(e)}")
        logger.error(f"[PDF_UPLOAD] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@app.post("/save_parsed")
def save_parsed_transactions(
    payload: dict,
    client_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save parsed transactions provided as JSON array of {date, description, amount}.

    Returns session_id and counts.
    
    Args:
        client_id: Optional client ID for multi-client support
    """
    try:
        txns = payload.get("transactions") or []
        if not isinstance(txns, list) or not txns:
            raise HTTPException(status_code=400, detail="transactions must be a non-empty list")

        session_id = str(uuid.uuid4())
        categories_found = set()

        # Validate client ownership if provided
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # load enabled auto-apply rules
        try:
            rules_query = db.query(Rule).filter(Rule.enabled == 1)
            if client_id is not None:
                rules_query = rules_query.filter(Rule.client_id == client_id)
            enabled_rules_db = rules_query.order_by(Rule.priority.asc()).all()
            enabled_rules = [
                {"id": r.id, "conditions": json.loads(r.conditions), "action": json.loads(r.action), "auto_apply": bool(r.auto_apply)}
                for r in enabled_rules_db
            ]
        except Exception:
            enabled_rules = []

        def txn_matches_conditions(txn: dict, conds: dict) -> bool:
            match_type = conds.get('match_type', 'all')
            clauses = conds.get('conditions', [])
            def eval_clause(cl):
                f = cl.get('field')
                op = cl.get('op')
                val = cl.get('value')
                v = txn.get(f)
                if v is None:
                    return False
                try:
                    if op == 'contains':
                        return str(val).lower() in str(v).lower()
                    if op == 'equals':
                        return str(v).lower() == str(val).lower()
                    if op == 'regex':
                        return re.search(val, str(v)) is not None
                    if op == 'gt':
                        return float(v) > float(val)
                    if op == 'lt':
                        return float(v) < float(val)
                except Exception:
                    return False
                return False
            results = [eval_clause(c) for c in clauses]
            if match_type == 'any':
                return any(results)
            return all(results)

        for item in txns:
            d = item.get("date")
            desc = item.get("description") or ""
            amount = item.get("amount")
            if not d or amount is None:
                continue
            # parse date string to date
            if isinstance(d, str):
                date_obj = parse_date(d)
                if not date_obj:
                    raise HTTPException(status_code=400, detail=f"Invalid date format: {d}")
            else:
                date_obj = d

            category, is_expense = categorize_transaction(desc, amount)

            tdict = {"description": desc, "amount": amount, "date": date_obj, "category": category}
            for r in enabled_rules:
                if not r.get('auto_apply'):
                    continue
                try:
                    if txn_matches_conditions(tdict, r.get('conditions', {})):
                        act = r.get('action', {})
                        if act.get('type') == 'set_category' and act.get('category'):
                            category = act.get('category')
                            break
                        if act.get('type') == 'set_merchant' and act.get('merchant'):
                            item['_merchant'] = act.get('merchant')
                            break
                except Exception:
                    continue

            categories_found.add(category)
            transaction = Transaction(
                client_id=client_id,
                session_id=session_id,
                date=date_obj,
                description=desc,
                amount=amount,
                category=category,
                balance_verified=item.get("balance_verified"),
                balance_difference=item.get("balance_difference"),
                validation_message=item.get("validation_message")
            )
            db.add(transaction)
            db.flush()
            if item.get('_merchant'):
                from models import TransactionMerchant as TM
                tm = TM(transaction_id=transaction.id, session_id=session_id, merchant=item.get('_merchant'))
                db.add(tm)

        db.commit()

        # **APPLY LEARNED CATEGORIZATION RULES**
        # Auto-categorize transactions based on previously learned patterns
        try:
            all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
            effective_user_id = str(current_user.id)
            suggestions = learning_service.apply_learned_rules(effective_user_id, all_transactions, db)
            
            # Update transactions with learned categorizations
            for txn_id, category in suggestions.items():
                txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
                if txn:
                    txn.category = category
            
            if suggestions:
                db.commit()
                print(f"✓ Auto-categorized {len(suggestions)} transaction(s) using learned rules")
        except Exception as learn_error:
            # Don't fail save if auto-categorization fails
            print(f"Warning: Failed to apply learned rules: {learn_error}")

        return {"session_id": session_id, "transaction_count": len(txns), "categories": sorted(list(categories_found))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# TRANSACTION ENDPOINTS
# =============================================================================


@app.post('/pdf_debug')
async def pdf_debug_extract(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Return raw extracted text and table previews per page to help debug parsing."""
    try:
        content = await file.read()
        # import helpers from pdf_parser
        try:
            from services.pdf_parser import _HAS_PDFPLUMBER, pdfplumber
        except Exception:
            raise HTTPException(status_code=500, detail='PDF debug helper not available')

        if not _HAS_PDFPLUMBER or pdfplumber is None:
            raise HTTPException(status_code=400, detail='pdfplumber not available; install pdfplumber')

        pages_out = []
        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ''
                except Exception:
                    text = ''
                text_preview = text[:5000]
                tables = []
                try:
                    t = page.extract_tables()
                    for table in t:
                        rows_preview = [[('' if c is None else str(c)) for c in row] for row in table[:10]]
                        tables.append(rows_preview)
                except Exception:
                    tables = []

                pages_out.append({'page': i, 'text_preview': text_preview, 'tables': tables})

        return {'pages': pages_out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ocr/regions")
async def save_ocr_regions(payload: dict, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save OCR region definitions for a user's session.

    Expected payload example:
    {
      "page": 1,
      "date_region": { "x": 0.05, "y": 0.2, "w": 0.15, "h": 0.6 },
      "description_region": { "x": 0.2, "y": 0.2, "w": 0.45, "h": 0.6 },
      "amount_region": { "x": 0.7, "y": 0.2, "w": 0.2, "h": 0.6 },
      "amount_type": "single"
    }
    """
    try:
        ensure_session_access(session_id, current_user, db)

        if not payload:
            raise HTTPException(status_code=400, detail="Payload is required")

        # Check if it's multi-page format or single-page format
        has_pages = 'pages' in payload and isinstance(payload['pages'], dict)
        has_single_page = 'page' in payload

        if not has_pages and not has_single_page:
            raise HTTPException(status_code=400, detail="Payload must include either 'pages' (multi-page) or 'page' (single-page) and region definitions")

        page = int(payload.get('page', 1))
        # Basic validation of region coords (0..1) for single-page format
        if has_single_page:
            for key in ['date_region', 'description_region', 'amount_region', 'debit_region', 'credit_region']:
                if key in payload:
                    r = payload[key]
                    for f in ['x', 'y', 'w', 'h']:
                        if f not in r:
                            raise HTTPException(status_code=400, detail=f"Region {key} missing {f}")
                        v = float(r[f])
                        if v < 0 or v > 1:
                            raise HTTPException(status_code=400, detail=f"Region coordinates must be relative 0..1 for {key}")

        # Allow either a single page payload or a multi-page payload (pages dict)
        # If payload contains 'pages', expect structure: { "1": {date_region:..., description_region:...}, "2": {...} }
        entry = ocr_region_store.get(session_id, {'pages': {}, 'amount_type': 'single'})

        if 'pages' in payload and isinstance(payload['pages'], dict):
            for p_str, regs in payload['pages'].items():
                try:
                    pnum = int(p_str)
                except Exception:
                    continue
                # sanitize regions for that page
                regs_filtered = {k: v for k, v in regs.items() if k.endswith('_region')}
                entry['pages'][pnum] = regs_filtered
        else:
            # single page submission
            regs_filtered = {k: payload[k] for k in payload if k.endswith('_region')}
            entry['pages'][page] = regs_filtered

        # persist amount_type if provided
        if 'amount_type' in payload:
            entry['amount_type'] = payload.get('amount_type', entry.get('amount_type', 'single'))

        ocr_region_store[session_id] = entry

        return {"success": True, "message": "Regions saved", "session_id": session_id, "pages_saved": list(entry['pages'].keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ocr/extract")
async def ocr_extract(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    page: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run OCR extraction using previously saved regions for this session.

    Requires `session_id` query parameter referencing regions saved with `/ocr/regions`.
    The uploaded PDF is used to render the page(s) and crop the regions.
    Returns parsed rows, raw OCR snippets and warnings.
    """
    # Rate limiting
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    
    # Validate PDF upload
    await validate_pdf_upload(file)
    
    try:
        ensure_session_access(session_id, current_user, db)
        if not session_id or session_id not in ocr_region_store:
            raise HTTPException(status_code=400, detail="session_id is required and must have saved regions via /ocr/regions")

        content = await file.read()
        saved = ocr_region_store[session_id]
        pages_map = saved.get('pages', {})
        amount_type = saved.get('amount_type', 'single')

        from services.ocr_workflow import run_extraction

        results = {}

        # If a specific page was requested, only run that one
        if page is not None:
            if int(page) not in pages_map:
                raise HTTPException(status_code=400, detail=f"No regions saved for page {page}")
            res = run_extraction(content, pages_map[int(page)], page=int(page))
            results[int(page)] = res
        else:
            # Run extraction for each saved page
            for pnum, regs in pages_map.items():
                res = run_extraction(content, regs, page=int(pnum))
                results[int(pnum)] = res

        return { 'success': True, 'preview': True, 'results': results, 'amount_type': amount_type }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/transactions", tags=["Transactions"])
async def get_transactions(
    request: Request,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for a session or client
    
    Query parameters:
        - session_id (optional): Session ID from upload (legacy)
        - client_id (optional): Filter by client (new multi-client support)
        - category (optional): Filter by category
    """
    
    # Fetch transactions - filter by session_id or client_id
    if session_id:
        ensure_session_access(session_id, current_user, db)
        query = db.query(Transaction).filter(Transaction.session_id == session_id)
    elif client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        query = db.query(Transaction).filter(Transaction.client_id == client_id)
    else:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

    # Optional category filter
    if category and category.strip():
        query = query.filter(Transaction.category == category)

    # Date filters (expect YYYY-MM-DD)
    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Transaction.date >= df)
        except Exception:
            raise HTTPException(status_code=400, detail="date_from must be YYYY-MM-DD")

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Transaction.date <= dt)
        except Exception:
            raise HTTPException(status_code=400, detail="date_to must be YYYY-MM-DD")

    if q and q.strip():
        # simple case-insensitive substring match on description and amount
        like_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Transaction.description.ilike(like_pattern),
                func.cast(Transaction.amount, String).ilike(like_pattern)
            )
        )

    transactions = query.order_by(Transaction.date.desc()).all()
    
    # Apply limit if provided (for dashboard preview)
    if limit and limit > 0:
        transactions = transactions[:limit]
    
    # Get session state friendly names for statement identification
    session_names = {}
    if client_id:
        sessions = db.query(SessionState).join(
            Transaction, Transaction.session_id == SessionState.session_id
        ).filter(Transaction.client_id == client_id).distinct().all()
        session_names = {s.session_id: s.friendly_name for s in sessions}
    elif session_id:
        session_state = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if session_state:
            session_names[session_id] = session_state.friendly_name
    
    return {
        "session_id": session_id,
        "count": len(transactions),
        "transactions": [
            {
                "id": t.id,
                "session_id": t.session_id,
                "statement_name": session_names.get(t.session_id, "Unknown Statement"),
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "invoice_id": t.invoice_id,
                "merchant": (db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first().merchant if db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first() else None),
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat
            }
            for t in transactions
        ]
    }


@app.get("/sessions/{session_id}/validation-report")
def get_validation_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get balance validation report for a statement session.
    Shows which transactions were verified against their balance information.
    """
    ensure_session_access(session_id, current_user, db)
    transactions = db.query(Transaction).filter(
        Transaction.session_id == session_id
    ).order_by(Transaction.date.asc()).all()
    
    if not transactions:
        raise HTTPException(status_code=404, detail=f"No transactions found for session {session_id}")
    
    # Calculate statistics
    verified = sum(1 for t in transactions if t.balance_verified is True)
    failed = sum(1 for t in transactions if t.balance_verified is False)
    no_balance = sum(1 for t in transactions if t.balance_verified is None)
    
    # Calculate income/expenses with verification breakdown
    verified_income = sum(t.amount for t in transactions if t.balance_verified is True and t.amount > 0)
    verified_expenses = sum(t.amount for t in transactions if t.balance_verified is True and t.amount < 0)
    unverified_income = sum(t.amount for t in transactions if t.balance_verified is not True and t.amount > 0)
    unverified_expenses = sum(t.amount for t in transactions if t.balance_verified is not True and t.amount < 0)
    
    total_income = verified_income + unverified_income
    total_expenses = verified_expenses + unverified_expenses
    total_net = total_income + total_expenses
    
    # Group failures by issue
    failures_by_diff = {}
    for t in transactions:
        if t.balance_verified is False:
            diff_bucket = f">{t.balance_difference:.0f}" if t.balance_difference else "unknown"
            if diff_bucket not in failures_by_diff:
                failures_by_diff[diff_bucket] = 0
            failures_by_diff[diff_bucket] += 1
    
    return {
        "session_id": session_id,
        "summary": {
            "total_transactions": len(transactions),
            "verified_count": verified,
            "failed_count": failed,
            "no_balance_count": no_balance,
            "verification_rate": f"{verified / max(1, len(transactions) - no_balance) * 100:.1f}%" if (len(transactions) - no_balance) > 0 else "N/A"
        },
        "financials": {
            "verified": {
                "income": verified_income,
                "expenses": verified_expenses,
                "net": verified_income + verified_expenses
            },
            "unverified": {
                "income": unverified_income,
                "expenses": unverified_expenses,
                "net": unverified_income + unverified_expenses
            },
            "total": {
                "income": total_income,
                "expenses": total_expenses,
                "net": total_net
            }
        },
        "failures_by_difference": failures_by_diff,
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "balance_verified": t.balance_verified,
                "balance_difference": t.balance_difference,
                "validation_message": t.validation_message or ""
            }
            for t in transactions
        ]
    }


@app.post("/invoice/upload")
def upload_invoice(payload: dict = Body(...), session_id: str = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload invoice metadata for matching.

    Body: { supplier_name, invoice_date (YYYY-MM-DD), invoice_number?, total_amount, vat_amount?, file_reference? }
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        ensure_session_access(session_id, current_user, db)

        # Basic validation
        supplier = payload.get("supplier_name")
        inv_date = payload.get("invoice_date")
        total = payload.get("total_amount")
        if not supplier or not inv_date or total is None:
            raise HTTPException(status_code=400, detail="supplier_name, invoice_date and total_amount are required")

        # parse date
        try:
            if isinstance(inv_date, str):
                inv_date_obj = datetime.fromisoformat(inv_date).date()
            else:
                inv_date_obj = inv_date
        except Exception:
            raise HTTPException(status_code=400, detail="invoice_date must be YYYY-MM-DD")

        inv = Invoice(
            session_id=session_id,
            supplier_name=supplier.strip(),
            invoice_date=inv_date_obj,
            invoice_number=payload.get("invoice_number"),
            total_amount=float(total),
            vat_amount=(float(payload.get("vat_amount")) if payload.get("vat_amount") is not None else None),
            file_reference=payload.get("file_reference")
        )
        db.add(inv)
        db.commit()
        return {"success": True, "invoice_id": inv.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/statements")
def get_statements(client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all uploaded statements (sessions) for a client
    Returns session info with transaction counts and date ranges
    """
    try:
        # Get unique session_ids for this user's clients
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            session_ids = db.query(Transaction.session_id).filter(
                Transaction.client_id == client_id
            ).distinct().all()
            session_ids = [s[0] for s in session_ids]
        else:
            client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
            if not client_ids:
                return {"statements": []}
            session_ids = db.query(Transaction.session_id).filter(
                Transaction.client_id.in_(client_ids)
            ).distinct().all()
            session_ids = [s[0] for s in session_ids]

        if not session_ids:
            return {"statements": []}

        sessions = db.query(SessionState).filter(
            SessionState.session_id.in_(session_ids)
        ).all()
        
        result = []
        for session in sessions:
            # Get transaction count and date range for this session
            txn_query = db.query(Transaction).filter(Transaction.session_id == session.session_id)
            if client_id:
                txn_query = txn_query.filter(Transaction.client_id == client_id)
            
            txn_count = txn_query.count()
            
            # Skip if no transactions (shouldn't happen but safety check)
            if txn_count == 0:
                continue
            
            # Get date range
            date_stats = db.query(
                func.min(Transaction.date).label('min_date'),
                func.max(Transaction.date).label('max_date')
            ).filter(Transaction.session_id == session.session_id)
            
            if client_id:
                date_stats = date_stats.filter(Transaction.client_id == client_id)
            
            stats = date_stats.first()
            
            result.append({
                "session_id": session.session_id,
                "friendly_name": session.friendly_name or "Unknown Statement",
                "transaction_count": txn_count,
                "date_from": stats.min_date.isoformat() if stats.min_date else None,
                "date_to": stats.max_date.isoformat() if stats.max_date else None,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        # Sort by created_at descending (newest first)
        result.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        print(f"[DEBUG] Found {len(result)} statements for client {client_id}")
        
        return {"statements": result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/invoices")
def list_invoices(
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Filter by session_id or client_id
        if session_id:
            ensure_session_access(session_id, current_user, db)
            rows = db.query(Invoice).filter(Invoice.session_id == session_id).all()
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            rows = db.query(Invoice).filter(Invoice.client_id == client_id).all()
        else:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "supplier_name": r.supplier_name,
                "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
                "invoice_number": r.invoice_number,
                "total_amount": r.total_amount,
                "vat_amount": r.vat_amount,
                "file_reference": r.file_reference,
            })
        return {"invoices": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invoice/match")
def match_invoices(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Attempt matches for all invoices and bank transactions in the session.
    Returns best match per invoice with confidence score and a human-readable explanation.
    Also persists suggested matches (status='suggested') so user can confirm/reject later.
    """
    try:
        ensure_session_access(session_id, current_user, db)

        # load invoices and transactions
        invoices_db = db.query(Invoice).filter(Invoice.session_id == session_id).all()
        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()

        invoices = [
            {
                "id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "vat_amount": inv.vat_amount,
                "file_reference": inv.file_reference,
            }
            for inv in invoices_db
        ]

        txns = [
            {"id": t.id, "date": t.date.isoformat() if t.date else None, "description": t.description, "amount": t.amount}
            for t in txns_db
        ]

        matches = matcher.find_best_matches(invoices, txns)

        # Persist or update suggested matches
        for m in matches:
            # Upsert a suggested match for this invoice
            inv_id = m.get("invoice_id")
            txn_id = m.get("transaction_id")
            score = int(m.get("score") or 0)
            explanation = m.get("explanation")

            existing = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv_id).first()
            if existing:
                existing.transaction_id = txn_id
                existing.confidence = score
                existing.explanation = explanation
                existing.status = 'suggested'
                existing.suggested_at = datetime.utcnow()
            else:
                im = InvoiceMatch(invoice_id=inv_id, transaction_id=txn_id, confidence=score, explanation=explanation, status='suggested')
                db.add(im)

        db.commit()

        # Build response in requested shape
        out = []
        for m in matches:
            out.append({
                "invoice_id": m.get("invoice_id"),
                "invoice": m.get("invoice"),
                "suggested_transaction_id": m.get("transaction_id"),
                "transaction": m.get("transaction"),
                "confidence": m.get("score"),
                "classification": m.get("classification"),
                "explanation": m.get("explanation"),
            })

        return {"matches": out, "count": len(out)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invoice/match/confirm")
def confirm_match(payload: dict = Body(...), session_id: str = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    User confirms or rejects a suggested match.
    Body: { invoice_id: int, transaction_id: int (optional), confirm: true|false }
    Behavior:
      - If confirm=true: mark matching InvoiceMatch.status='confirmed' and set confirmed_at.
      - If confirm=false: mark InvoiceMatch.status='rejected'.
    Note: This endpoint never posts accounting entries or claims VAT automatically.
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        ensure_session_access(session_id, current_user, db)

        inv_id = payload.get("invoice_id")
        txn_id = payload.get("transaction_id")
        confirm = payload.get("confirm")

        if inv_id is None or confirm is None:
            raise HTTPException(status_code=400, detail="invoice_id and confirm are required")

        # Validate that the invoice belongs to this session
        invoice = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.session_id != session_id:
            raise HTTPException(status_code=403, detail="Invoice does not belong to this session")

        im = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv_id).first()
        if not im:
            raise HTTPException(status_code=404, detail="Suggested match not found for this invoice")

        if confirm:
            # Ensure transaction_id matches suggested one if provided
            if txn_id is not None and im.transaction_id != txn_id:
                # allow confirmation to a different txn_id: update it but still treat as user action
                im.transaction_id = txn_id
            im.status = 'confirmed'
            im.confirmed_at = datetime.utcnow()
            
            # Link the transaction to the invoice
            txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
            if txn:
                txn.invoice_id = inv_id
        else:
            im.status = 'rejected'
            im.confirmed_at = datetime.utcnow()
            
            # Remove invoice link if rejecting
            txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
            if txn:
                txn.invoice_id = None

        db.commit()

        return {"success": True, "invoice_id": inv_id, "transaction_id": im.transaction_id, "status": im.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/invoice/matches")
def list_matches(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List suggested/confirmed/rejected matches for a session."""
    try:
        ensure_session_access(session_id, current_user, db)
        # join invoices and invoice_matches and include suggested transaction details
        rows = db.query(Invoice, InvoiceMatch).filter(Invoice.session_id == session_id).outerjoin(InvoiceMatch, InvoiceMatch.invoice_id == Invoice.id).all()
        out = []
        for inv, im in rows:
            txn_obj = None
            if im and im.transaction_id:
                txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
                if txn:
                    txn_obj = {"id": txn.id, "date": txn.date.isoformat() if txn.date else None, "description": txn.description, "amount": txn.amount}

            row = {
                "invoice_id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "total_amount": inv.total_amount,
                "match_status": im.status if im else None,
                "suggested_transaction_id": im.transaction_id if im else None,
                "transaction": txn_obj,
                "confidence": im.confidence if im else None,
                "explanation": im.explanation if im else None,
            }
            out.append(row)
        return {"matches": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/unmatched")
def unmatched_view(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return bank transactions without confirmed invoice matches and invoices without confirmed transaction matches."""
    try:
        ensure_session_access(session_id, current_user, db)

        # transactions with confirmed matches
        confirmed_txn_ids = {im.transaction_id for im in db.query(InvoiceMatch).filter(InvoiceMatch.status == 'confirmed').all()}
        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        unmatched_txns = [
            {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": t.amount}
            for t in txns_db if t.id not in confirmed_txn_ids
        ]

        # invoices with confirmed matches
        confirmed_inv_ids = {im.invoice_id for im in db.query(InvoiceMatch).filter(InvoiceMatch.status == 'confirmed').all()}
        invs_db = db.query(Invoice).filter(Invoice.session_id == session_id).all()
        unmatched_invoices = [
            {"id": i.id, "supplier_name": i.supplier_name, "invoice_date": i.invoice_date.isoformat(), "total_amount": i.total_amount}
            for i in invs_db if i.id not in confirmed_inv_ids
        ]

        return {"unmatched_transactions": unmatched_txns, "unmatched_invoices": unmatched_invoices}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/bulk-categorise/ids")
def bulk_categorize_by_ids(
    payload: dict,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply a category to an explicit list of transaction IDs for a session.

    Body payload: { "ids": [1,2,3], "category": "Fees & Charges" }
    """
    try:
        ensure_session_access(session_id, current_user, db)

        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        ids = payload.get("ids") or []
        category = payload.get("category")

        if not ids or not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="ids must be a non-empty list")
        if not category or not category.strip():
            raise HTTPException(status_code=400, detail="category is required")

        # Fetch transactions to update (ensure they belong to session)
        txns_db = db.query(Transaction).filter(
            Transaction.session_id == session_id,
            Transaction.id.in_(ids)
        ).all()

        if not txns_db:
            raise HTTPException(status_code=404, detail="No matching transactions found for these IDs")

        # Save original state for undo
        original_state = [
            {"id": t.id, "category": t.category, "description": t.description}
            for t in txns_db
        ]

        # Update
        for t in txns_db:
            t.category = category
        db.commit()
        
        # **RECALCULATE VAT FOR ALL UPDATED TRANSACTIONS**
        for t in txns_db:
            vat_service.apply_vat_to_transaction(t.id, session_id, force=False)
        
        # Learn from this bulk categorization
        try:
            # Use the first transaction as representative for learning
            if txns_db:
                representative_txn = txns_db[0]
                # Get merchant if it exists
                merchant = None
                tm = db.query(TransactionMerchant).filter(
                    TransactionMerchant.transaction_id == representative_txn.id
                ).first()
                if tm:
                    merchant = tm.merchant
                
                effective_user_id = str(current_user.id)
                learned_rules = learning_service.learn_from_categorization(
                    user_id=effective_user_id,
                    session_id=session_id,
                    description=representative_txn.description,
                    category=category,
                    merchant=merchant,
                    keyword=None,  # No keyword for ID-based selection
                    db=db
                )
                if learned_rules:
                    print(f"Learned {len(learned_rules)} rules from bulk categorization by IDs")
        except Exception as e:
            print(f"Warning: Failed to learn from bulk categorization: {e}")
            # Don't fail the whole operation for learning issues

        # Record undo action in bulk_categorizer
        try:
            import uuid
            action_id = str(uuid.uuid4())
            from services.bulk_categorizer import BulkAction
            bulk_categorizer.last_action = BulkAction(
                action_id=action_id,
                keyword="by_ids",
                category=category,
                timestamp=datetime.utcnow().isoformat(),
                matched_transactions=original_state,
                transaction_ids=[t["id"] for t in original_state]
            )
        except Exception:
            # non-fatal: undo will not be available
            pass

        # Return updated list
        updated_transactions_db = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()

        updated_transactions = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat
            }
            for t in updated_transactions_db
        ]

        return {
            "updated_count": len(txns_db),
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
            "message": f"Updated {len(txns_db)} transaction(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Bulk by IDs failed: {str(e)}")


@app.put("/transactions/{transaction_id}")
def update_transaction_category(
    transaction_id: int, 
    request: dict,
    session_id: str,
    current_user: User = Depends(get_current_user),
    learn_rule: bool = False,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update the category of a single transaction
    
    Args:
        transaction_id: ID of the transaction to update
        request: Request body with category field
        session_id: Session ID (query param)
        learn_rule: If true, create a learned rule for this categorization (query param)
        keyword: Optional keyword for pattern matching in learned rule (query param)
    
    Returns:
        Updated transaction data
    """
    try:
        ensure_session_access(session_id, current_user, db)
        
        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        category = request.get("category")
        new_description = request.get("description")  # Optional description update
        
        # At least one of category or description must be provided
        if not category and not new_description:
            raise HTTPException(status_code=400, detail="Either category or description is required")
        
        # Find the transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.session_id == session_id
        ).first()
        
        if not transaction:
            # Provide helpful diagnostic information for 404 errors
            
            # Check if transaction exists in ANY session
            txn_any_session = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            
            # Check if session has ANY transactions
            session_has_txns = db.query(Transaction).filter(Transaction.session_id == session_id).count()
            
            if txn_any_session and txn_any_session.session_id != session_id:
                # Transaction exists but in a different session
                detail = f"Transaction {transaction_id} exists in a different session. Session mismatch. Please refresh the page."
            elif session_has_txns == 0 and txn_any_session:
                # This session has no transactions, but other sessions do
                detail = "This session has no transactions. The database may have been reset. Please upload a new statement."
            elif session_has_txns == 0:
                # No transactions anywhere
                detail = "No transactions found. Please upload a bank statement first."
            else:
                # Transaction truly doesn't exist for this session
                detail = f"Transaction {transaction_id} not found in current session."
            
            raise HTTPException(status_code=404, detail=detail)
        
        # Update the category if provided
        if category:
            transaction.category = category
        
        # Update description if provided (with warning - affects rules)
        if new_description is not None and new_description != transaction.description:
            transaction.description = new_description
            print(f"⚠️  Description updated for transaction {transaction_id}: '{transaction.description}' -> '{new_description}'")
        
        db.commit()
        
        # Invalidate cache for this session
        cache = get_cache()
        cache.invalidate_session(session_id)
        
        # **RECALCULATE VAT IF CATEGORY CHANGED**
        # When category changes, VAT applicability may change
        if category:
            vat_service.apply_vat_to_transaction(transaction_id, session_id, force=False)
        
        # **LEARN FROM THIS CATEGORIZATION** (only if explicitly requested and category was provided)
        # Create pattern-based rules so similar transactions are auto-categorized in future
        if learn_rule and category:
            try:
                # Get merchant if it exists
                merchant = None
                tm = db.query(TransactionMerchant).filter(
                    TransactionMerchant.transaction_id == transaction_id
                ).first()
                if tm:
                    merchant = tm.merchant
                
                learned_rules = learning_service.learn_from_categorization(
                    user_id=str(current_user.id),
                    session_id=session_id,
                    description=transaction.description,
                    category=category,
                    merchant=merchant,
                    keyword=keyword,  # Pass keyword separately
                    db=db
                )
                # Log how many rules were learned (optional)
                if learned_rules:
                    print(f"✓ Learned {len(learned_rules)} new categorization pattern(s) for user {str(current_user.id)}")
                    if keyword:
                        print(f"  Using keyword: '{keyword}' (contains pattern)")
                
                # **APPLY TO ALL MATCHING TRANSACTIONS IN CURRENT SESSION**
                # Update all other transactions with the keyword in their description
                if keyword and len(keyword.strip()) >= 3:
                    keyword_upper = keyword.strip().upper()
                    # Find all transactions in this session containing the keyword
                    matching_transactions = db.query(Transaction).filter(
                        Transaction.session_id == session_id,
                        Transaction.id != transaction_id,  # Exclude the current one (already updated)
                        Transaction.description.ilike(f"%{keyword_upper}%")
                    ).all()
                    
                    updated_count = 0
                    for txn in matching_transactions:
                        txn.category = category
                        updated_count += 1
                    
                    if updated_count > 0:
                        db.commit()
                        # Recalculate VAT for all matching transactions
                        for txn in matching_transactions:
                            vat_service.apply_vat_to_transaction(txn.id, session_id, force=False)
                        print(f"  ✓ Also updated {updated_count} matching transaction(s) in current session")
                
            except Exception as learn_error:
                # Don't fail the update if learning fails, just log it
                print(f"Warning: Failed to learn from categorization: {learn_error}")
        
        # Refresh transaction to get updated VAT fields
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.session_id == session_id
        ).first()
        
        return {
            "id": transaction.id,
            "date": transaction.date.isoformat(),
            "description": transaction.description,
            "amount": transaction.amount,
            "category": transaction.category,
            "vat_amount": transaction.vat_amount,
            "amount_excl_vat": transaction.amount_excl_vat,
            "amount_incl_vat": transaction.amount_incl_vat
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.put("/transactions/{transaction_id}/merchant")
def update_transaction_merchant(transaction_id: int, request: dict, session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update or set merchant for a single transaction"""
    try:
        merchant = request.get("merchant")
        if merchant is None:
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # ensure transaction exists
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if session_id and txn.session_id != session_id:
            raise HTTPException(status_code=404, detail="Transaction not found in this session")
        if client_id and txn.client_id != client_id:
            raise HTTPException(status_code=404, detail="Transaction not found for this client")

        # Check if session is locked if session_id provided
        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        # If merchant is blank, treat as clearing the merchant assignment
        if str(merchant).strip() == "":
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction_id).first()
            if tm:
                db.delete(tm)
                db.commit()
            return {"id": transaction_id, "merchant": None}

        # Otherwise create or update mapping
        tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction_id).first()
        if not tm:
            tm = TransactionMerchant(transaction_id=transaction_id, session_id=txn.session_id, merchant=merchant)
            db.add(tm)
        else:
            tm.merchant = merchant

        db.commit()

        return {"id": transaction_id, "merchant": merchant}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transactions/{transaction_id}/merchant/similar")
def apply_merchant_to_similar(transaction_id: int, request: dict, session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply merchant to transactions with the same description as the given transaction"""
    try:
        merchant = request.get("merchant")
        if merchant is None:
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # Get the source transaction
        source_txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not source_txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Check if session is locked if session_id provided
        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        # Find all transactions with the same description within the same session/client scope
        similar_query = db.query(Transaction).filter(
            Transaction.description == source_txn.description,
            Transaction.id != transaction_id  # Exclude the source transaction
        )
        if session_id:
            similar_query = similar_query.filter(Transaction.session_id == session_id)
        if client_id:
            similar_query = similar_query.filter(Transaction.client_id == client_id)
        similar_txns = similar_query.all()

        if not similar_txns:
            return {"updated_count": 0, "message": "No similar transactions found"}

        updated = 0
        for t in similar_txns:
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=t.id, session_id=t.session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if tm.merchant != merchant:
                    tm.merchant = merchant
                    updated += 1

        db.commit()

        return {"updated_count": updated, "message": f"Applied merchant '{merchant}' to {updated} similar transactions"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transactions/clear-categories")
def clear_all_categories(request: Optional[ClearCategoriesRequest] = Body(None), session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Clear categories from all transactions in a session or client"""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # Prevent modifications if session is locked
        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        # Get all transactions for this session or client
        if session_id:
            transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            transactions = db.query(Transaction).filter(Transaction.client_id == client_id).all()
        
        if not transactions:
            return {"success": True, "cleared_count": 0, "message": "No transactions to clear"}

        # Clear categories for all transactions
        count = 0
        for txn in transactions:
            if txn.category:
                txn.category = ""
                count += 1

        db.commit()

        return {"success": True, "cleared_count": count, "message": f"Cleared categories from {count} transaction(s)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/invoice/download")
def download_invoice_file(request: Request, invoice_id: int, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a secure, time-limited download URL for the invoice PDF."""
    try:
        ensure_session_access(session_id, current_user, db)
        inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.session_id == session_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not inv.file_reference:
            raise HTTPException(status_code=404, detail="No file attached to this invoice")
        
        # Get storage backend
        storage = get_storage()
        file_key = inv.file_reference
        
        # Verify file exists
        if not storage.file_exists(file_key):
            raise HTTPException(status_code=404, detail="Invoice file not found in storage")
        
        # Log file access
        log_file_access(db, current_user.id, file_key, "generate_url", request, inv.id)
        
        # Generate signed URL for cloud storage or return file for local storage
        if Config.STORAGE_BACKEND == "local":
            # For local storage, return file directly
            local_path = storage.generate_signed_url(file_key)
            return FileResponse(local_path, media_type='application/pdf', filename=os.path.basename(file_key))
        else:
            # For cloud storage, return signed URL
            signed_url = storage.generate_signed_url(file_key, expiration_seconds=Config.SIGNED_URL_EXPIRATION_SECONDS)
            return {"download_url": signed_url, "expires_in_seconds": Config.SIGNED_URL_EXPIRATION_SECONDS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/invoice/upload_file")
async def upload_invoice_file(
    request: Request,
    supplier_name: str = None,
    invoice_date: str = None,
    total_amount: float = None,
    invoice_number: Optional[str] = None,
    vat_amount: Optional[float] = None,
    file: UploadFile = File(None),
    session_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an invoice PDF (multipart/form-data) along with metadata.

    Form fields: supplier_name, invoice_date (YYYY-MM-DD), total_amount, invoice_number (opt), vat_amount (opt), file (pdf)
    Query: session_id
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")

        ensure_session_access(session_id, current_user, db)

        if not supplier_name or not invoice_date or total_amount is None:
            raise HTTPException(status_code=400, detail="supplier_name, invoice_date and total_amount are required")

        # parse date
        try:
            if isinstance(invoice_date, str):
                inv_date_obj = datetime.fromisoformat(invoice_date).date()
            else:
                inv_date_obj = invoice_date
        except Exception:
            raise HTTPException(status_code=400, detail="invoice_date must be YYYY-MM-DD")

        file_key = None
        if file:
            # Only accept PDFs
            filename = file.filename or 'invoice.pdf'
            if not filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed for file upload")
            
            # Upload to cloud storage
            content = await file.read()
            file_key = generate_file_key(filename, prefix="invoices")
            storage = get_storage()
            storage.upload_file(content, file_key, content_type="application/pdf")

        inv = Invoice(
            session_id=session_id,
            supplier_name=supplier_name.strip(),
            invoice_date=inv_date_obj,
            invoice_number=invoice_number,
            total_amount=float(total_amount),
            vat_amount=(float(vat_amount) if vat_amount is not None else None),
            file_reference=file_key
        )
        db.add(inv)
        db.commit()
        
        # Log file upload
        if file_key:
            log_file_access(db, current_user.id, file_key, "upload", request, inv.id)
        
        return {"success": True, "invoice_id": inv.id, "file_key": file_key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invoice/upload_file_auto")
async def upload_invoice_file_auto(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an invoice PDF and automatically extract metadata, create invoice, and suggest a match."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")
        ensure_session_access(session_id, current_user, db)
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        filename = file.filename or 'invoice.pdf'
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        content = await file.read()

        # Upload to cloud storage
        file_key = generate_file_key(filename, prefix="invoices")
        storage = get_storage()
        storage.upload_file(content, file_key, content_type="application/pdf")

        # Extract metadata
        meta = extract_invoice_metadata(content)
        if not meta.get('supplier_name') and not meta.get('total_amount'):
            # minimal sanity check
            raise HTTPException(status_code=400, detail="Failed to extract key fields from invoice. Please provide metadata manually.")

        inv = Invoice(
            session_id=session_id,
            supplier_name=(meta.get('supplier_name') or '').strip() or 'Unknown Supplier',
            invoice_date=meta.get('invoice_date'),
            invoice_number=meta.get('invoice_number'),
            total_amount=float(meta.get('total_amount') or 0.0),
            vat_amount=(float(meta.get('vat_amount')) if meta.get('vat_amount') is not None else None),
            file_reference=file_key
        )
        db.add(inv)
        db.commit()
        
        # Log file upload
        log_file_access(db, current_user.id, file_key, "upload", request, inv.id)

        # Run matching against transactions in this session
        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txns = [{"id": t.id, "date": t.date.isoformat() if t.date else None, "description": t.description, "amount": t.amount} for t in txns_db]
        invoices = [{
            "id": inv.id,
            "supplier_name": inv.supplier_name,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "invoice_number": inv.invoice_number,
            "total_amount": inv.total_amount,
            "vat_amount": inv.vat_amount,
            "file_key": inv.file_reference
        }]

        matches = matcher.find_best_matches(invoices, txns)
        m = matches[0] if matches else None
        # persist suggestion
        if m:
            existing = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv.id).first()
            if existing:
                existing.transaction_id = m.get('transaction_id')
                existing.confidence = int(m.get('score') or 0)
                existing.explanation = m.get('explanation')
                existing.status = 'suggested'
                existing.suggested_at = datetime.utcnow()
            else:
                im = InvoiceMatch(invoice_id=inv.id, transaction_id=m.get('transaction_id'), confidence=int(m.get('score') or 0), explanation=m.get('explanation'), status='suggested')
                db.add(im)
            db.commit()

        return {
            "success": True,
            "invoice": invoices[0],
            "extracted_meta": meta,
            "suggested_match": m
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invoice/upload_file_direct")
async def upload_invoice_file_direct(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    transaction_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an invoice PDF and directly link to a specific transaction (no matching)."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")
        ensure_session_access(session_id, current_user, db)
        if not transaction_id:
            raise HTTPException(status_code=400, detail="transaction_id query parameter is required")
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        filename = file.filename or 'invoice.pdf'
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Verify transaction exists and belongs to session
        txn = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.session_id == session_id
        ).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found in this session")

        content = await file.read()

        # Upload to cloud storage
        file_key = generate_file_key(filename, prefix="invoices")
        storage = get_storage()
        storage.upload_file(content, file_key, content_type="application/pdf")

        # Extract metadata
        meta = extract_invoice_metadata(content)
        if not meta.get('supplier_name') and not meta.get('total_amount'):
            raise HTTPException(status_code=400, detail="Failed to extract key fields from invoice. Please provide metadata manually.")

        # Use transaction date as fallback if invoice date extraction failed
        invoice_date = meta.get('invoice_date') or txn.date

        # Create invoice
        inv = Invoice(
            session_id=session_id,
            supplier_name=(meta.get('supplier_name') or '').strip() or 'Unknown Supplier',
            invoice_date=invoice_date,
            invoice_number=meta.get('invoice_number'),
            total_amount=float(meta.get('total_amount') or 0.0),
            vat_amount=(float(meta.get('vat_amount')) if meta.get('vat_amount') is not None else None),
            file_reference=file_key
        )
        db.add(inv)
        db.commit()
        
        # Log file upload
        log_file_access(db, current_user.id, file_key, "upload", request, inv.id)

        # Directly link to the transaction (confirmed match)
        existing_match = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv.id).first()
        if not existing_match:
            im = InvoiceMatch(
                invoice_id=inv.id,
                transaction_id=transaction_id,
                confidence=100,  # Direct upload = 100% confidence
                explanation="Directly uploaded for this transaction",
                status='confirmed'
            )
            db.add(im)
            db.commit()

        return {
            "success": True,
            "invoice": {
                "id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "vat_amount": inv.vat_amount,
                "file_reference": inv.file_reference,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            },
            "transaction_id": transaction_id,
            "message": "Invoice linked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/bulk-merchant/ids")
def bulk_set_merchant_by_ids(payload: dict = Body(...), session_id: str = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply a merchant name to an explicit list of transaction IDs for a session."""
    try:
        ensure_session_access(session_id, current_user, db)

        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        ids = payload.get("ids") or []
        merchant = payload.get("merchant")

        if not ids or not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="ids must be a non-empty list")
        if merchant is None or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id, Transaction.id.in_(ids)).all()
        if not txns_db:
            raise HTTPException(status_code=404, detail="No matching transactions found for these IDs")

        updated = 0
        for t in txns_db:
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=t.id, session_id=session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if tm.merchant != merchant:
                    tm.merchant = merchant
                    updated += 1

        db.commit()

        return {"updated_count": updated, "message": f"Updated {updated} transaction(s) with merchant '{merchant}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/bulk-merchant")
def bulk_set_merchant_by_keyword(request: dict = Body(...), session_id: str = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply a merchant to transactions matching a keyword (uses BulkCategorizer matching logic)."""
    try:
        ensure_session_access(session_id, current_user, db)

        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        keyword = request.get("keyword")
        merchant = request.get("merchant")
        only_unassigned = request.get("only_unassigned", True)

        if not merchant or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        # Load all transactions for session as dicts
        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        transactions = [
            {"id": t.id, "description": t.description, "category": t.category, "date": t.date, "amount": t.amount}
            for t in txns_db
        ]

        from services.bulk_categorizer import BulkCategorizer
        bc = BulkCategorizer()
        matching_ids = bc.find_matching_transactions(transactions, keyword or "", only_uncategorised=only_unassigned)

        if not matching_ids:
            return {"updated_count": 0, "message": "No matching transactions"}

        updated = 0
        for tid in matching_ids:
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == tid).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=tid, session_id=session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if not only_unassigned or not tm.merchant:
                    if tm.merchant != merchant:
                        tm.merchant = merchant
                        updated += 1

        db.commit()
        return {"updated_count": updated, "message": f"Updated {updated} transaction(s) with merchant '{merchant}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/merchant-rules/learn")
def upsert_merchant_rule(request: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create or update a merchant auto-apply rule based on a keyword in description."""
    try:
        keyword = (request.get("keyword") or "").strip()
        merchant = request.get("merchant")
        auto_apply = bool(request.get("auto_apply", True))
        enabled = bool(request.get("enabled", True))

        if not keyword or len(keyword) < 3:
            raise HTTPException(status_code=400, detail="keyword must be at least 3 characters")
        if merchant is None or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        keyword_norm = keyword.lower()
        existing_rule = None

        # Look for an existing merchant rule that matches this keyword
        rules = db.query(Rule).all()
        for r in rules:
            try:
                conds = json.loads(r.conditions)
                action = json.loads(r.action)
            except Exception:
                continue

            if action.get("type") != "set_merchant":
                continue

            clauses = conds.get("conditions", []) if isinstance(conds, dict) else []
            for clause in clauses:
                if (
                    clause.get("field") == "description"
                    and clause.get("op") == "contains"
                    and str(clause.get("value", "")).strip().lower() == keyword_norm
                ):
                    existing_rule = r
                    break
            if existing_rule:
                break

        if existing_rule:
            action = json.loads(existing_rule.action)
            action["type"] = "set_merchant"
            action["merchant"] = merchant
            existing_rule.action = json.dumps(action)
            existing_rule.auto_apply = 1 if auto_apply else 0
            existing_rule.enabled = 1 if enabled else 0
            existing_rule.name = f"Merchant: {merchant} ({keyword})"
            db.commit()
            return {"success": True, "updated": True, "id": existing_rule.id}

        conditions = {
            "match_type": "all",
            "conditions": [
                {"field": "description", "op": "contains", "value": keyword}
            ]
        }
        action = {"type": "set_merchant", "merchant": merchant}

        r = Rule(
            name=f"Merchant: {merchant} ({keyword})",
            enabled=1 if enabled else 0,
            priority=int(request.get("priority", 100)),
            conditions=json.dumps(conditions),
            action=json.dumps(action),
            auto_apply=1 if auto_apply else 0
        )
        db.add(r)
        db.commit()
        return {"success": True, "created": True, "id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/merchants")
def list_merchants(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return list of merchants known for this session. Includes heuristically extracted merchants from descriptions."""
    try:
        ensure_session_access(session_id, current_user, db)
        # merchants saved explicitly
        rows = db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).all()
        merchants = {r.merchant for r in rows if r.merchant}

        # also extract heuristics from transactions to suggest candidates
        txns = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        for t in txns:
            m = extract_merchant(t.description)
            if m:
                merchants.add(m)

        return {"merchants": sorted(list(merchants))}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# SUMMARY ENDPOINTS
# =============================================================================

@app.get("/summary")
@cached(ttl=1800)  # Cache for 30 minutes
async def get_summary(request: Request, session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get monthly summary for a session or client
    
    Returns monthly totals and category breakdowns
    """
    if not session_id and not client_id:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
    
    if session_id:
        ensure_session_access(session_id, current_user, db)
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    summary = calculate_monthly_summary(session_id, db, client_id)
    return summary


@app.get("/category-summary")
@cached(ttl=1800)  # Cache for 30 minutes
async def get_category_totals(request: Request, session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get total amounts by category for a session or client
    """
    if not session_id and not client_id:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
    
    if session_id:
        ensure_session_access(session_id, current_user, db)
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    categories = get_category_summary(session_id, db, client_id)
    return {"categories": categories}


@app.get("/categories/{category}/transactions")
def get_transactions_for_category(category: str, session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return transactions for a specific category in this session"""
    try:
        ensure_session_access(session_id, current_user, db)
        from services.summary import get_transactions_by_category
        txns = get_transactions_by_category(session_id, category, db)
        return {"transactions": txns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/category-monthly")
def get_category_monthly(session_id: str, category: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return month-to-month totals for a specific category"""
    try:
        ensure_session_access(session_id, current_user, db)
        summary = calculate_monthly_summary(session_id, db)
        months = summary.get("months", [])
        # Build time series for the category
        series = []
        for m in months:
            series.append({"month": m["month"], "amount": m.get("categories", {}).get(category, 0.0)})

        return {"category": category, "series": series}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reconciliation")
def get_reconciliations(session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return list of reconciliations for session or client"""
    try:
        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            # Get reconciliations directly for this client
            recs = db.query(Reconciliation).filter(Reconciliation.client_id == client_id).all()
        elif session_id:
            ensure_session_access(session_id, current_user, db)
            recs = db.query(Reconciliation).filter(Reconciliation.session_id == session_id).all()
        else:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        return {
            "reconciliations": [
                {
                    "month": r.month,
                    "opening_balance": r.opening_balance,
                    "closing_balance": r.closing_balance
                }
                for r in recs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reconciliation")
def set_reconciliation(request: ReconciliationRequest, session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create or update a reconciliation record for session+month or client+month"""
    try:
        month = request.month
        if not month or len(month) != 7:
            raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")
        
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        # Query based on client_id or session_id
        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            rec = db.query(Reconciliation).filter(
                Reconciliation.client_id == client_id,
                Reconciliation.month == month
            ).first()
            if not rec:
                rec = Reconciliation(client_id=client_id, month=month)
                db.add(rec)
        else:
            ensure_session_access(session_id, current_user, db)
            rec = db.query(Reconciliation).filter(
                Reconciliation.session_id == session_id,
                Reconciliation.month == month
            ).first()
            if not rec:
                rec = Reconciliation(session_id=session_id, month=month)
                db.add(rec)

        rec.opening_balance = request.opening_balance
        rec.closing_balance = request.closing_balance
        db.commit()

        return {"success": True, "month": month, "opening_balance": rec.opening_balance, "closing_balance": rec.closing_balance}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reconciliation/overview")
def get_reconciliation_overview(session_id: Optional[str] = None, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compute overall system balances and return difference vs bank closing balance (if provided)."""
    try:
        # Validate and convert parameters
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        if client_id:
            try:
                client_id = int(client_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid client_id: {client_id}")
        
        # Sum all transactions for session or client
        if session_id:
            ensure_session_access(session_id, current_user, db)
            logger.info(f"[reconciliation/overview] Fetching overview for session_id={session_id}")
            total_txn = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.session_id == session_id).scalar()
            # Find stored overall reconciliation record (one per session)
            overall = db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).first()
            identifier = session_id
        else:  # client_id
            logger.info(f"[reconciliation/overview] Fetching overview for client_id={client_id}")
            # Check if client exists
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                logger.warning(f"[reconciliation/overview] Client not found: client_id={client_id}")
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
            
            total_txn = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.client_id == client_id).scalar()
            # Find stored overall reconciliation record for client
            overall = db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).first()
            identifier = f"client_{client_id}"

        system_opening = overall.system_opening_balance if overall and overall.system_opening_balance is not None else 0.0
        bank_closing = overall.bank_closing_balance if overall and overall.bank_closing_balance is not None else None

        system_closing = system_opening + (total_txn or 0.0)
        difference = None if bank_closing is None else (bank_closing - system_closing)

        logger.info(f"[reconciliation/overview] Success: {identifier} - opening={system_opening}, txns={total_txn}, closing={system_closing}")
        return {
            "identifier": identifier,
            "system_opening_balance": system_opening,
            "transactions_total": total_txn,
            "system_closing_balance": system_closing,
            "bank_closing_balance": bank_closing,
            "difference": difference
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[reconciliation/overview] Error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch reconciliation overview: {str(e)}")


@app.post("/session/lock")
def lock_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a session as locked/finalized. Locked sessions cannot be modified."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not ss:
            ss = SessionState(session_id=session_id, locked=1)
            db.add(ss)
        else:
            ss.locked = 1
        db.commit()
        return {"session_id": session_id, "locked": True, "message": "Session locked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/session/unlock")
def unlock_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Unlock a previously locked session (for admin or corrections)."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not ss:
            return {"session_id": session_id, "locked": False, "message": "Session not found; treated as unlocked"}
        ss.locked = 0
        db.commit()
        return {"session_id": session_id, "locked": False, "message": "Session unlocked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/session/status")
def session_status(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return lock status for a session."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        locked = bool(ss.locked) if ss else False
        return {"session_id": session_id, "locked": locked}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions")
async def list_sessions(request: Request, client_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a list of previous upload sessions with basic metadata.

    Query parameters:
        - client_id (optional): Filter sessions by client. If not provided, returns all sessions.

    Response:
      {
        "sessions": [
           { "session_id": "...", "transaction_count": 12, "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "locked": false }
        ]
      }
    """
    try:
        # Build base query
        query = db.query(
            Transaction.session_id,
            func.count(Transaction.id).label('txn_count'),
            func.min(Transaction.date).label('date_from'),
            func.max(Transaction.date).label('date_to')
        )
        
        # Filter by client_id if provided
        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            query = query.filter(Transaction.client_id == client_id)
        else:
            client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
            if not client_ids:
                return {"sessions": []}
            query = query.filter(Transaction.client_id.in_(client_ids))
        
        rows = query.group_by(Transaction.session_id).all()

        sessions = []
        for r in rows:
            sid = r[0]
            txn_count = int(r[1] or 0)
            date_from = r[2].isoformat() if r[2] else None
            date_to = r[3].isoformat() if r[3] else None

            ss = db.query(SessionState).filter(SessionState.session_id == sid).first()
            locked = bool(ss.locked) if ss else False
            
            # Get friendly name from SessionState, or generate from dates
            if ss and ss.friendly_name:
                friendly_name = ss.friendly_name
            elif date_from and date_to:
                # Generate friendly name: "Statement Nov 18 - Jan 20, 2026"
                from datetime import datetime
                from_date = datetime.fromisoformat(date_from)
                to_date = datetime.fromisoformat(date_to)
                friendly_name = f"Statement {from_date.strftime('%b %d')} - {to_date.strftime('%b %d, %Y')}"
            else:
                friendly_name = sid

            sessions.append({
                "session_id": sid,
                "friendly_name": friendly_name,
                "transaction_count": txn_count,
                "date_from": date_from,
                "date_to": date_to,
                "locked": locked
            })

        # sort by date_to desc (most recent first)
        sessions.sort(key=lambda s: s.get('date_to') or '', reverse=True)

        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a session and all associated data (transactions, invoices, etc.)
    
    Args:
        session_id: The session to delete
    
    Response:
        {
            "success": true,
            "message": "Session deleted successfully",
            "deleted_counts": {
                "transactions": 42,
                "invoices": 5,
                "merchants": 10
            }
        }
    """
    try:
        ensure_session_access(session_id, current_user, db)
        # Count what we're deleting
        txn_count = db.query(Transaction).filter(Transaction.session_id == session_id).count()
        inv_count = db.query(Invoice).filter(Invoice.session_id == session_id).count()
        merchant_count = db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).count()
        
        # Get invoice IDs for this session to delete their matches
        invoice_ids = db.query(Invoice.id).filter(Invoice.session_id == session_id).all()
        invoice_ids = [inv_id[0] for inv_id in invoice_ids]
        
        # Delete all associated data
        db.query(Transaction).filter(Transaction.session_id == session_id).delete()
        db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).delete()
        
        # Delete invoice matches by invoice IDs
        if invoice_ids:
            db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id.in_(invoice_ids)).delete()
        
        db.query(Invoice).filter(Invoice.session_id == session_id).delete()
        db.query(Reconciliation).filter(Reconciliation.session_id == session_id).delete()
        db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).delete()
        db.query(SessionState).filter(SessionState.session_id == session_id).delete()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Session deleted successfully",
            "deleted_counts": {
                "transactions": txn_count,
                "invoices": inv_count,
                "merchants": merchant_count
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/bulk-delete")
def bulk_delete_sessions(request: BulkDeleteSessionsRequest, db: Session = Depends(get_db)):
    """Delete multiple sessions and all their associated data
    
    Args:
        request: Contains list of session IDs to delete
    
    Response:
        {
            "success": true,
            "message": "3 sessions deleted successfully",
            "deleted_sessions": 3,
            "total_transactions": 150,
            "total_invoices": 25
        }
    """
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="No sessions specified")
    
    try:
        total_txns = 0
        total_invs = 0
        total_merchants = 0
        deleted_count = 0
        
        for session_id in request.session_ids:
            # Count what we're deleting
            txn_count = db.query(Transaction).filter(Transaction.session_id == session_id).count()
            inv_count = db.query(Invoice).filter(Invoice.session_id == session_id).count()
            merchant_count = db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).count()
            
            if txn_count == 0 and inv_count == 0:
                continue  # Skip if no data for this session
            
            # Get invoice IDs for this session to delete their matches
            invoice_ids = db.query(Invoice.id).filter(Invoice.session_id == session_id).all()
            invoice_ids = [inv_id[0] for inv_id in invoice_ids]
            
            # Delete all associated data
            db.query(Transaction).filter(Transaction.session_id == session_id).delete()
            db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).delete()
            
            # Delete invoice matches by invoice IDs
            if invoice_ids:
                db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id.in_(invoice_ids)).delete()
            
            db.query(Invoice).filter(Invoice.session_id == session_id).delete()
            db.query(Reconciliation).filter(Reconciliation.session_id == session_id).delete()
            db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).delete()
            db.query(SessionState).filter(SessionState.session_id == session_id).delete()
            
            total_txns += txn_count
            total_invs += inv_count
            total_merchants += merchant_count
            deleted_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"{deleted_count} session(s) deleted successfully",
            "deleted_sessions": deleted_count,
            "total_transactions": total_txns,
            "total_invoices": total_invs
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# =====================
# Rules CRUD + preview
# =====================


@app.get("/rules")
def list_rules(client_id: Optional[int] = None, db: Session = Depends(get_db)):
    try:
        if client_id:
            rows = db.query(Rule).filter(Rule.client_id == client_id).order_by(Rule.priority.asc()).all()
        else:
            rows = db.query(Rule).order_by(Rule.priority.asc()).all()
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "name": r.name,
                "enabled": bool(r.enabled),
                "priority": r.priority,
                "conditions": json.loads(r.conditions),
                "action": json.loads(r.action),
                "auto_apply": bool(r.auto_apply)
            })
        return {"rules": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rules")
def create_rule(request: dict, client_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Create a new rule. Body: { name, enabled, priority, conditions, action, auto_apply }"""
    try:
        name = request.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        conditions = request.get("conditions")
        action = request.get("action")
        if conditions is None or action is None:
            raise HTTPException(status_code=400, detail="conditions and action are required")

        r = Rule(
            client_id=client_id,
            name=name,
            enabled=1 if request.get("enabled", True) else 0,
            priority=int(request.get("priority", 100)),
            conditions=json.dumps(conditions),
            action=json.dumps(action),
            auto_apply=1 if request.get("auto_apply", False) else 0
        )
        db.add(r)
        db.commit()
        return {"success": True, "id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/rules/{rule_id}")
def update_rule(rule_id: int, request: dict, db: Session = Depends(get_db)):
    try:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        if "name" in request:
            r.name = request.get("name")
        if "enabled" in request:
            r.enabled = 1 if request.get("enabled") else 0
        if "priority" in request:
            r.priority = int(request.get("priority"))
        if "conditions" in request:
            r.conditions = json.dumps(request.get("conditions"))
        if "action" in request:
            r.action = json.dumps(request.get("action"))
        if "auto_apply" in request:
            r.auto_apply = 1 if request.get("auto_apply") else 0
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    try:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        db.delete(r)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _txn_matches_conditions(txn: dict, conds: dict) -> bool:
    match_type = conds.get('match_type', 'all')
    clauses = conds.get('conditions', [])

    def eval_clause(cl):
        f = cl.get('field')
        op = cl.get('op')
        val = cl.get('value')
        v = txn.get(f)
        if v is None:
            return False
        try:
            if op == 'contains':
                return str(val).lower() in str(v).lower()
            if op == 'equals':
                return str(v).lower() == str(val).lower()
            if op == 'regex':
                return re.search(val, str(v)) is not None
            if op == 'gt':
                return float(v) > float(val)
            if op == 'lt':
                return float(v) < float(val)
        except Exception:
            return False
        return False

    results = [eval_clause(c) for c in clauses]
    if match_type == 'any':
        return any(results)
    return all(results)


@app.post("/rules/{rule_id}/preview")
def preview_rule(rule_id: int, payload: dict, db: Session = Depends(get_db)):
    """Preview a rule against a session: body { session_id: '...' }"""
    try:
        sid = payload.get('session_id')
        if not sid:
            raise HTTPException(status_code=400, detail="session_id is required")
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        conds = json.loads(r.conditions)
        txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        matches = []
        for t in txns_db:
            td = {"id": t.id, "description": t.description, "amount": t.amount, "date": t.date, "category": t.category}
            if _txn_matches_conditions(td, conds):
                matches.append({"id": t.id, "description": t.description, "amount": t.amount, "category": t.category})
        return {"matches": matches, "count": len(matches)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rules/{rule_id}/apply")
def apply_rule(rule_id: int, payload: dict, session_id: str = None, db: Session = Depends(get_db)):
    """Apply a rule to a session. Query param session_id or payload.session_id required."""
    try:
        sid = session_id or payload.get('session_id')
        if not sid:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == sid).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

        conds = json.loads(r.conditions)
        action = json.loads(r.action)

        txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        matched = []
        original_state = []
        for t in txns_db:
            td = {"id": t.id, "description": t.description, "amount": t.amount, "date": t.date, "category": t.category}
            if _txn_matches_conditions(td, conds):
                matched.append(t.id)
                original_state.append({"id": t.id, "category": t.category, "description": t.description})

        if not matched:
            return {"updated_count": 0, "message": "No matching transactions"}

        # Apply action (support set_category and set_merchant)
        updated_count = 0
        if action.get('type') == 'set_category' and action.get('category'):
            newcat = action.get('category')
            for tid in matched:
                db.query(Transaction).filter(Transaction.id == tid).update({"category": newcat})
                updated_count += 1
            db.commit()

            # record undo action in bulk_categorizer
            try:
                import uuid
                from services.bulk_categorizer import BulkAction
                action_id = str(uuid.uuid4())
                bulk_categorizer.last_action = BulkAction(
                    action_id=action_id,
                    keyword=f"rule:{r.id}",
                    category=newcat,
                    timestamp=datetime.utcnow().isoformat(),
                    matched_transactions=original_state,
                    transaction_ids=[t['id'] for t in original_state]
                )
            except Exception:
                pass

        elif action.get('type') == 'set_merchant' and action.get('merchant'):
            newm = action.get('merchant')
            for tid in matched:
                tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == tid).first()
                if not tm:
                    tm = TransactionMerchant(transaction_id=tid, session_id=sid, merchant=newm)
                    db.add(tm)
                    updated_count += 1
                else:
                    if tm.merchant != newm:
                        tm.merchant = newm
                        updated_count += 1
            db.commit()

        # return updated transactions list
        updated_txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        updated_transactions = [
            {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": t.amount, "category": t.category}
            for t in updated_txns_db
        ]

        return {"updated_count": updated_count, "transactions": updated_transactions, "undo_available": bulk_categorizer.get_last_action_info() is not None, "message": f"Updated {updated_count} transaction(s)"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reconciliation/overview")
def set_reconciliation_overview(request: OverallReconciliationRequest, session_id: Optional[str] = None, client_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Set or update overall opening and bank closing balances for a session or client."""
    try:
        if session_id:
            logger.info(f"[reconciliation/overview POST] Updating overview for session_id={session_id}: opening={request.system_opening_balance}, closing={request.bank_closing_balance}")
            rec = db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).first()
            if not rec:
                rec = OverallReconciliation(session_id=session_id)
                db.add(rec)
            identifier = session_id
        elif client_id:
            logger.info(f"[reconciliation/overview POST] Updating overview for client_id={client_id}: opening={request.system_opening_balance}, closing={request.bank_closing_balance}")
            rec = db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).first()
            if not rec:
                rec = OverallReconciliation(client_id=client_id)
                db.add(rec)
            identifier = f"client_{client_id}"
        else:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if request.system_opening_balance is not None:
            rec.system_opening_balance = request.system_opening_balance
        if request.bank_closing_balance is not None:
            rec.bank_closing_balance = request.bank_closing_balance

        db.commit()
        logger.info(f"[reconciliation/overview POST] Success: {identifier} updated")

        return {"success": True, "message": "Overall reconciliation updated", "identifier": identifier}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[reconciliation/overview POST] Error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to update reconciliation: {str(e)}")


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@app.get("/export/transactions")
def export_transactions(session_id: Optional[str] = None, client_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Export all transactions to Excel
    """
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        output = ExcelExporter.export_transactions(session_id, db, client_id)  # BytesIO
        filename_part = session_id[:8] if session_id else f"client_{client_id}"
        headers = {
            "Content-Disposition": f'attachment; filename="transactions_{filename_part}.xlsx"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/export/summary")
def export_summary(session_id: Optional[str] = None, client_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Export monthly summary to Excel (multi-sheet)
    """
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        summary = calculate_monthly_summary(session_id, db, client_id)
        output = ExcelExporter.export_monthly_summary(summary)  # BytesIO
        filename_part = session_id[:8] if session_id else f"client_{client_id}"
        headers = {
            "Content-Disposition": f'attachment; filename="summary_{filename_part}.xlsx"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/export/category")
def export_category(session_id: str, category: str, db: Session = Depends(get_db)):
    """
    Export a single category workbook with month sections (opening balance + running balances).
    """
    try:
        output = ExcelExporter.export_category_monthly(session_id, category, db)
        headers = {
            "Content-Disposition": f'attachment; filename="category_{category[:16]}_{session_id[:8]}.xlsx"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/export/categories")
def export_all_categories(
    session_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    include_vat: bool = False,
    categories: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export all categories into a single workbook (one sheet per category).
    Supports date range filtering, VAT column inclusion, and category filtering.
    
    Parameters:
    - date_from: Start date in YYYY-MM-DD format (optional)
    - date_to: End date in YYYY-MM-DD format (optional)
    - include_vat: Whether to include VAT columns (default: False)
    - categories: Comma-separated list of category names to include (optional, default: all)
    """
    try:
        import traceback
        print(f"\n{'='*60}")
        print(f"CATEGORY EXPORT REQUEST")
        print(f"{'='*60}")
        print(f"Session: {session_id}")
        print(f"Date range: {date_from} to {date_to}")
        print(f"Include VAT (raw): {include_vat} (type: {type(include_vat).__name__})")
        print(f"Categories filter (raw): {categories}")
        
        # Ensure include_vat is a proper boolean
        if isinstance(include_vat, str):
            include_vat_bool = include_vat.lower() in ('true', '1', 'yes')
        else:
            include_vat_bool = bool(include_vat)
        
        print(f"Include VAT (converted): {include_vat_bool}")
        
        # Parse categories filter if provided
        selected_categories = None
        if categories:
            selected_categories = [c.strip() for c in categories.split(',') if c.strip()]
            print(f"Selected categories: {selected_categories}")
        else:
            print(f"Exporting ALL categories")
        
        print(f"{'='*60}\n")
        
        output = ExcelExporter.export_all_categories_monthly(
            session_id=session_id,
            db=db,
            date_from=date_from,
            date_to=date_to,
            include_vat=include_vat_bool,
            selected_categories=selected_categories
        )
        print("Export completed successfully")
        
        # Generate dynamic filename
        date_suffix = f"{date_from}_to_{date_to}" if date_from and date_to else session_id[:8]
        vat_suffix = "_with_vat" if include_vat_bool else ""
        filename = f"categories{vat_suffix}_{date_suffix}.xlsx"
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        import traceback
        print("Export error:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/export/accountant")
def export_for_accountant(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Export comprehensive report for accountants.
    Includes: Executive Summary, Merchant Analysis, Detailed Transactions
    """
    try:
        ensure_session_access(session_id, current_user, db)
        print(f"Starting accountant export for session: {session_id}")
        output = ExcelExporter.export_for_accountant(session_id, db)
        print("Accountant export completed successfully")
        headers = {
            "Content-Disposition": f'attachment; filename="statement_report_{session_id[:8]}.xlsx"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        import traceback
        print("Accountant export error:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# =============================================================================
# BULK CATEGORIZATION ENDPOINTS
# =============================================================================

@app.post("/bulk-categorise")
def bulk_categorize(
    request: BulkCategorizeRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply a category to all transactions matching a keyword
    
    Args:
        keyword: Search term (case-insensitive, substring match)
        category: Category to apply
        only_uncategorised: If True, only match uncategorised transactions
        session_id: Session ID (query param)
    
    Returns:
        {
            "updated_count": number of transactions updated,
            "transactions": updated transaction list,
            "undo_available": whether undo is possible,
            "message": success message
        }
    """
    try:
        # Load enabled rules (for preview or potential integration) - not applied here unless rule action requested
        # (bulk categorize endpoint remains explicit; applying a rule should be via /rules/{id}/apply)
        pass
        ensure_session_access(session_id, current_user, db)

        # Prevent modifications if session is locked
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        print(f"\n=== BULK CATEGORIZE REQUEST ===")
        print(f"Session ID: {session_id}")
        print(f"User ID: {current_user.id}")
        print(f"Keyword: {request.keyword}")
        print(f"Category: {request.category}")
        print(f"Only uncategorised: {request.only_uncategorised}")
        
        # Get all transactions for this session
        transactions_db = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        print(f"Total transactions found: {len(transactions_db)}")
        
        if not transactions_db:
            raise HTTPException(status_code=404, detail="No transactions found for this session")
        
        # Convert to dict format for bulk categorizer
        transactions = [
            {
                "id": t.id,
                "description": t.description,
                "category": t.category,
                "date": t.date,
                "amount": t.amount
            }
            for t in transactions_db
        ]
        
        # Apply bulk categorization
        updated_count, updated_txns, error_msg = bulk_categorizer.apply_bulk_categorization(
            transactions,
            request.keyword,
            request.category,
            request.only_uncategorised
        )
        
        print(f"Updated count from categorizer: {updated_count}")
        print(f"Error msg: {error_msg}")
        
        if error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Update database with new categories
        if updated_count > 0:
            print(f"Updating {updated_count} transactions in database")
            updated_txn_ids = []
            for txn_dict in updated_txns:
                print(f"  - ID: {txn_dict['id']}, Category: {txn_dict['category']}")
                db.query(Transaction).filter(
                    Transaction.id == txn_dict["id"]
                ).update({"category": txn_dict["category"]})
                updated_txn_ids.append(txn_dict["id"])
            db.commit()
            print("Database commit successful")
            
            # **RECALCULATE VAT FOR ALL UPDATED TRANSACTIONS**
            print(f"Recalculating VAT for {len(updated_txn_ids)} transactions")
            for txn_id in updated_txn_ids:
                vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)
            
            # Learn from this bulk categorization
            try:
                # Use the first updated transaction as representative for learning
                if updated_txns:
                    representative_txn = updated_txns[0]
                    txn_db = db.query(Transaction).filter(Transaction.id == representative_txn["id"]).first()
                    if txn_db:
                        # Get merchant if it exists
                        merchant = None
                        tm = db.query(TransactionMerchant).filter(
                            TransactionMerchant.transaction_id == txn_db.id
                        ).first()
                        if tm:
                            merchant = tm.merchant
                        
                        effective_user_id = str(current_user.id)
                        learned_rules = learning_service.learn_from_categorization(
                            user_id=effective_user_id,
                            session_id=session_id,
                            description=txn_db.description,
                            category=request.category,
                            merchant=merchant,
                            keyword=request.keyword,  # Use the keyword from the request
                            db=db
                        )
                        if learned_rules:
                            print(f"Learned {len(learned_rules)} rules from bulk categorization")
            except Exception as e:
                print(f"Warning: Failed to learn from bulk categorization: {e}")
                # Don't fail the whole operation for learning issues
        else:
            print("No transactions to update")
        
        # Get updated list
        updated_transactions_db = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        updated_transactions = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat
            }
            for t in updated_transactions_db
        ]
        
        # Invalidate cache for this session (bulk update affects all caches)
        if updated_count > 0:
            cache = get_cache()
            cache.invalidate_session(session_id)
        
        return {
            "updated_count": updated_count,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
            "message": f"Updated {updated_count} transaction(s)" if updated_count > 0 else "No matching transactions"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Bulk categorization error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Bulk categorization failed: {str(e)}")


@app.post("/bulk-categorise/undo")
def undo_bulk_categorize(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Undo the last bulk categorization action for this session
    
    Args:
        session_id: Session ID (query param)
    
    Returns:
        {
            "success": whether undo was successful,
            "message": status message,
            "transactions": reverted transaction list,
            "undo_available": whether another undo is possible
        }
    """
    try:
        ensure_session_access(session_id, current_user, db)

        # Get current transactions
        transactions_db = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        transactions = [
            {
                "id": t.id,
                "description": t.description,
                "category": t.category,
                "date": t.date,
                "amount": t.amount
            }
            for t in transactions_db
        ]
        
        # Perform undo
        success, message, reverted_txns = bulk_categorizer.undo_last_action(transactions)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Update database
        if success:
            for txn_dict in reverted_txns:
                db.query(Transaction).filter(
                    Transaction.id == txn_dict["id"]
                ).update({"category": txn_dict["category"]})
            db.commit()
        
        # Get updated list
        updated_transactions_db = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        updated_transactions = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category
            }
            for t in updated_transactions_db
        ]
        
        return {
            "success": success,
            "message": message,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Undo error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Undo failed: {str(e)}")


# =============================================================================
# ASYNC BACKGROUND JOBS ENDPOINTS
# =============================================================================

@app.post("/upload_pdf_async", tags=["Background Jobs"])
async def upload_pdf_async(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None
):
    """
    Upload PDF asynchronously and return task ID for progress tracking.
    Use GET /tasks/{task_id}/status to check progress.
    """
    # Rate limiting
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    
    # Validate PDF upload
    await validate_pdf_upload(file)
    
    try:
        # Read file content
        content = await file.read()
        
        # Convert to base64 for Celery task
        import base64
        content_base64 = base64.b64encode(content).decode('utf-8')
        
        # Submit background task
        from tasks import parse_pdf_async
        task = parse_pdf_async.delay(
            pdf_content_base64=content_base64,
            filename=file.filename,
            user_id=current_user.id,
            client_id=client_id
        )
        
        # Create task status record
        from models import TaskStatus
        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name='parse_pdf_async',
            status='PENDING',
            progress_percent=0,
            progress_message='Task submitted'
        )
        db.add(task_status)
        db.commit()
        
        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "PDF parsing started. Use GET /tasks/{task_id}/status to check progress."
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@app.post("/bulk_categorize_async", tags=["Background Jobs"])
async def bulk_categorize_async_endpoint(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rules: Optional[List[dict]] = None
):
    """
    Apply bulk categorization asynchronously.
    Returns task ID for progress tracking.
    """
    try:
        # Verify session exists and belongs to user
        session_state = db.query(SessionState).filter(
            SessionState.session_id == session_id,
            SessionState.user_id == current_user.id
        ).first()
        
        if not session_state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Submit background task
        from tasks import bulk_categorize_async
        task = bulk_categorize_async.delay(
            session_id=session_id,
            user_id=current_user.id,
            rules=rules
        )
        
        # Create task status record
        from models import TaskStatus
        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name='bulk_categorize_async',
            status='PENDING',
            progress_percent=0,
            progress_message='Task submitted'
        )
        db.add(task_status)
        db.commit()
        
        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Bulk categorization started. Use GET /tasks/{task_id}/status to check progress."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@app.post("/reports/generate_async", tags=["Background Jobs"])
async def generate_report_async_endpoint(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_type: str = 'excel',
    include_vat: bool = False
):
    """
    Generate report asynchronously in background.
    Returns task ID. Once complete, result contains file_key for download.
    """
    try:
        # Verify session exists and belongs to user
        session_state = db.query(SessionState).filter(
            SessionState.session_id == session_id,
            SessionState.user_id == current_user.id
        ).first()
        
        if not session_state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Submit background task
        from tasks import generate_report_async
        task = generate_report_async.delay(
            session_id=session_id,
            user_id=current_user.id,
            report_type=report_type,
            include_vat=include_vat
        )
        
        # Create task status record
        from models import TaskStatus
        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name='generate_report_async',
            status='PENDING',
            progress_percent=0,
            progress_message='Task submitted'
        )
        db.add(task_status)
        db.commit()
        
        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Report generation started. Use GET /tasks/{task_id}/status to check progress."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@app.get("/tasks/{task_id}/status", tags=["Background Jobs"])
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get status and progress of a background task.
    """
    from models import TaskStatus
    
    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id
    ).first()
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_status.task_id,
        "task_name": task_status.task_name,
        "status": task_status.status,
        "progress_percent": task_status.progress_percent,
        "progress_message": task_status.progress_message,
        "created_at": task_status.created_at.isoformat(),
        "updated_at": task_status.updated_at.isoformat()
    }


@app.get("/tasks/{task_id}/result", tags=["Background Jobs"])
async def get_task_result(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get result of a completed background task.
    """
    from models import TaskStatus
    
    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id
    ).first()
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_status.status != 'SUCCESS':
        return {
            "task_id": task_id,
            "status": task_status.status,
            "message": "Task not completed yet" if task_status.status in ['PENDING', 'PROCESSING'] 
                      else f"Task failed: {task_status.error_message}"
        }
    
    result_data = json.loads(task_status.result) if task_status.result else {}
    
    return {
        "task_id": task_id,
        "status": "SUCCESS",
        "result": result_data
    }


@app.delete("/tasks/{task_id}", tags=["Background Jobs"])
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running task or delete task result.
    """
    from models import TaskStatus
    from celery.result import AsyncResult
    
    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id
    ).first()
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Try to revoke the task if it's still running
    if task_status.status in ['PENDING', 'PROCESSING']:
        celery_task = AsyncResult(task_id)
        celery_task.revoke(terminate=True)
        task_status.status = 'CANCELLED'
        task_status.error_message = 'Cancelled by user'
        db.commit()
        return {"message": "Task cancelled"}
    else:
        # Delete the task record
        db.delete(task_status)
        db.commit()
        return {"message": "Task result deleted"}




# =============================================================================
# CACHE MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/cache/stats", tags=["Cache"])
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """
    Get cache statistics including hit rate, size, and key count.
    Requires authentication.
    """
    cache = get_cache()
    return cache.get_stats()


@app.get("/cache/health", tags=["Cache"])
async def cache_health_check():
    """
    Check cache health status (Redis connection).
    Public endpoint for health monitoring.
    """
    cache = get_cache()
    return cache.health_check()


@app.delete("/cache/flush", tags=["Cache"])
async def flush_cache(current_user: User = Depends(get_current_user)):
    """
    Flush all cache entries.
    Requires authentication. Use with caution in production.
    """
    # Only allow superusers to flush all cache in production
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can flush cache")
    
    cache = get_cache()
    success = cache.flush_all()
    
    if success:
        return {"message": "Cache flushed successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to flush cache")


@app.delete("/cache/session/{session_id}", tags=["Cache"])
async def invalidate_session_cache(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invalidate all cache entries for a specific session.
    Useful when you want to force refresh after manual data changes.
    """
    # Verify user has access to this session
    ensure_session_access(session_id, current_user, db)
    
    cache = get_cache()
    deleted_count = cache.invalidate_session(session_id)
    
    return {
        "message": f"Invalidated cache for session {session_id}",
        "deleted_keys": deleted_count
    }


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/")
def root():
    """API information"""
    return {
        "name": "Bank Statement Analyzer",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload and process bank statement CSV",
            "GET /transactions": "Get all transactions",
            "GET /summary": "Get monthly summary",
            "GET /category-summary": "Get category totals",
            "GET /export/transactions": "Export transactions to Excel",
            "GET /export/summary": "Export monthly summary to Excel",
            "POST /bulk-categorise": "Apply category to matching transactions",
            "POST /bulk-categorise/undo": "Undo last bulk categorization",
            "POST /upload_pdf_async": "Upload PDF for async processing",
            "POST /bulk_categorize_async": "Bulk categorize asynchronously",
            "POST /reports/generate_async": "Generate report in background",
            "GET /tasks/{task_id}/status": "Get task status and progress",
            "GET /tasks/{task_id}/result": "Get completed task result"
        }
    }


if __name__ == "__main__":
    import uvicorn
    # Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)

