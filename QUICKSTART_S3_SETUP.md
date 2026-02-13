# Quick Fix: AWS S3 Storage Setup
## ⏱️ Time: 15 minutes | 💰 Cost: <$1/month

---

## Prerequisites

✅ AWS Account (free tier works)  
✅ AWS CLI installed: https://aws.amazon.com/cli/  
✅ Render.com account with deployed service

---

## Option 1: Automated Setup (Recommended)

### Step 1: Run Setup Script

```powershell
# From project root directory
.\setup-s3-storage.ps1
```

This script will:
- ✅ Create S3 bucket with encryption
- ✅ Block public access
- ✅ Create IAM user with minimal permissions
- ✅ Generate access credentials
- ✅ Save credentials to `aws-s3-credentials.txt`

**Expected output:**
```
✅ SETUP COMPLETE!

STORAGE_BACKEND=s3
S3_BUCKET_NAME=statementbur-invoices-prod
S3_REGION=us-west-2
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalr...EXAMPLEKEY
```

### Step 2: Update Render Environment

1. Go to https://dashboard.render.com
2. Select **statementbur-api** service
3. Click **Environment** tab
4. Update/Add these variables:

   | Variable | Value |
   |----------|-------|
   | `STORAGE_BACKEND` | `s3` |
   | `S3_BUCKET_NAME` | (from script output) |
   | `S3_REGION` | (from script output) |
   | `S3_ACCESS_KEY` | (from script output) |
   | `S3_SECRET_KEY` | (from script output) |

5. Click **Save Changes** (triggers auto-deploy)

### Step 3: Test Configuration

```powershell
# After Render deployment completes (~5 minutes)
.\test-s3-storage.ps1
```

Expected: All 8 tests pass ✅

### Step 4: Clean Up

```powershell
# Delete credentials file (security)
Remove-Item aws-s3-credentials.txt
```

---

## Option 2: Manual Setup

### 1. Configure AWS CLI (if not done)

```powershell
aws configure
# Enter: Access Key ID, Secret Key, Region (us-west-2), Output (json)
```

### 2. Create S3 Bucket

```powershell
$BUCKET = "statementbur-invoices-prod"
$REGION = "us-west-2"

# Create bucket
aws s3 mb "s3://$BUCKET" --region $REGION

# Enable encryption
aws s3api put-bucket-encryption `
  --bucket $BUCKET `
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Block public access
aws s3api put-public-access-block `
  --bucket $BUCKET `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### 3. Create IAM User

```powershell
# Create user
aws iam create-user --user-name statementbur-s3-access

# Create policy file
@"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::statementbur-invoices-prod", "arn:aws:s3:::statementbur-invoices-prod/*"]
  }]
}
"@ | Out-File s3-policy.json

# Attach policy
aws iam put-user-policy `
  --user-name statementbur-s3-access `
  --policy-name S3InvoiceAccess `
  --policy-document file://s3-policy.json

# Create access keys
aws iam create-access-key --user-name statementbur-s3-access
```

**⚠️ Save the AccessKeyId and SecretAccessKey from output!**

### 4. Update Render.com

See Step 2 in Option 1 above.

---

## Verification Checklist

After deployment completes:

- [ ] Run `.\test-s3-storage.ps1` - all tests pass
- [ ] Upload a test invoice via API
- [ ] Verify file in S3: `aws s3 ls s3://statementbur-invoices-prod/invoices/`
- [ ] **Critical:** Trigger a redeploy, verify file still exists
- [ ] Delete test invoice
- [ ] Delete `aws-s3-credentials.txt`

---

## Troubleshooting

### "AWS CLI not found"
```powershell
# Install AWS CLI
winget install Amazon.AWSCLI
# OR download from: https://aws.amazon.com/cli/
```

### "AWS credentials not configured"
```powershell
aws configure
# Enter your AWS access key, secret key, region
```

### "Could not create access key (LimitExceeded)"
```powershell
# List existing keys
aws iam list-access-keys --user-name statementbur-s3-access

# Delete old key
aws iam delete-access-key --user-name statementbur-s3-access --access-key-id OLD_KEY_ID

# Try again
aws iam create-access-key --user-name statementbur-s3-access
```

### "Access Denied" errors
- Check IAM policy is attached: `aws iam get-user-policy --user-name statementbur-s3-access --policy-name S3InvoiceStoragePolicy`
- Verify bucket name matches in policy and environment variables
- Check credentials are correct in Render

### Files still disappearing
- Verify `STORAGE_BACKEND=s3` in Render environment (not `local`)
- Check Render logs for storage errors
- Run `.\test-s3-storage.ps1` to verify S3 configuration

---

## Cost Breakdown

**Typical costs for 100 users:**

| Item | Usage | Cost |
|------|-------|------|
| Storage | 1 GB/month | $0.02 |
| PUT requests | 2,000/month | $0.01 |
| GET requests | 10,000/month | $0.004 |
| Data transfer | 5 GB out | $0.45 |
| **Total** | | **~$0.50/month** |

First 5GB egress free, so actual cost may be lower!

---

## Security Notes

✅ **Configured Automatically:**
- Server-side encryption (AES256)
- Public access blocked
- IAM least-privilege access
- Pre-signed URLs (1-hour expiration)

⚠️ **Your Responsibility:**
- Keep credentials secure (password manager)
- Never commit credentials to git
- Rotate credentials every 90 days
- Monitor AWS bills monthly

---

## Next Steps After Setup

1. ✅ Test thoroughly in staging first
2. ✅ Set up CloudWatch alarms for S3 costs
3. ✅ Enable S3 access logging (optional)
4. ✅ Configure backup/lifecycle policies
5. ✅ Document credentials in team password manager

---

## Support

- 📖 Full audit: [FILE_STORAGE_AUDIT_REPORT.md](FILE_STORAGE_AUDIT_REPORT.md)
- 📖 Detailed guide: [PRODUCTION_STORAGE_CHECKLIST.md](PRODUCTION_STORAGE_CHECKLIST.md)
- 🔧 AWS Support: https://console.aws.amazon.com/support
- 🌐 Render Support: https://render.com/docs/support

---

**Ready? Run `.\setup-s3-storage.ps1` now! ⚡**
