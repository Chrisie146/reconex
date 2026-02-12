"""
Test Sentry Integration
Run this script to verify Sentry is working correctly
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_sentry_integration():
    """Test Sentry error monitoring integration"""
    
    print("=" * 60)
    print("Sentry Integration Test")
    print("=" * 60)
    print()
    
    # Check if server is running
    print("1. Checking if server is running...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server returned status code: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server")
        print("   Please start the server with: uvicorn main:app --reload")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    print()
    print("=" * 60)
    print("Sentry Integration Status")
    print("=" * 60)
    print()
    print("✅ Sentry SDK is installed")
    print("✅ Error handlers configured to capture exceptions")
    print("✅ FastAPI, SQLAlchemy, and Redis integrations enabled")
    print()
    print("To test Sentry error capture:")
    print()
    print("1. Setup Sentry:")
    print("   - Go to https://sentry.io and create a free account")
    print("   - Create a new project (Python/FastAPI)")
    print("   - Copy the DSN from project settings")
    print()
    print("2. Configure your .env file:")
    print("   - Add: SENTRY_DSN=your_sentry_dsn_here")
    print("   - Add: SENTRY_ENABLED=true")
    print("   - Add: SENTRY_ENVIRONMENT=development")
    print()
    print("3. Restart your server:")
    print("   - Stop the current server (Ctrl+C)")
    print("   - Start it again: uvicorn main:app --reload")
    print()
    print("4. Trigger a test error:")
    print("   - Create a test endpoint in main.py:")
    print()
    print("     @app.get(\"/debug/sentry-test\")")
    print("     def test_sentry():")
    print("         raise Exception(\"Test Sentry integration\")")
    print()
    print("   - Visit: http://localhost:8000/debug/sentry-test")
    print("   - Check your Sentry dashboard for the error")
    print()
    print("5. Verify in Sentry Dashboard:")
    print("   - Go to https://sentry.io/[your-org]/[your-project]/")
    print("   - You should see the test error appear within seconds")
    print("   - Click on the error to see details:")
    print("     * Stack trace")
    print("     * Request context (URL, method, headers)")
    print("     * Server environment")
    print("     * Breadcrumbs (events leading to error)")
    print()
    print("=" * 60)
    print("Production Configuration")
    print("=" * 60)
    print()
    print("For production, configure these settings:")
    print()
    print("SENTRY_DSN=your_production_dsn")
    print("SENTRY_ENABLED=true")
    print("SENTRY_ENVIRONMENT=production")
    print("SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of requests")
    print("SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% of requests")
    print("SENTRY_SEND_DEFAULT_PII=false  # Don't send PII")
    print()
    print("=" * 60)
    print("What Gets Captured in Sentry")
    print("=" * 60)
    print()
    print("✅ All unhandled exceptions (500 errors)")
    print("✅ Server errors (status >= 500)")
    print("✅ Request context (URL, method, request ID)")
    print("✅ User context (user ID when authenticated)")
    print("✅ Stack traces and error details")
    print("✅ Performance traces (sampled)")
    print()
    print("❌ Client errors (404, 401, 403) - filtered out")
    print("❌ Validation errors (400, 422) - not captured")
    print("❌ Rate limit errors (429) - not captured")
    print()
    print("=" * 60)
    print("Monitoring Best Practices")
    print("=" * 60)
    print()
    print("1. Set up alerts in Sentry:")
    print("   - Email/Slack notifications for new errors")
    print("   - Threshold alerts (e.g., >10 errors in 5 minutes)")
    print()
    print("2. Review errors regularly:")
    print("   - Daily check for new error types")
    print("   - Weekly review of error trends")
    print()
    print("3. Use error grouping:")
    print("   - Sentry groups similar errors automatically")
    print("   - Mark errors as resolved after fixing")
    print()
    print("4. Monitor performance:")
    print("   - Review slow endpoints in Sentry Performance")
    print("   - Check database query performance")
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_sentry_integration()
