# File Storage Security Audit Report
**Date:** February 13, 2026  
**Application:** Bank Statement Analyzer (FastAPI SaaS)  
**Deployment Target:** Render.com

---

## Executive Summary

### 🚨 **CRITICAL FINDING: Files Will Be Lost on Render Redeploy**

**Current Configuration:** `STORAGE_BACKEND=local` (line 92 in render.yaml)

**Risk Level:** 🔴 **CRITICAL - DATA LOSS IMMINENT**

**Impact:**
- ✅ **Good News:** Bank statement uploads (CSV/PDF) are **NOT** stored - they're processed in-memory and discarded
- 🔴 **Bad News:** Invoice PDFs **ARE** permanently stored and **WILL BE DELETED** on every redeploy
- 🔴 Render uses ephemeral containers - any files in `/uploads` directory are lost when:
  - App restarts
  - New deployment occurs (code push)
  - Container crashes or scales
  - Platform maintenance happens

**Recommendation:** **MUST migrate to AWS S3 before production launch**

---

## Detailed Findings

### 1. ✅ File Storage Architecture (Well Designed)

**Status:** EXCELLENT - Production-ready abstraction layer already implemented

**What's Good:**
- Clean storage abstraction layer with multiple backends (`services/storage.py`)
- Supports AWS S3, Azure Blob, Google Cloud Storage, and local development
- Pre-signed URLs for secure time-limited access
- Server-side encryption on S3 uploads (AES256)
- File access audit logging in database (`FileAccessLog` model)
- Unique file keys with UUID: `invoices/{uuid}_{filename}`

**Code Quality:**
```python
# Storage abstraction is clean and well-structured
storage = get_storage()  # Returns configured backend
storage.upload_file(content, file_key, content_type="application/pdf")
url = storage.generate_signed_url(file_key, expiration_seconds=3600)
```

### 2. ✅ File Upload Security (Strong)

**Status:** GOOD - Multiple layers of protection

**Security Measures Implemented:**
- ✅ **Authentication Required:** All upload endpoints require JWT token (`current_user: User = Depends(get_current_user)`)
- ✅ **File Type Validation:** 
  - PDF-only validation for invoices
  - CSV/PDF validation for statements
  - Extension checking + optional MIME type detection with python-magic
  - Magic bytes validation available (if python-magic installed)
- ✅ **Size Limits:** 50MB max (configurable via `MAX_UPLOAD_SIZE_MB`)
- ✅ **Rate Limiting:** 10 uploads/minute, 100/hour per user
- ✅ **Empty File Rejection:** Files with 0 bytes are rejected
- ✅ **Session Ownership Validation:** Files linked to sessions are validated with `ensure_session_access()`
- ✅ **Audit Logging:** All file operations logged with user_id, timestamp, IP address

**Code Example:**
```python
@app.post("/invoice/upload_file_auto")
async def upload_invoice_file_auto(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    current_user: User = Depends(get_current_user),  # 🔒 Auth required
    db: Session = Depends(get_db)
):
    ensure_session_access(session_id, current_user, db)  # 🔒 Multi-tenant isolation
    
    # Validate PDF only
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    # Upload to cloud storage
    storage = get_storage()
    storage.upload_file(content, file_key, content_type="application/pdf")
    
    # Audit log
    log_file_access(db, current_user.id, file_key, "upload", request, inv.id)
```

### 3. 🟡 File Validation (Good, Could Be Enhanced)

**Status:** ADEQUATE - Basic validation present, advanced checks optional

**Current Implementation:**
- Extension validation (`.pdf`, `.csv`)
- Size validation (50MB limit)
- Optional MIME type validation via python-magic
- Empty file rejection

**Recommendations for Financial Documents:**
1. **Install python-magic** (currently optional):
   ```bash
   pip install python-magic python-magic-bin
   ```
   - Provides magic bytes validation (more secure than extension checking)
   - Prevents file type spoofing attacks

2. **Add PDF Structure Validation:**
   ```python
   # Add to validators.py
   import PyPDF2
   
   async def validate_pdf_structure(file_content: bytes) -> None:
       """Ensure PDF is valid and not corrupted"""
       try:
           pdf = PyPDF2.PdfReader(io.BytesIO(file_content))
           if len(pdf.pages) == 0:
               raise HTTPException(400, "PDF has no pages")
           if len(pdf.pages) > 100:  # Reasonable limit for invoices
               raise HTTPException(400, "PDF too large (>100 pages)")
       except Exception as e:
           raise HTTPException(400, f"Invalid PDF file: {str(e)}")
   ```

3. **Add Virus Scanning (Recommended for Production):**
   - Use ClamAV or cloud-based solution (AWS GuardDuty, Azure Defender)
   - Scan files before storage
   - Reject malicious files

4. **Content Security Checks:**
   ```python
   # Reject PDFs with embedded JavaScript or forms (potential XSS)
   def check_pdf_safety(pdf_content: bytes) -> bool:
       pdf = PyPDF2.PdfReader(io.BytesIO(pdf_content))
       # Check for JavaScript, embedded files, forms
       return True  # Safe
   ```

### 4. 🔴 Storage Backend Configuration (CRITICAL ISSUE)

**Current Status:** LOCAL STORAGE CONFIGURED IN PRODUCTION

**render.yaml Line 92:**
```yaml
- key: STORAGE_BACKEND
  value: local  # ⚠️ WILL CAUSE DATA LOSS IN PRODUCTION
```

**What Happens with Local Storage on Render:**
```
Day 1: User uploads invoice.pdf → Saved to /backend/uploads/invoices/abc123.pdf
Day 2: You push code update → Render rebuilds container → FILE DELETED
Day 3: User tries to download invoice → 404 FILE NOT FOUND ❌
```

**Why This Happens:**
- Render uses **ephemeral containers** (stateless, immutable infrastructure)
- Each deployment creates a **new container** with fresh filesystem
- No persistent volumes for web services on Render
- Files in local storage are **container-specific** and lost on restart

**Business Impact:**
- 🔴 **Customer Data Loss:** Users lose access to their uploaded invoices
- 🔴 **Compliance Violation:** Financial documents must be retained
- 🔴 **Trust Damage:** Customers expect permanent document storage
- 🔴 **Support Burden:** "Where did my invoices go?" tickets after every deploy

### 5. 📊 What Files Are Affected?

**Analysis of Upload Endpoints:**

| Endpoint | File Type | Storage Method | Risk |
|----------|-----------|----------------|------|
| `POST /upload` | CSV | ❌ Not stored (in-memory only) | ✅ Safe |
| `POST /upload_pdf` | PDF | ❌ Not stored (in-memory OCR) | ✅ Safe |
| `POST /ocr/extract` | PDF | ❌ Not stored (in-memory) | ✅ Safe |
| `POST /invoice/upload_file` | PDF | ✅ **Stored to cloud** | 🔴 **At Risk** |
| `POST /invoice/upload_file_auto` | PDF | ✅ **Stored to cloud** | 🔴 **At Risk** |
| `POST /invoice/upload_file_direct` | PDF | ✅ **Stored to cloud** | 🔴 **At Risk** |

**Summary:**
- ✅ **Bank statements:** Processed in-memory, extracted data saved to DB, original file discarded ✅
- 🔴 **Invoice PDFs:** Permanently stored for later retrieval, subject to data loss with local storage

### 6. 💰 Cloud Storage Cost Analysis

**Estimated Costs for 100 Active Users:**

#### AWS S3 (Recommended)
```
Assumptions:
- 100 users
- 20 invoices/user/month = 2,000 invoices/month
- Average invoice size: 500KB
- Storage: 2,000 × 0.5MB = 1GB/month cumulative
- Downloads: 5 per invoice = 10,000 requests/month

Monthly Costs:
- Storage (1GB standard): $0.023/GB = $0.02
- PUT requests (2,000): $0.005/1000 = $0.01
- GET requests (10,000): $0.0004/1000 = $0.004
- Data transfer (5GB out): $0.09/GB = $0.45

Total: ~$0.50/month for first month
Year 1 (12GB): ~$2-3/month
```

**Cheapest Option:** AWS S3 Standard
- First 50TB: $0.023/GB/month
- 1M GET requests: $0.40
- 10K PUT requests: $0.05

**Alternative Options:**
- **Azure Blob:** Similar pricing (~$0.018/GB)
- **Google Cloud Storage:** Similar pricing (~$0.020/GB)
- **Cloudflare R2:** $0/GB for first 10GB, no egress fees

**Recommendation:** Start with AWS S3, migrate to Cloudflare R2 if costs become significant

---

## Production-Ready Solution

### ✅ Immediate Actions Required (Before Launch)

#### 1. Create AWS S3 Bucket

```bash
# Using AWS CLI
aws s3 mb s3://statementbur-invoices-prod --region us-west-2

# Enable versioning (optional, for backup)
aws s3api put-bucket-versioning \
  --bucket statementbur-invoices-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket statementbur-invoices-prod \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Block public access (critical for security)
aws s3api put-public-access-block \
  --bucket statementbur-invoices-prod \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

#### 2. Create IAM User with Minimal Permissions

**Policy (save as `s3-invoice-storage-policy.json`):**
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

**Create User:**
```bash
# Create IAM user
aws iam create-user --user-name statementbur-s3-access

# Attach policy
aws iam put-user-policy \
  --user-name statementbur-s3-access \
  --policy-name S3InvoiceAccess \
  --policy-document file://s3-invoice-storage-policy.json

# Create access keys
aws iam create-access-key --user-name statementbur-s3-access
# ⚠️ SAVE THE OUTPUT - You'll need the AccessKeyId and SecretAccessKey
```

#### 3. Update Render.com Environment Variables

**In Render Dashboard → Environment:**
```yaml
# Storage Backend
STORAGE_BACKEND=s3

# AWS S3 Configuration
S3_BUCKET_NAME=statementbur-invoices-prod
S3_REGION=us-west-2
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE  # From step 2
S3_SECRET_KEY=wJalrXUt...EXAMPLEKEY  # From step 2
SIGNED_URL_EXPIRATION_SECONDS=3600

# Optional: Set shorter expiration for security
# SIGNED_URL_EXPIRATION_SECONDS=1800  # 30 minutes
```

**Update render.yaml:**
```yaml
# Storage Backend (Update for cloud storage)
- key: STORAGE_BACKEND
  value: s3  # Changed from 'local'

- key: S3_BUCKET_NAME
  value: statementbur-invoices-prod

- key: S3_REGION
  value: us-west-2

- key: S3_ACCESS_KEY
  sync: false  # Set via Render dashboard (secret)

- key: S3_SECRET_KEY
  sync: false  # Set via Render dashboard (secret)
```

#### 4. Update requirements.txt

**Add boto3 (if not already present):**
```bash
# Check if boto3 is in requirements.txt
grep boto3 backend/requirements.txt

# If not present, add it:
echo "boto3>=1.34.0" >> backend/requirements.txt
```

#### 5. Deploy and Test

```bash
# Commit changes
git add render.yaml
git commit -m "Configure S3 storage for production"
git push

# After deployment, test file upload
curl -X POST "https://statementbur-api.onrender.com/invoice/upload_file_auto?session_id=test123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test-invoice.pdf"

# Verify file is in S3
aws s3 ls s3://statementbur-invoices-prod/invoices/
```

---

## Security Best Practices Implemented ✅

### 1. Authentication & Authorization
- ✅ All upload endpoints require JWT authentication
- ✅ Multi-tenant isolation via `ensure_session_access()`
- ✅ Users can only access their own organization's files

### 2. File Validation
- ✅ File type restrictions (PDF-only for invoices)
- ✅ Size limits (50MB configurable)
- ✅ Extension validation
- ✅ Optional MIME type validation
- ✅ Empty file rejection

### 3. Secure Storage
- ✅ Pre-signed URLs with expiration (1 hour default)
- ✅ Server-side encryption on S3 (AES256)
- ✅ No direct file access - all through API
- ✅ Unique file keys prevent filename conflicts

### 4. Audit Trail
- ✅ Complete file access logging (upload, download, delete)
- ✅ User ID, timestamp, IP address tracked
- ✅ Database-backed audit log (`FileAccessLog` model)

### 5. Rate Limiting
- ✅ Upload limits: 10/minute, 100/hour per user
- ✅ Prevents abuse and DoS attacks

---

## Additional Security Recommendations

### 1. Content Security Policy for File Downloads

**Add to file download endpoints:**
```python
@app.get("/invoice/download/{invoice_id}")
async def download_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... existing validation ...
    
    # Generate signed URL with strict headers
    url = storage.generate_signed_url(invoice.file_reference, expiration_seconds=300)
    
    return {
        "url": url,
        "filename": invoice.supplier_name,
        "content_type": "application/pdf",
        "expires_in": 300,
        # Add Content-Disposition header hint for client
        "download_hint": f"attachment; filename=\"{invoice.supplier_name}_invoice.pdf\""
    }
```

### 2. File Retention Policy

**Implement automatic cleanup:**
```python
# Add to background jobs (Celery)
@celery_app.task
def cleanup_old_invoices():
    """Delete invoices older than 7 years (compliance requirement)"""
    cutoff_date = datetime.now() - timedelta(days=7*365)
    old_invoices = db.query(Invoice).filter(Invoice.created_at < cutoff_date).all()
    
    for invoice in old_invoices:
        if invoice.file_reference:
            storage = get_storage()
            storage.delete_file(invoice.file_reference)
            log_file_access(db, None, invoice.file_reference, "auto_delete", None)
        db.delete(invoice)
    
    db.commit()
```

### 3. Virus Scanning Integration

**AWS GuardDuty or ClamAV:**
```python
async def scan_file_for_malware(file_content: bytes) -> bool:
    """Scan uploaded file for malware before storage"""
    # Option 1: AWS GuardDuty (serverless)
    # Option 2: ClamAV (self-hosted)
    # Option 3: VirusTotal API
    
    # For now, implement basic checks:
    suspicious_patterns = [
        b'<script',  # JavaScript in PDF
        b'/JavaScript',  # PDF JavaScript
        b'/JS',  # PDF JS
        b'/Launch',  # PDF launch external
    ]
    
    for pattern in suspicious_patterns:
        if pattern in file_content:
            logger.warning(f"Suspicious content detected in uploaded file")
            return False
    
    return True
```

### 4. Disaster Recovery

**S3 Bucket Lifecycle Policy:**
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldInvoices",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER_IR"
        }
      ],
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "GLACIER_IR"
        }
      ]
    }
  ]
}
```

**Enable Cross-Region Replication:**
```bash
# Create backup bucket in different region
aws s3 mb s3://statementbur-invoices-backup --region eu-west-1

# Enable replication (requires versioning)
aws s3api put-bucket-replication \
  --bucket statementbur-invoices-prod \
  --replication-configuration file://replication-config.json
```

---

## Migration Checklist

### Pre-Launch (Before First Customer)
- [ ] Create AWS S3 bucket with encryption
- [ ] Create IAM user with minimal permissions
- [ ] Update Render environment variables
- [ ] Deploy with `STORAGE_BACKEND=s3`
- [ ] Test file upload/download workflow
- [ ] Verify files persist across redeploy
- [ ] Test pre-signed URL generation
- [ ] Verify audit logs are working

### Post-Launch (If Already on Local Storage)
- [ ] Create S3 bucket
- [ ] **Migrate existing files** from database to S3:
  ```python
  # Migration script
  from models import Invoice
  from services.storage import get_storage
  
  storage = get_storage()
  invoices = db.query(Invoice).filter(Invoice.file_reference.isnot(None)).all()
  
  for invoice in invoices:
      # Read from local storage
      local_path = f"backend/uploads/{invoice.file_reference}"
      if os.path.exists(local_path):
          with open(local_path, 'rb') as f:
              content = f.read()
          
          # Upload to S3
          storage.upload_file(content, invoice.file_reference, "application/pdf")
          print(f"Migrated: {invoice.file_reference}")
  ```
- [ ] Update `STORAGE_BACKEND=s3` in production
- [ ] Deploy
- [ ] Verify all existing files accessible
- [ ] Monitor for download errors (24-48 hours)
- [ ] Clean up local files (after confirmation)

### Ongoing Maintenance
- [ ] Monitor S3 costs monthly
- [ ] Review audit logs quarterly
- [ ] Test disaster recovery annually
- [ ] Update IAM credentials annually
- [ ] Review file retention policy quarterly

---

## Cost Optimization Tips

### 1. Use S3 Intelligent-Tiering
```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket statementbur-invoices-prod \
  --id AutoArchive \
  --intelligent-tiering-configuration file://tiering-config.json
```

**tiering-config.json:**
```json
{
  "Id": "AutoArchive",
  "Status": "Enabled",
  "Tierings": [
    {
      "Days": 90,
      "AccessTier": "ARCHIVE_ACCESS"
    },
    {
      "Days": 180,
      "AccessTier": "DEEP_ARCHIVE_ACCESS"
    }
  ]
}
```

### 2. CloudFront CDN (If High Download Volume)
```yaml
# Add CloudFront distribution for S3
# Benefits:
# - Faster downloads (edge locations)
# - Reduced S3 data transfer costs
# - DDoS protection
```

### 3. Compress PDFs Before Upload
```python
# Use ghostscript or similar to compress PDFs
def compress_pdf(pdf_content: bytes) -> bytes:
    """Compress PDF to reduce storage costs"""
    # Implementation depends on requirements
    # Trade-off: smaller files vs. lower quality
    return compressed_content
```

---

## Compliance Considerations

### GDPR / Data Privacy
- ✅ Users can delete their own data (implemented)
- ✅ Audit trail for all file access
- ⚠️ Add data export functionality
- ⚠️ Implement "right to be forgotten" for files

### Financial Document Retention
- Most jurisdictions: 7 years retention for financial docs
- Implement lifecycle policy to auto-delete after 7 years
- Archive to Glacier after 1 year for cost savings

### SOC 2 / ISO 27001
- ✅ Encryption at rest (S3 AES256)
- ✅ Encryption in transit (HTTPS)
- ✅ Access logging and audit trail
- ✅ Least privilege access (IAM policies)
- ⚠️ Add MFA for admin access
- ⚠️ Implement automated security scanning

---

## Summary

### Current State
- ✅ **Architecture:** Excellent - production-ready storage abstraction
- ✅ **Security:** Strong - authentication, validation, audit logging
- 🔴 **Configuration:** CRITICAL ISSUE - local storage will cause data loss
- ✅ **Code Quality:** High - clean, maintainable, well-documented

### Action Required
**BEFORE PRODUCTION LAUNCH:** Switch to AWS S3 storage to prevent invoice data loss

### Estimated Time to Fix
- **Setup S3 bucket:** 15 minutes
- **Configure credentials:** 10 minutes
- **Update Render config:** 5 minutes
- **Deploy and test:** 15 minutes
- **Total:** ~1 hour

### Cost Impact
- **AWS S3:** ~$0.50/month initially, ~$2-3/month at 100 users
- **Negligible cost** compared to risk of data loss

### Risk Assessment
- **Without S3:** 🔴 HIGH - Guaranteed data loss on every redeploy
- **With S3:** ✅ LOW - Production-ready, scalable, secure

---

## Questions or Support

This audit finds your codebase is **ready for production** from a security and architecture perspective. The **only blocker** is switching from local storage to S3, which is a **simple configuration change**.

**Contact:** Security team for IAM credential management
