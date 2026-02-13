# Production Deployment Checklist - File Storage

## 🚨 CRITICAL: Complete Before First Production Deploy

### Why This Matters
Files stored with `STORAGE_BACKEND=local` on Render.com will be **permanently deleted** on every:
- Code deployment (git push)
- App restart
- Container crash
- Platform maintenance

**All uploaded invoice PDFs will be lost. This is unacceptable for a financial SaaS.**

---

## Step 1: Create AWS S3 Bucket (15 minutes)

### Option A: AWS Console (Easiest)
1. Go to [AWS S3 Console](https://console.aws.amazon.com/s3)
2. Click "Create bucket"
3. **Bucket name:** `statementbur-invoices-prod` (must be globally unique)
4. **Region:** Choose closest to your users (e.g., `us-west-2` for US West Coast)
5. **Block Public Access:** ✅ Keep ALL boxes checked (critical for security)
6. **Bucket Versioning:** Enable (optional, allows recovery from accidental deletion)
7. **Default encryption:** ✅ Enable SSE-S3 (Amazon S3-managed keys)
8. Click "Create bucket"

### Option B: AWS CLI (Faster)
```bash
# Set your bucket name (must be globally unique)
BUCKET_NAME="statementbur-invoices-prod"
REGION="us-west-2"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**✅ Checkpoint:** Bucket created and secured

---

## Step 2: Create IAM User with Minimal Permissions (10 minutes)

### Create IAM Policy

**Save this as `s3-policy.json`:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvoiceStorageAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetObjectAttributes"
      ],
      "Resource": [
        "arn:aws:s3:::statementbur-invoices-prod",
        "arn:aws:s3:::statementbur-invoices-prod/*"
      ]
    }
  ]
}
```

**⚠️ Update the bucket name in the policy if you used a different name!**

### Create IAM User and Attach Policy

```bash
# Create IAM user
aws iam create-user --user-name statementbur-s3-access

# Attach policy
aws iam put-user-policy \
  --user-name statementbur-s3-access \
  --policy-name S3InvoiceStoragePolicy \
  --policy-document file://s3-policy.json

# Create access keys
aws iam create-access-key --user-name statementbur-s3-access
```

**⚠️ SAVE THE OUTPUT!** You'll see something like:
```json
{
    "AccessKey": {
        "UserName": "statementbur-s3-access",
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "Status": "Active"
    }
}
```

**Copy these values - you'll need them in Step 3:**
- `AccessKeyId` → This is your `S3_ACCESS_KEY`
- `SecretAccessKey` → This is your `S3_SECRET_KEY`

**✅ Checkpoint:** IAM user created, credentials saved

---

## Step 3: Configure Render.com Environment Variables (5 minutes)

### In Render Dashboard:

1. Go to your **statementbur-api** service
2. Click **Environment** tab
3. Add/Update these variables:

| Variable Name | Value | Notes |
|---------------|-------|-------|
| `STORAGE_BACKEND` | `s3` | ⚠️ Critical change from `local` |
| `S3_BUCKET_NAME` | `statementbur-invoices-prod` | Your bucket name |
| `S3_REGION` | `us-west-2` | Your bucket region |
| `S3_ACCESS_KEY` | Your AccessKeyId | From Step 2 - keep secret! |
| `S3_SECRET_KEY` | Your SecretAccessKey | From Step 2 - keep secret! |
| `SIGNED_URL_EXPIRATION_SECONDS` | `3600` | 1 hour (default) |

**⚠️ Security Note:** 
- Mark `S3_ACCESS_KEY` and `S3_SECRET_KEY` as **secret** (not shown in logs)
- Never commit these to git
- Rotate credentials every 90 days

**✅ Checkpoint:** Environment variables configured in Render

---

## Step 4: Deploy and Test (15 minutes)

### 4.1: Deploy

```bash
# Commit the render.yaml changes
git add render.yaml
git commit -m "Configure AWS S3 storage for production"
git push origin main
```

Render will automatically deploy. Wait for "Live" status.

### 4.2: Test File Upload

```bash
# Get your JWT token first (login to get token)
TOKEN="your-jwt-token-here"
API_URL="https://statementbur-api.onrender.com"
SESSION_ID="test-session-123"

# Upload a test invoice
curl -X POST "$API_URL/invoice/upload_file_auto?session_id=$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-invoice.pdf"

# Expected response:
# {
#   "success": true,
#   "invoice_id": 123,
#   "file_key": "invoices/abc-123_test-invoice.pdf",
#   ...
# }
```

### 4.3: Verify File in S3

```bash
# List files in your bucket
aws s3 ls s3://statementbur-invoices-prod/invoices/

# You should see your uploaded file!
# Example output:
# 2026-02-13 10:30:45    125890 invoices/abc-123_test-invoice.pdf
```

### 4.4: Test File Download

```bash
# Get invoice details (includes pre-signed URL)
curl "$API_URL/invoice/123" \
  -H "Authorization: Bearer $TOKEN"

# Download the invoice PDF using the signed URL from response
# (URL will look like: https://statementbur-invoices-prod.s3.amazonaws.com/...)
curl "SIGNED_URL_FROM_RESPONSE" -o downloaded-invoice.pdf

# Verify the file downloaded correctly
file downloaded-invoice.pdf
# Expected: downloaded-invoice.pdf: PDF document, version 1.4
```

### 4.5: Test Persistence (CRITICAL)

```bash
# 1. Note the file_key from upload response
FILE_KEY="invoices/abc-123_test-invoice.pdf"

# 2. Trigger a redeploy (push any change)
echo "# Test comment" >> README.md
git add README.md
git commit -m "Test redeploy persistence"
git push

# 3. Wait for deployment to complete (~5 minutes)

# 4. Verify file still exists in S3
aws s3 ls s3://statementbur-invoices-prod/invoices/

# 5. Verify API can still download it
curl "$API_URL/invoice/123" -H "Authorization: Bearer $TOKEN"
```

**✅ Expected Result:** File still exists after redeploy!
**❌ If using local storage:** File would be gone (404 error)

**✅ Checkpoint:** File storage working and persists across deploys

---

## Step 5: Clean Up Test Data (Optional)

```bash
# Delete test invoice from database (via API)
curl -X DELETE "$API_URL/invoice/123" \
  -H "Authorization: Bearer $TOKEN"

# Verify file was deleted from S3
aws s3 ls s3://statementbur-invoices-prod/invoices/
# (test file should be gone)
```

---

## Verification Checklist

- [ ] S3 bucket created with encryption enabled
- [ ] S3 bucket has public access blocked (all 4 settings)
- [ ] IAM user created with minimal S3 permissions
- [ ] Access key and secret key saved securely
- [ ] Render environment variables updated (STORAGE_BACKEND=s3)
- [ ] S3 credentials added to Render (marked as secret)
- [ ] Application deployed successfully
- [ ] Test file uploaded to API
- [ ] File exists in S3 bucket (verified with AWS CLI)
- [ ] File can be downloaded via API (signed URL works)
- [ ] File persists after redeploy (CRITICAL TEST)
- [ ] Test data cleaned up
- [ ] Credentials stored in password manager (not in code!)

---

## Estimated Costs

### First Month (Assuming 10 Test Users)
- Storage: 0.1GB × $0.023/GB = **$0.002**
- Requests: 100 uploads + 500 downloads = **$0.05**
- Data transfer: 0.5GB out × $0.09/GB = **$0.05**
- **Total: ~$0.10/month**

### At 100 Active Users (Business Case)
- Storage: 1GB × $0.023/GB = **$0.02**
- Requests: 2,000 uploads + 10,000 downloads = **$0.50**
- Data transfer: 5GB out × $0.09/GB = **$0.45**
- **Total: ~$1.00/month**

### At 1,000 Users (Scale)
- Storage: 10GB × $0.023/GB = **$0.23**
- Requests: 20K uploads + 100K downloads = **$5.00**
- Data transfer: 50GB out × $0.09/GB = **$4.50**
- **Total: ~$10/month**

**Negligible cost compared to data loss risk!**

---

## Troubleshooting

### Error: "Failed to upload to S3: An error occurred (AccessDenied)"
**Cause:** IAM permissions incorrect or credentials wrong

**Fix:**
1. Verify IAM policy allows `s3:PutObject` on your bucket
2. Check `S3_ACCESS_KEY` and `S3_SECRET_KEY` are correct in Render
3. Verify bucket name matches in policy and environment variable

### Error: "Failed to upload to S3: An error occurred (NoSuchBucket)"
**Cause:** Bucket name mismatch or bucket doesn't exist

**Fix:**
1. Verify bucket exists: `aws s3 ls s3://your-bucket-name`
2. Check `S3_BUCKET_NAME` matches actual bucket name
3. Verify region matches: `S3_REGION` should match bucket region

### Error: "File not found in S3" after upload reports success
**Cause:** Wrong bucket or region configured

**Fix:**
1. Check which bucket was used: Look at API logs
2. List all your buckets: `aws s3 ls`
3. Search for file in all buckets: `aws s3 ls s3://BUCKET-NAME/invoices/ --recursive`

### Files still disappearing after redeploy
**Cause:** Still using local storage!

**Fix:**
1. Check Render environment: `STORAGE_BACKEND` must be `s3` (not `local`)
2. Verify deployment used new config (check build logs)
3. Test: Upload file → trigger redeploy → verify file still accessible

---

## Security Best Practices

### ✅ Currently Implemented
- Bucket encryption (AES256)
- Public access blocked
- IAM least-privilege access
- Pre-signed URLs (time-limited)
- Audit logging in database

### 🔒 Additional Recommendations (Optional)

#### 1. Enable S3 Access Logging
```bash
# Create logging bucket
aws s3 mb s3://statementbur-invoices-logs

# Enable logging
aws s3api put-bucket-logging \
  --bucket statementbur-invoices-prod \
  --bucket-logging-status \
  '{"LoggingEnabled":{"TargetBucket":"statementbur-invoices-logs","TargetPrefix":"access-logs/"}}'
```

#### 2. Enable S3 Object Lock (Prevent Deletion)
```bash
# Enable object lock (must be done at bucket creation)
aws s3api create-bucket \
  --bucket statementbur-invoices-prod \
  --region us-west-2 \
  --object-lock-enabled-for-bucket
```

#### 3. Set Up CloudWatch Alarms
- Alert on high S3 costs (>$10/month)
- Alert on unusual delete operations
- Alert on access denied errors

#### 4. Rotate IAM Credentials Quarterly
```bash
# Create new access key
aws iam create-access-key --user-name statementbur-s3-access

# Update Render environment variables with new credentials

# Test that new credentials work

# Delete old access key
aws iam delete-access-key \
  --user-name statementbur-s3-access \
  --access-key-id OLD_ACCESS_KEY_ID
```

---

## Support and Documentation

### Related Documentation
- 📄 `FILE_STORAGE_AUDIT_REPORT.md` - Complete security audit
- 📄 `CLOUD_FILE_STORAGE_GUIDE.md` - Developer guide
- 📄 `CLOUD_STORAGE_IMPLEMENTATION_COMPLETE.md` - Implementation notes

### AWS Resources
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [S3 Pricing Calculator](https://calculator.aws/#/addService/S3)

### Need Help?
- AWS Support: https://console.aws.amazon.com/support
- Render Support: https://render.com/docs/support
- This project: Check documentation or contact dev team

---

## Final Notes

**This is not optional.** Using local storage in production will cause:
- ❌ Permanent data loss
- ❌ Customer trust issues
- ❌ Potential legal/compliance problems
- ❌ Loss of revenue

**S3 storage is:**
- ✅ Required for production
- ✅ Minimal cost (<$1/month initially)
- ✅ Fast to set up (1 hour total)
- ✅ Production-ready and scalable

**Complete this checklist before your first production deployment!**
