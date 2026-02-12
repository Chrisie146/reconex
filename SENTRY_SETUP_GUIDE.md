# Sentry Error Monitoring - Setup Guide

## Overview

Sentry provides real-time error tracking and performance monitoring for production applications. This integration captures unhandled exceptions, server errors, and performance metrics, helping you find and fix issues before they impact users.

**What Sentry Monitors:**
- ✅ Unhandled exceptions (500 errors)
- ✅ Server errors (status >= 500)
- ✅ Performance bottlenecks (slow endpoints)
- ✅ Database query performance
- ✅ Request context and user sessions

**Cost:** Free tier includes 5,000 errors/month + 10,000 performance units

---

## Quick Start (5 minutes)

### 1. Create Sentry Account

1. Go to https://sentry.io
2. Sign up for a free account (no credit card required)
3. Create a new project:
   - Platform: **Python**
   - Framework: **FastAPI** (or Generic Python)
   - Project name: `bank-statement-analyzer`

### 2. Get Your DSN

After creating the project, Sentry will show you a **Data Source Name (DSN)**:

```
https://1234567890abcdef@o123456.ingest.sentry.io/4567890
```

Copy this DSN - you'll need it for configuration.

### 3. Configure Environment Variables

Add to your [backend/.env](backend/.env) file:

```env
# Sentry Error Monitoring
SENTRY_DSN=https://your-dsn-here@o123456.ingest.sentry.io/4567890
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_SEND_DEFAULT_PII=false
```

### 4. Restart Server

```bash
cd backend
uvicorn main:app --reload
```

You should see in the logs:

```
✅ Sentry error monitoring initialized
   Environment: development
   Traces Sample Rate: 10%
```

### 5. Test Error Capture (Optional)

Add a test endpoint to [backend/main.py](backend/main.py):

```python
@app.get("/debug/sentry-test", tags=["Debug"])
def test_sentry():
    """Test Sentry error capture (remove in production)"""
    raise Exception("Test Sentry integration - this should appear in Sentry dashboard")
```

Visit: http://localhost:8000/debug/sentry-test

Check Sentry dashboard (https://sentry.io) - the error should appear within seconds!

**⚠️ Important:** Remove this test endpoint before deploying to production.

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | **Yes** | `""` | Data Source Name from Sentry project settings |
| `SENTRY_ENABLED` | No | `true` | Enable/disable Sentry (auto-disabled if DSN empty) |
| `SENTRY_ENVIRONMENT` | No | `development` | Environment name (development, staging, production) |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | % of transactions to trace (0.0-1.0) |
| `SENTRY_PROFILES_SAMPLE_RATE` | No | `0.1` | % of transactions to profile (0.0-1.0) |
| `SENTRY_SEND_DEFAULT_PII` | No | `false` | Send personally identifiable information |

### Sample Rate Guidelines

**Development:**
```env
SENTRY_TRACES_SAMPLE_RATE=1.0  # Capture 100% for debugging
SENTRY_PROFILES_SAMPLE_RATE=1.0
```

**Production (Low Traffic < 1000 req/day):**
```env
SENTRY_TRACES_SAMPLE_RATE=0.1  # Capture 10%
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

**Production (High Traffic > 10,000 req/day):**
```env
SENTRY_TRACES_SAMPLE_RATE=0.01  # Capture 1%
SENTRY_PROFILES_SAMPLE_RATE=0.01
```

**Cost Impact:**
- 1.0 (100%) = Highest cost, most detailed data
- 0.1 (10%) = Recommended balance
- 0.01 (1%) = Lowest cost, sufficient for large apps

---

## What Gets Captured

### Automatically Captured ✅

**1. Unhandled Exceptions**
```python
# Example: Division by zero
result = 10 / 0  # Captured automatically!
```

**2. Server Errors (HTTP 500+)**
```python
# Example: Database errors
db.query(Transaction).filter(bad_query).all()  # Captured!
```

**3. Request Context**
- URL and method
- Request headers
- Request ID (from middleware)
- User agent and IP
- Query parameters

**4. User Context** (when authenticated)
```python
# Automatically added when user is logged in
{
  "id": 123,
  "email": "user@example.com"  # if SEND_DEFAULT_PII=true
}
```

**5. Performance Metrics**
- Endpoint response times
- Database query duration
- External API calls
- Cache hit/miss rates

### NOT Captured (Filtered Out) ❌

**Client Errors:**
- 404 Not Found
- 401 Unauthorized
- 403 Forbidden
- 422 Validation Error
- 429 Rate Limit Exceeded

**Reason:** These are expected errors, not bugs. Capturing them would create noise.

---

## Integrations

Sentry automatically integrates with:

### 1. FastAPI
- Automatic transaction tracking
- Request/response context
- Endpoint performance monitoring

### 2. SQLAlchemy
- Database query tracking
- Query duration monitoring
- Connection pool metrics

### 3. Redis
- Cache operation tracking
- Connection monitoring
- Performance metrics

### 4. Celery (Background Jobs)
- Task error tracking
- Task duration monitoring
- Worker performance

---

## Error Filtering

### Before Send Hook

Sentry uses a `_before_send_sentry()` function to filter errors:

```python
def _before_send_sentry(event, hint):
    """Filter errors before sending to Sentry"""
    
    # Don't send HTTP 404 errors
    if isinstance(exc_value, HTTPException) and exc_value.status_code == 404:
        return None  # Discard event
    
    # Don't send authentication errors
    if exc_value.status_code in [401, 403]:
        return None
    
    # Add custom tags
    event['tags']['environment'] = Config.SENTRY_ENVIRONMENT
    
    return event  # Send event
```

**Customize in [backend/main.py](backend/main.py)** to filter more error types.

---

## Sentry Dashboard

### Viewing Errors

1. Go to https://sentry.io
2. Select your project
3. View **Issues** tab for errors

**Each error shows:**
- Error message and type
- Stack trace
- Request URL and method
- User information (if authenticated)
- Server environment
- Breadcrumbs (events leading to error)
- Similar errors (grouped)

### Performance Monitoring

1. Click **Performance** tab
2. View:
   - Slowest endpoints
   - Database query times
   - External API call duration
   - Apdex score (user satisfaction)

### Releases

Track errors by deployment:

```bash
# Tag errors with release version
SENTRY_RELEASE=v1.2.3
```

Add to environment variables:
```env
SENTRY_RELEASE=v1.2.3
```

Sentry will show:
- New errors in this release
- Regressions (errors that came back)
- Errors fixed in this release

---

## Alerting & Notifications

### Setup Alerts

1. Go to **Alerts** → **Create Alert**
2. Choose alert type:
   - **Issues:** Alert when new error occurs
   - **Metric:** Alert on error rate threshold
   - **Uptime:** Alert on downtime

### Recommended Alerts

**1. New Error Type**
- **Trigger:** First time an error occurs
- **Action:** Email + Slack notification
- **Priority:** High

**2. Error Spike**
- **Trigger:** >10 errors in 5 minutes
- **Action:** Email + SMS
- **Priority:** Critical

**3. Performance Degradation**
- **Trigger:** P95 response time >2 seconds
- **Action:** Slack notification
- **Priority:** Medium

### Integration Options
- Email notifications
- Slack integration
- PagerDuty integration
- Webhook (custom integrations)

---

## Best Practices

### 1. Review Errors Daily

Set up a morning routine:
1. Check Sentry dashboard
2. Review new errors
3. Triage by severity:
   - **Critical:** Fix immediately
   - **High:** Fix within 24 hours
   - **Medium:** Fix within 1 week
   - **Low:** Backlog

### 2. Mark Errors as Resolved

After fixing an error:
1. Deploy the fix
2. Mark error as "Resolved" in Sentry
3. If error recurs, Sentry will reopen it automatically

### 3. Use Error Grouping

Sentry groups similar errors:
- Same error type
- Same stack trace
- Same location in code

**Benefits:**
- Reduces noise (100 identical errors = 1 issue)
- Shows error frequency
- Tracks error trends

### 4. Add Context with Tags

Add custom tags in your code:

```python
import sentry_sdk

# Tag errors by feature
sentry_sdk.set_tag("feature", "pdf_parsing")

# Tag by user type
sentry_sdk.set_tag("user_type", "premium")
```

**Use cases:**
- Filter errors by feature
- Track errors by user tier
- Monitor A/B test variants

### 5. Add Breadcrumbs

Breadcrumbs show events leading to error:

```python
sentry_sdk.add_breadcrumb(
    category="upload",
    message="User uploaded PDF",
    level="info",
    data={"file_size": 1024000}
)
```

**Automatically added:**
- HTTP requests
- Database queries
- Cache operations
- Log messages

### 6. Monitor Performance

Watch for:
- **Slow endpoints:** >1 second response time
- **Database queries:** N+1 problems
- **External APIs:** Timeouts and failures
- **Memory leaks:** Increasing usage over time

### 7. Set Budget Alerts

Free tier limits:
- 5,000 errors/month
- 10,000 performance units/month

**Setup budget alerts:**
1. Settings → Usage & Billing
2. Set threshold at 80% (4,000 errors)
3. Configure email notification

**If you hit limits:**
- Sentry stops capturing new errors
- Existing errors remain visible
- Upgrade to paid plan or reduce sample rate

---

## Troubleshooting

### Sentry Not Capturing Errors

**1. Check DSN is configured:**
```bash
# In backend/.env
SENTRY_DSN=https://...@sentry.io/...
```

**2. Check Sentry is enabled:**
```bash
# In logs, you should see:
✅ Sentry error monitoring initialized
```

**3. Check error type is captured:**
- Only HTTP 500+ errors are captured
- 404, 401, 403 are filtered out (by design)

**4. Check sample rate:**
```bash
# If sample rate is too low, some errors won't be captured
SENTRY_TRACES_SAMPLE_RATE=0.01  # Only 1% of errors
```

Set to 1.0 for development to capture everything.

### Too Many Errors Captured

**1. Filter noisy errors:**

Edit `_before_send_sentry()` in [backend/main.py](backend/main.py):

```python
def _before_send_sentry(event, hint):
    # Filter out specific error types
    if 'database timeout' in str(exc_value):
        return None  # Don't send
    
    return event
```

**2. Reduce sample rate:**
```env
SENTRY_TRACES_SAMPLE_RATE=0.1  # Capture only 10%
```

**3. Use error grouping:**
- Sentry groups similar errors automatically
- 1000 identical errors = 1 issue in dashboard

### Sentry Quota Exceeded

**Option 1: Reduce sample rate**
```env
SENTRY_TRACES_SAMPLE_RATE=0.01  # 1% instead of 10%
```

**Option 2: Filter more errors**
- Add more filters in `_before_send_sentry()`
- Only capture critical errors

**Option 3: Upgrade plan**
- Free: 5,000 errors/month ($0)
- Team: 50,000 errors/month ($26/month)
- Business: Unlimited ($80/month)

---

## Security & Privacy

### PII (Personally Identifiable Information)

**By default, Sentry DOES send:**
- User ID
- IP address (anonymized)
- Request URLs

**By default, Sentry does NOT send:**
- Email addresses
- Passwords
- Request bodies
- HTTP headers (except standard ones)

### Disable PII Completely

```env
SENTRY_SEND_DEFAULT_PII=false
```

This removes:
- IP addresses
- User identifiers
- Query parameters containing PII

### GDPR Compliance

Sentry is GDPR compliant:
- Data stored in EU (optional)
- User data deletion on request
- Data processing agreement available

**Configure data location:**
1. Go to Settings → General
2. Choose **EU Data Residency** (paid plans)

### Scrubbing Sensitive Data

Add custom scrubbing in `_before_send_sentry()`:

```python
def _before_send_sentry(event, hint):
    # Remove sensitive query params
    if 'request' in event:
        url = event['request'].get('url', '')
        # Remove password from URL
        url = url.replace('password=', 'password=***')
        event['request']['url'] = url
    
    return event
```

---

## Production Deployment

### 1. Production .env Configuration

```env
# === PRODUCTION SENTRY CONFIG ===

# Get production DSN from Sentry (separate from development)
SENTRY_DSN=https://prod-dsn@sentry.io/prod-project-id

# Enable Sentry in production
SENTRY_ENABLED=true

# Set environment to production
SENTRY_ENVIRONMENT=production

# Lower sample rate to reduce costs
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10%
SENTRY_PROFILES_SAMPLE_RATE=0.1

# Disable PII for privacy
SENTRY_SEND_DEFAULT_PII=false

# Tag with release version
SENTRY_RELEASE=v1.0.0
```

### 2. Separate Projects

Create separate Sentry projects for each environment:
- `bank-analyzer-dev` (development environment)
- `bank-analyzer-staging` (staging environment)
- `bank-analyzer-prod` (production environment)

**Benefits:**
- Isolate development errors from production
- Different alerting rules per environment
- Separate quotas and billing

### 3. Release Tracking

Tag errors with release version:

```bash
# In CI/CD pipeline or deployment script
export SENTRY_RELEASE=v1.2.3

# Notify Sentry of new release
sentry-cli releases new $SENTRY_RELEASE
sentry-cli releases set-commits $SENTRY_RELEASE --auto
sentry-cli releases finalize $SENTRY_RELEASE
```

### 4. Health Checks

Sentry provides a health check API:

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "sentry_enabled": Config.SENTRY_ENABLED,
        "sentry_environment": Config.SENTRY_ENVIRONMENT
    }
```

### 5. Monitor Deployment Success

After deploying:
1. Check Sentry dashboard
2. Verify no new errors
3. Check performance hasn't degraded
4. Review release health (Sentry Releases page)

---

## Cost Management

### Free Tier Limits

- **5,000 errors** per month
- **10,000 performance units** per month
- 1 project
- 30 days data retention

**What happens when you exceed:**
- Sentry stops accepting new events
- Existing data remains accessible
- No charges (free tier never bills)

### Optimizing Usage

**1. Reduce Sample Rate**
```env
SENTRY_TRACES_SAMPLE_RATE=0.05  # 5% instead of 10%
```

**2. Filter Noisy Errors**
```python
# Don't capture expected errors
if 'connection reset' in str(exc):
    return None  # Don't send to Sentry
```

**3. Only Monitor Production**
```env
# Development - disable Sentry
SENTRY_ENABLED=false

# Production - enable Sentry
SENTRY_ENABLED=true
```

**4. Use Error Grouping**
- Sentry groups similar errors → counts as 1 event
- 1000 identical errors = 1 event

### Paid Plans

**Team Plan: $26/month**
- 50,000 errors/month
- 100,000 performance units/month
- 5 projects
- 90 days retention
- Slack/PagerDuty integration

**Business Plan: $80/month**
- Unlimited errors
- Unlimited performance
- Unlimited projects
- 90 days retention
- SSO, advanced features

**Enterprise: Custom pricing**
- Custom retention
- On-premise option
- SLA guarantee
- Dedicated support

---

## Monitoring Dashboard

### Key Metrics to Watch

**1. Error Rate**
- Target: < 1% of requests
- Alert: > 5% of requests

**2. New Error Types**
- Target: 0 new errors per deployment
- Alert: Any new unhandled exception

**3. P95 Response Time**
- Target: < 500ms for API endpoints
- Alert: > 2 seconds

**4. Apdex Score**
- Target: > 0.95 (95% satisfied users)
- Alert: < 0.80

### Creating Custom Dashboards

1. Go to **Dashboards** → **Create Dashboard**
2. Add widgets:
   - Error frequency chart
   - Slowest endpoints
   - Error types breakdown
   - User-facing errors
3. Share with team

---

## Support & Resources

### Official Documentation
- **Sentry Docs:** https://docs.sentry.io/
- **Python SDK:** https://docs.sentry.io/platforms/python/
- **FastAPI Guide:** https://docs.sentry.io/platforms/python/guides/fastapi/

### Community Support
- **Discord:** https://discord.gg/sentry
- **Forum:** https://forum.sentry.io/
- **GitHub:** https://github.com/getsentry/sentry

### Getting Help
1. Check Sentry documentation
2. Search forum for similar issues
3. Ask in Discord #help channel
4. Open GitHub issue (for SDK bugs)

---

## Summary

Sentry error monitoring is now fully integrated! 🎉

**What's Been Configured:**
- ✅ Sentry SDK installed
- ✅ Error handlers capture exceptions
- ✅ FastAPI, SQLAlchemy, Redis integrations enabled
- ✅ User context tracking
- ✅ Performance monitoring
- ✅ Privacy-safe configuration (no PII by default)

**Next Steps:**
1. Create Sentry account (5 minutes)
2. Add SENTRY_DSN to .env
3. Restart server
4. Test with debug endpoint
5. Setup alerts and notifications
6. Review errors daily

**Production Ready:** ✅  
This integration is production-ready and follows Sentry best practices.

---

**Last Updated:** February 12, 2026  
**Version:** 1.0.0  
**Status:** ✅ Complete
