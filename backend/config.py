"""
Application configuration using environment variables with validation
Centralizes all configuration and validates on startup
"""

import os
import secrets
import logging
from typing import List

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Application configuration with environment variable validation"""
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # Security - JWT Authentication
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days default
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./statement_analyzer.db")
    
    # CORS
    ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
    ALLOWED_ORIGINS: List[str] = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]
    
    # API Server
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENVIRONMENT == "production" else "DEBUG")
    
    # File Upload Limits
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # Rate Limiting (requests per time window)
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() in ("true", "1", "yes")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    UPLOAD_RATE_LIMIT_PER_MINUTE = int(os.getenv("UPLOAD_RATE_LIMIT_PER_MINUTE", "10"))
    UPLOAD_RATE_LIMIT_PER_HOUR = int(os.getenv("UPLOAD_RATE_LIMIT_PER_HOUR", "100"))
    READ_RATE_LIMIT_PER_MINUTE = int(os.getenv("READ_RATE_LIMIT_PER_MINUTE", "120"))
    READ_RATE_LIMIT_PER_HOUR = int(os.getenv("READ_RATE_LIMIT_PER_HOUR", "2000"))
    
    # Cloud File Storage
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # Options: local, s3, azure, gcs
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", os.path.join(os.path.dirname(__file__), 'uploads'))
    
    # AWS S3 Settings
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    
    # Azure Blob Storage Settings
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "")
    
    # Google Cloud Storage Settings
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
    GCS_CREDENTIALS_PATH = os.getenv("GCS_CREDENTIALS_PATH", "")
    GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID", "")
    
    # File Access Settings
    SIGNED_URL_EXPIRATION_SECONDS = int(os.getenv("SIGNED_URL_EXPIRATION_SECONDS", "3600"))  # 1 hour default
    
    # Redis Cache Configuration
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
    REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/1")  # Separate DB from Celery (db=0)
    CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "300"))  # 5 minutes
    CACHE_TTL_TRANSACTIONS = int(os.getenv("CACHE_TTL_TRANSACTIONS", "300"))  # 5 minutes
    CACHE_TTL_SUMMARIES = int(os.getenv("CACHE_TTL_SUMMARIES", "1800"))  # 30 minutes
    CACHE_TTL_RULES = int(os.getenv("CACHE_TTL_RULES", "3600"))  # 1 hour
    CACHE_TTL_SESSIONS = int(os.getenv("CACHE_TTL_SESSIONS", "600"))  # 10 minutes
    
    # Sentry Error Monitoring Configuration
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")  # Sentry Data Source Name (from sentry.io project settings)
    SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "true").lower() in ("true", "1", "yes") and bool(SENTRY_DSN)
    SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", ENVIRONMENT)  # development, staging, production
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))  # 10% of transactions
    SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))  # 10% of transactions
    SENTRY_SEND_DEFAULT_PII = os.getenv("SENTRY_SEND_DEFAULT_PII", "false").lower() in ("true", "1", "yes")
    
    @classmethod
    def validate(cls):
        """
        Validate configuration and fail fast if critical settings are missing or insecure
        """
        errors = []
        warnings = []
        
        # Validate SECRET_KEY
        if not cls.SECRET_KEY:
            if cls.ENVIRONMENT == "production":
                errors.append("SECRET_KEY environment variable must be set in production")
            else:
                # Generate a secure key for development
                cls.SECRET_KEY = secrets.token_urlsafe(32)
                warnings.append(f"SECRET_KEY not set - generated temporary key for development: {cls.SECRET_KEY[:20]}...")
        elif cls.SECRET_KEY in [
            "your-secret-key-change-this-in-production",
            "your-secret-key-here-generate-with-openssl-rand-hex-32",
            "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",  # Old default
            "change-me",
            "secret",
        ]:
            if cls.ENVIRONMENT == "production":
                errors.append("SECRET_KEY is using a default/weak value - generate a strong key with: openssl rand -hex 32")
            else:
                warnings.append("SECRET_KEY is using a weak default - should be changed for security")
        elif len(cls.SECRET_KEY) < 32:
            if cls.ENVIRONMENT == "production":
                errors.append(f"SECRET_KEY is too short ({len(cls.SECRET_KEY)} chars) - should be at least 32 characters")
            else:
                warnings.append(f"SECRET_KEY is short ({len(cls.SECRET_KEY)} chars) - recommended: at least 32 characters")
        
        # Validate DATABASE_URL
        if "EXAMPLE" in cls.DATABASE_URL.upper():
            errors.append("DATABASE_URL contains 'EXAMPLE' - update with actual database path")
        
        # Validate CORS origins
        if cls.ENVIRONMENT == "production" and "localhost" in cls.ALLOWED_ORIGINS_STR.lower():
            warnings.append("ALLOWED_ORIGINS includes localhost in production - ensure this is intentional")
        
        # Validate Storage Backend
        valid_backends = ["local", "s3", "azure", "gcs"]
        if cls.STORAGE_BACKEND not in valid_backends:
            errors.append(f"STORAGE_BACKEND must be one of {valid_backends}, got: {cls.STORAGE_BACKEND}")
        
        # Validate cloud storage credentials if not using local storage
        if cls.STORAGE_BACKEND == "s3":
            if not cls.S3_BUCKET_NAME:
                errors.append("S3_BUCKET_NAME must be set when using S3 storage")
            if cls.ENVIRONMENT == "production" and (not cls.S3_ACCESS_KEY or not cls.S3_SECRET_KEY):
                warnings.append("S3_ACCESS_KEY and S3_SECRET_KEY not set - will attempt to use IAM role credentials")
        elif cls.STORAGE_BACKEND == "azure":
            if not cls.AZURE_STORAGE_CONNECTION_STRING or not cls.AZURE_CONTAINER_NAME:
                errors.append("AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME must be set when using Azure storage")
        elif cls.STORAGE_BACKEND == "gcs":
            if not cls.GCS_BUCKET_NAME:
                errors.append("GCS_BUCKET_NAME must be set when using GCS storage")
            if not cls.GCS_CREDENTIALS_PATH and not cls.GCS_PROJECT_ID:
                warnings.append("GCS_CREDENTIALS_PATH not set - will attempt to use Application Default Credentials")
        elif cls.STORAGE_BACKEND == "local":
            if cls.ENVIRONMENT == "production":
                warnings.append("Using local file storage in production - consider using cloud storage (S3/Azure/GCS)")
        
        # Log configuration status
        logger = logging.getLogger(__name__)
        
        if errors:
            for error in errors:
                logger.error(f"❌ Configuration Error: {error}")
            raise ValueError(f"Configuration validation failed with {len(errors)} error(s). See logs above.")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️  Configuration Warning: {warning}")
        
        # Log successful validation
        logger.info(f"✅ Configuration validated successfully")
        logger.info(f"   Environment: {cls.ENVIRONMENT}")
        logger.info(f"   Debug: {cls.DEBUG}")
        logger.info(f"   Database: {cls.DATABASE_URL}")
        logger.info(f"   CORS Origins: {len(cls.ALLOWED_ORIGINS)} origin(s)")
        logger.info(f"   Log Level: {cls.LOG_LEVEL}")
        logger.info(f"   Max Upload Size: {cls.MAX_UPLOAD_SIZE_MB}MB")
        logger.info(f"   Storage Backend: {cls.STORAGE_BACKEND}")
    
    @classmethod
    def configure_logging(cls):
        """Configure application logging based on environment"""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# Configure logging first
Config.configure_logging()

# Validate configuration on import
Config.validate()


# Convenience exports for backward compatibility
SECRET_KEY = Config.SECRET_KEY
ALGORITHM = Config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = Config.ACCESS_TOKEN_EXPIRE_MINUTES
DATABASE_URL = Config.DATABASE_URL
ALLOWED_ORIGINS = Config.ALLOWED_ORIGINS
DEBUG = Config.DEBUG
ENVIRONMENT = Config.ENVIRONMENT

# Legacy pydantic-style settings object for compatibility
class settings:
    """Legacy compatibility wrapper"""
    SECRET_KEY = Config.SECRET_KEY
    ALGORITHM = Config.ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = Config.ACCESS_TOKEN_EXPIRE_MINUTES
    DATABASE_URL = Config.DATABASE_URL
    ALLOWED_ORIGINS = Config.ALLOWED_ORIGINS_STR
    ENVIRONMENT = Config.ENVIRONMENT
    
    @property
    def origins_list(self) -> List[str]:
        return Config.ALLOWED_ORIGINS
