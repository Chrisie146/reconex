"""
Input validation utilities for file uploads and request data
Provides security checks and size limits
"""

# Try to import python-magic, but make it optional
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    import logging
    logging.getLogger(__name__).warning(
        "python-magic not available - file type validation will use extension-based checks only. "
        "Install python-magic for stronger validation: pip install python-magic python-magic-bin"
    )

from fastapi import UploadFile, HTTPException
from typing import List, Optional
import logging

from config import Config

logger = logging.getLogger(__name__)


# Allowed MIME types for different file categories
ALLOWED_PDF_TYPES = {
    "application/pdf",
    "application/x-pdf",
}

ALLOWED_CSV_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",  # Sometimes CSVs are detected as this
}

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
}

ALL_ALLOWED_TYPES = ALLOWED_PDF_TYPES | ALLOWED_CSV_TYPES | ALLOWED_IMAGE_TYPES


async def validate_file_upload(
    file: UploadFile,
    allowed_types: Optional[List[str]] = None,
    max_size_bytes: Optional[int] = None,
    require_extension: Optional[List[str]] = None
) -> None:
    """
    Validate uploaded file for type, size, and basic security checks
    
    Args:
        file: FastAPI UploadFile object
        allowed_types: List of allowed MIME types. If None, allows PDF, CSV, images
        max_size_bytes: Maximum file size in bytes. If None, uses Config.MAX_UPLOAD_SIZE_BYTES
        require_extension: List of required file extensions (e.g., ['.pdf', '.csv'])
    
    Raises:
        HTTPException: If validation fails
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="File has no filename")
    
    # Use default max size from config if not specified
    if max_size_bytes is None:
        max_size_bytes = Config.MAX_UPLOAD_SIZE_BYTES
    
    # Use default allowed types if not specified
    if allowed_types is None:
        allowed_types = list(ALL_ALLOWED_TYPES)
    
    # Check file extension if required
    if require_extension:
        file_lower = file.filename.lower()
        if not any(file_lower.endswith(ext.lower()) for ext in require_extension):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed extensions: {', '.join(require_extension)}"
            )
    
    # Read file content for validation (read in chunks to avoid memory issues)
    content = await file.read()
    file_size = len(content)
    
    # Reset file pointer so it can be read again
    await file.seek(0)
    
    # Check file is not empty
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    # Check file size
    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_mb:.1f}MB, your file: {actual_mb:.1f}MB"
        )
    
    # Validate MIME type using magic bytes (more secure than trusting file extension)
    mime_type = None
    if HAS_MAGIC:
        try:
            # Try to detect MIME type from content
            mime_type = magic.from_buffer(content[:2048], mime=True)  # Check first 2KB
            logger.info(f"MIME type detected: {file.filename} -> {mime_type}")
            
            if mime_type not in allowed_types:
                logger.warning(f"MIME type mismatch for {file.filename}: got '{mime_type}', allowed {allowed_types}")
                # Check by extension as fallback before rejecting
                if require_extension:
                    file_lower = file.filename.lower()
                    if any(file_lower.endswith(ext.lower()) for ext in require_extension):
                        # Extension is correct, warn but allow
                        logger.info(f"MIME type mismatch but extension valid, allowing: {file.filename}")
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid file type '{mime_type}'. Allowed types: {', '.join(sorted(set([t.split('/')[-1] for t in allowed_types])))}"
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type '{mime_type}'. Expected one of: {', '.join(allowed_types)}"
                    )
            
            logger.info(f"File validation passed: {file.filename} ({file_size} bytes, {mime_type})")
            
        except HTTPException:
            raise
        except Exception as e:
            # If magic library fails completely, fall back to extension check
            logger.warning(f"MIME type detection error for {file.filename}: {e}. Falling back to extension check.")
            
            # Check by extension only
            if require_extension:
                file_lower = file.filename.lower()
                if not any(file_lower.endswith(ext.lower()) for ext in require_extension):
                    raise HTTPException(
                        status_code=400,
                        detail=f"File extension check failed. Must be: {', '.join(require_extension)}"
                    )
            logger.info(f"File validated by extension: {file.filename} ({file_size} bytes)")
    else:
        # Magic not available - use extension-only validation
        logger.debug(f"File validation (extension-only, python-magic unavailable): {file.filename} ({file_size} bytes)")
        if require_extension:
            file_lower = file.filename.lower()
            if not any(file_lower.endswith(ext.lower()) for ext in require_extension):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file extension. Allowed: {', '.join(require_extension)}"
                )


async def validate_pdf_upload(file: UploadFile) -> None:
    """Validate PDF file upload"""
    await validate_file_upload(
        file,
        allowed_types=list(ALLOWED_PDF_TYPES),
        require_extension=['.pdf']
    )


async def validate_csv_upload(file: UploadFile) -> None:
    """Validate CSV file upload"""
    await validate_file_upload(
        file,
        allowed_types=list(ALLOWED_CSV_TYPES),
        require_extension=['.csv', '.txt']
    )


async def validate_image_upload(file: UploadFile) -> None:
    """Validate image file upload"""
    await validate_file_upload(
        file,
        allowed_types=list(ALLOWED_IMAGE_TYPES),
        require_extension=['.jpg', '.jpeg', '.png', '.tiff', '.tif']
    )


def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: int = 1000) -> None:
    """
    Validate string field length
    
    Args:
        value: String value to validate
        field_name: Name of the field (for error messages)
        min_length: Minimum allowed length
        max_length: Maximum allowed length
    
    Raises:
        HTTPException: If validation fails
    """
    if value is None:
        if min_length > 0:
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        return
    
    length = len(value)
    
    if length < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be at least {min_length} characters (got {length})"
        )
    
    if length > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not exceed {max_length} characters (got {length})"
        )


def validate_numeric_range(value: float, field_name: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> None:
    """
    Validate numeric value is within range
    
    Args:
        value: Numeric value to validate
        field_name: Name of the field (for error messages)
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
    
    Raises:
        HTTPException: If validation fails
    """
    if min_value is not None and value < min_value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be at least {min_value} (got {value})"
        )
    
    if max_value is not None and value > max_value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not exceed {max_value} (got {value})"
        )
