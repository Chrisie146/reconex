# Uptime Monitoring Setup Guide

## Overview

Uptime monitoring ensures you're immediately notified when your API goes down or becomes unresponsive. This guide covers setting up free uptime monitoring using popular services.

**What You'll Monitor:**
- ✅ HTTP endpoint availability (200 status code)
- ✅ Response time (latency)
- ✅ Database connectivity
- ✅ Cache service status (Redis)
- ✅ SSL certificate expiration (for HTTPS)

**Cost:** Free for all recommended services (5-minute checks, unlimited monitors)

---

## Quick Start (5 Minutes)

### Option 1: UptimeRobot (Recommended)

**Why UptimeRobot:**
- ✅ 100% free for 50 monitors
- ✅ 5-minute check intervals
- ✅ Email, SMS, Slack, webhook alerts
- ✅ Status page generation
- ✅ No credit card required

**Setup Steps:**

1. **Create Account**
   - Go to https://uptimerobot.com
   - Sign up for free account (no credit card)

2. **Add Monitor**
   - Click "Add New Monitor"
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `Bank Statement Analyzer API`
   - URL: `https://your-domain.com/health` (or `http://your-ip:8000/health` for testing)
   - Monitoring Interval: **5 minutes**
   - Monitor Timeout: **30 seconds**
   - HTTP Method: **GET (HEAD)**

3. **Configure Alerts**
   - Alert Contacts: Add your email
   - Send a notification when: **Down**
   - Advanced Settings:
     - Check for keyword: `"status":"healthy"` (optional but recommended)
     - Status Codes to Accept: `200-299`

4. **Test the Monitor**
   - Wait 5 minutes for first check
   - Stop your API server to test alerts
   - You should receive an email within 5 minutes

5. **Create Status Page (Optional)**
   - Public Status Pages → Create
   - Add your monitors
   - Share URL with users

---

### Option 2: Pingdom (Alternative)

**Why Pingdom:**
- ✅ Free tier: 10 uptime checks
- ✅ 1-minute check intervals
- ✅ Advanced reporting
- ✅ More detailed response time metrics

**Setup:**
1. Go to https://www.pingdom.com
2. Sign up (free trial, then free tier)
3. Add Uptime Check:
   - URL: `https://your-domain.com/health`
   - Check interval: **1 minute** (paid) or **5 minutes** (free)
   - Alert when: Down for 2 consecutive checks

---

### Option 3: Healthchecks.io (Developer-Friendly)

**Why Healthchecks.io:**
- ✅ Free: 20 checks
- ✅ Push-based monitoring (your app pings them)
- ✅ Cron job monitoring
- ✅ Great for background jobs

**Setup:**
1. Go to https://healthchecks.io
2. Sign up for free
3. Create a new check
4. Copy the ping URL
5. Use a scheduled task to ping that URL every 5 minutes

---

## Enhanced Health Endpoint

Your API already has an enhanced health endpoint at `/health`:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T14:15:10.412377Z",
  "version": "1.0.0",
  "database": "connected",
  "cache": "not_configured"
}
```

**What It Checks:**
- ✅ **status**: Always "healthy" if server responds (HTTP 200)
- ✅ **timestamp**: Server's current UTC time
- ✅ **version**: API version
- ✅ **database**: PostgreSQL/SQLite connectivity
- ✅ **cache**: Redis connection status

**For Monitoring:**
- Check for: `"status":"healthy"` keyword
- Expected status code: `200`
- Warn if response time > 2 seconds
- Alert if response time > 5 seconds

---

## Production Deployment Checklist

### 1. Before Deploying to Production

- [ ] Deploy API to production server (cloud VM, Heroku, AWS, Azure)
- [ ] Configure HTTPS with SSL certificate (Let's Encrypt recommended)
- [ ] Update `.env` with production settings:
  ```env
  ENVIRONMENT=production
  DEBUG=False
  DATABASE_URL=postgresql://...  # Production database
  SENTRY_ENVIRONMENT=production
  ```
- [ ] Test `/health` endpoint manually: `curl https://your-domain.com/health`

### 2. Configure Uptime Monitor

- [ ] Add monitor with production URL: `https://your-domain.com/health`
- [ ] Set check interval: **5 minutes** (free) or **1 minute** (paid)
- [ ] Enable keyword check: Look for `"status":"healthy"`
- [ ] Configure alert contacts (email, SMS, Slack)
- [ ] Test alerts by stopping server for 10 minutes

### 3. Alert Configuration Best Practices

**Email Alerts:**
- ✅ Primary contact: Your email
- ✅ Secondary contact: Team email or Slack webhook
- ✅ Alert on: Down for 2+ consecutive checks (reduces false positives)
- ✅ Recovery notification: Yes (know when it's back up)

**SMS Alerts (Optional but Recommended):**
- Use for critical alerts only (you'll get charged after free tier)
- Enable for production only, not staging

**Slack/Teams Integration:**
- Create a dedicated channel: `#api-alerts`
- Route both down and recovery notifications
- Helps team respond quickly

### 4. Response Time Thresholds

Configure alerts for slow performance:

| Metric | Warning | Critical |
|--------|---------|----------|
| Response Time | > 2 seconds | > 5 seconds |
| Uptime (Monthly) | < 99.5% | < 99.0% |
| Consecutive Failures | 2 checks | 3 checks |

---

## Monitoring Strategy

### Development Environment

```
Monitor: http://localhost:8000/health
Interval: 1 minute
Alerts: Email only
Purpose: Catch issues during development
```

### Staging Environment

```
Monitor: https://staging.yourdomain.com/health
Interval: 5 minutes
Alerts: Email + Slack
Purpose: Test deployment pipeline
```

### Production Environment

```
Monitor: https://api.yourdomain.com/health
Interval: 1-5 minutes
Alerts: Email + SMS + Slack + PagerDuty
Purpose: Ensure 99.9% uptime SLA
Keyword Check: "status":"healthy"
```

---

## Advanced Monitoring (Optional)

### 1. Monitor Multiple Endpoints

Don't just monitor `/health`. Also monitor critical endpoints:

| Endpoint | What It Tests | Interval |
|----------|---------------|----------|
| `/health` | Server, DB, Cache | 5 min |
| `/auth/register` | Auth system | 15 min |
| `/sessions` | Session API | 10 min |

**Note:** Use authenticated requests for protected endpoints (add headers in monitor config)

### 2. Geographic Monitoring

Monitor from multiple locations to catch regional issues:
- US East (New York)
- US West (San Francisco)
- Europe (London)
- Asia (Tokyo)

Most services offer this on paid plans (~$10-20/month).

### 3. SSL Certificate Monitoring

Avoid HTTPS outages due to expired certificates:
- UptimeRobot: Automatically checks SSL expiration
- Alert: 7 days before expiration
- Renewal: Use Let's Encrypt with auto-renewal

---

## Troubleshooting

### Monitor Shows "Down" But Server is Running

**Possible Causes:**
1. Firewall blocking monitoring service IPs
2. Rate limiting blocking repeated requests
3. Server responding > timeout threshold (30s)
4. Database connection timeout

**Solutions:**
- Check server logs for errors during down period
- Whitelist monitoring service IPs in firewall
- Increase timeout to 60 seconds
- Check Sentry for errors during downtime

### False Positives (Random Down Alerts)

**Possible Causes:**
1. Network blip (monitoring service had connectivity issue)
2. Server restarted (deployment or auto-restart)
3. Database connection pool exhaustion

**Solutions:**
- Require 2+ consecutive failed checks before alerting
- Schedule maintenance windows in monitor
- Increase database connection pool size

### Health Endpoint Returns 200 But App is Broken

**Possible Causes:**
1. Health check is too basic (only checks server, not functionality)
2. Database connected but queries failing
3. External dependencies (APIs) down

**Solutions:**
- Enhance health endpoint to test critical functionality
- Add database query test (SELECT 1 FROM transactions LIMIT 1)
- Monitor specific functional endpoints (`/sessions`)

---

## Integration with Other Tools

### Sentry Integration

Your API already has Sentry error monitoring. Combine with uptime monitoring:

**When API goes down:**
1. UptimeRobot sends alert: "API is down"
2. Check Sentry dashboard for errors during downtime
3. Sentry shows exact error that caused crash
4. Fix error and redeploy
5. UptimeRobot confirms recovery

### Slack Integration

**Setup:**
1. UptimeRobot: Settings → Alert Contacts → Add Slack
2. Authorize UptimeRobot Slack app
3. Choose channel: `#api-alerts`
4. Test notification

**Slack Message Format:**
```
🔴 **DOWN** Bank Statement Analyzer API
https://api.yourdomain.com/health
Duration: 5 minutes
Response: Connection timeout

[View Details] [Acknowledge]
```

---

## Cost Summary

### Free Tier Comparison

| Service | Monitors | Interval | Alerts | Status Page |
|---------|----------|----------|--------|-------------|
| **UptimeRobot** | 50 | 5 min | Unlimited | Yes |
| **Pingdom** | 10 | 5 min | Email only | No |
| **Healthchecks.io** | 20 | Any | Unlimited | No |
| **Better Uptime** | 10 | 3 min | Unlimited | Yes |

**Recommendation:** UptimeRobot for most users (best free tier)

### Paid Plans (If Needed)

**UptimeRobot Pro ($7/month):**
- 1-minute intervals
- 50+ monitors
- SMS alerts
- Advanced reporting

**Pingdom Starter ($10/month):**
- 1-minute intervals
- 10 monitors
- Transaction monitoring

---

## Next Steps

After setting up uptime monitoring, proceed with:

1. **Database Backups** (2 hours)
   - Automated daily PostgreSQL backups
   - Upload to cloud storage (S3/Azure/GCS)
   - Test restore procedure

2. **CI/CD Pipeline** (3-4 hours)
   - GitHub Actions for automated testing
   - Automated deployments to staging/production
   - Docker containerization

3. **Load Testing** (1-2 hours)
   - Test API performance under load
   - Identify bottlenecks
   - Optimize slow endpoints

---

## Verification Checklist

- [ ] Monitor created and active
- [ ] Health endpoint accessible: `curl https://your-domain.com/health`
- [ ] Alert contact configured (email/SMS/Slack)
- [ ] Test alert by stopping server (received notification)
- [ ] Recovery notification received (server back online)
- [ ] Keyword check enabled: `"status":"healthy"`
- [ ] Response time threshold set: Warn at 2s, Alert at 5s
- [ ] Status page created (optional)
- [ ] Team knows where to check uptime dashboard
- [ ] Documented in runbook for on-call engineers

---

## Production Readiness Impact

**Before Uptime Monitoring:**
- Phase 2 (High-Risk Security): 86%
- Phase 4 (DevOps & Monitoring): 10%
- Overall: 65%

**After Uptime Monitoring:**
- Phase 4 (DevOps & Monitoring): 20% (+10%)
- Overall: 68% (+3%)

**Remaining for Private Beta:**
- Database Backups (2 hours)

✅ **You're 3 hours away from launching private beta!**
