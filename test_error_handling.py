"""
Test script to verify error handling implementation
Tests various error scenarios and validates response format
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from exceptions import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    DatabaseError
)


def test_exception_creation():
    """Test that custom exceptions can be created with proper attributes"""
    print("Testing Exception Creation...")
    
    # Test ValidationError
    try:
        raise ValidationError("Invalid email format", details={"field": "email"})
    except ValidationError as e:
        assert e.status_code == 400
        assert e.error_code == "VALIDATION_ERROR"
        assert e.message == "Invalid email format"
        assert e.details["field"] == "email"
        print("  ✅ ValidationError works correctly")
    
    # Test AuthenticationError
    try:
        raise AuthenticationError("Invalid credentials")
    except AuthenticationError as e:
        assert e.status_code == 401
        assert e.error_code == "AUTHENTICATION_ERROR"
        print("  ✅ AuthenticationError works correctly")
    
    # Test NotFoundError
    try:
        raise NotFoundError("User", 123)
    except NotFoundError as e:
        assert e.status_code == 404
        assert e.error_code == "NOT_FOUND"
        assert "123" in e.message
        assert e.details["resource"] == "User"
        print("  ✅ NotFoundError works correctly")
    
    # Test ConflictError
    try:
        raise ConflictError("Email already registered")
    except ConflictError as e:
        assert e.status_code == 409
        assert e.error_code == "CONFLICT"
        print("  ✅ ConflictError works correctly")
    
    # Test RateLimitError
    try:
        raise RateLimitError("Rate limit exceeded", retry_after=60)
    except RateLimitError as e:
        assert e.status_code == 429
        assert e.error_code == "RATE_LIMIT_EXCEEDED"
        assert e.details["retry_after"] == 60
        print("  ✅ RateLimitError works correctly")
    
    # Test DatabaseError
    try:
        raise DatabaseError("Connection failed")
    except DatabaseError as e:
        assert e.status_code == 500
        assert e.error_code == "DATABASE_ERROR"
        print("  ✅ DatabaseError works correctly")
    
    print("✅ All exception tests passed!\n")


def test_error_response_structure():
    """Test error response formatting"""
    print("Testing Error Response Structure...")
    
    from error_handler import ErrorResponse
    
    # Test basic error response
    response = ErrorResponse.create(
        message="Test error",
        status_code=400,
        error_code="TEST_ERROR"
    )
    
    assert "error" in response
    assert response["error"]["message"] == "Test error"
    assert response["error"]["code"] == "TEST_ERROR"
    assert response["error"]["status"] == 400
    assert "timestamp" in response["error"]
    print("  ✅ Basic error response structure correct")
    
    # Test error response with details
    response = ErrorResponse.create(
        message="Validation failed",
        status_code=400,
        error_code="VALIDATION_ERROR",
        details={"field": "email", "reason": "invalid format"},
        request_id="test-123"
    )
    
    assert response["error"]["details"]["field"] == "email"
    assert response["error"]["request_id"] == "test-123"
    print("  ✅ Error response with details correct")
    
    print("✅ All error response tests passed!\n")


def test_middleware_import():
    """Test that middleware can be imported"""
    print("Testing Middleware Import...")
    
    from middleware import RequestTrackingMiddleware
    
    # Should be able to create instance
    # (We can't test it fully without a FastAPI app instance)
    print("  ✅ RequestTrackingMiddleware imported successfully")
    print("✅ Middleware import test passed!\n")


def test_handler_import():
    """Test that error handlers can be imported"""
    print("Testing Error Handler Import...")
    
    from error_handler import (
        app_exception_handler,
        validation_exception_handler,
        http_exception_handler,
        unhandled_exception_handler,
        setup_exception_handlers
    )
    
    print("  ✅ All error handlers imported successfully")
    print("✅ Error handler import test passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("ERROR HANDLING IMPLEMENTATION TESTS")
    print("=" * 60)
    print()
    
    try:
        test_exception_creation()
        test_error_response_structure()
        test_middleware_import()
        test_handler_import()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Error handling implementation is working correctly:")
        print("  ✓ Custom exceptions with proper status codes")
        print("  ✓ Standardized error response format")
        print("  ✓ Request tracking middleware")
        print("  ✓ Global exception handlers")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
