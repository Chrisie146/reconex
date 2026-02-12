# Cloud File Storage Guide

## Overview

The Bank Statement Analyzer now uses a **cloud storage abstraction layer** for secure file management. This enables:

- ✅ **Multi-cloud support**: AWS S3, Azure Blob Storage, Google Cloud Storage
- ✅ **Secure access**: Time-limited signed URLs for downloads
- ✅ **Audit logging**: Complete file access trail for compliance
- ✅ **No local paths**: Files stored in cloud, accessed via pre-signed URLs
- ✅ **Scalability**: Horizontal scaling without shared filesystem
- ✅ **Development mode**: Local storage for testing

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Application                        │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         Storage Abstraction Layer                        │ │
│  │  (services/storage.py - StorageFactory)                 │ │
│  └────────────┬────────────┬────────────┬────────────┬─────┘ │
│               │            │            │            │       │
│  ┌────────────▼───┐  ┌────▼────┐  ┌───▼────┐  ┌───▼────┐  │
│  │  LocalStorage  │  │   S3    │  │ Azure  │  │  GCS   │  │
│  └────────────────┘  └─────────┘  └────────┘  └────────┘  │
└───────────┬────────────────┬──────────┬──────────┬─────────┘
            │                │          │          │
    ┌───────▼───────┐ ┌─────▼──────┐ ┌▼──────┐ ┌─▼────────┐
    │ Local Disk    │ │ AWS S3     │ │ Azure │ │ GCS      │
    │ (dev only)    │ │ Bucket     │ │ Blob  │ │ Bucket   │
    └───────────────┘ └────────────┘ └───────┘ └──────────┘
```

---

## Configuration

### 1. Environment Variables

Copy `.env.example` to `.env` and configure your storage backend:

```bash
# Storage backend selection
STORAGE_BACKEND=s3  # Options: local, s3, azure, gcs

# Signed URL expiration (seconds)
SIGNED_URL_EXPIRATION_SECONDS=3600  # 1 hour default
```

### 2. Provider-Specific Configuration

#### AWS S3

```bash
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Setup Steps:**
1. Create S3 bucket in AWS Console
2. Create IAM user with S3 permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name",
           "arn:aws:s3:::your-bucket-name/*"
         ]
       }
     ]
   }
   ```
3. Note access key and secret key
4. Configure bucket CORS for web uploads (optional)

#### Azure Blob Storage

```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=youraccountname;AccountKey=yourkey;EndpointSuffix=core.windows.net
AZURE_CONTAINER_NAME=invoices
```

**Setup Steps:**
1. Create Storage Account in Azure Portal
2. Create container named "invoices"
3. Get connection string from Access Keys section
4. Configure CORS rules if needed

#### Google Cloud Storage

```bash
GCS_BUCKET_NAME=your-bucket-name
GCS_CREDENTIALS_PATH=/path/to/service-account-key.json
GCS_PROJECT_ID=your-project-id
```

**Setup Steps:**
1. Create GCS bucket in Google Cloud Console
2. Create service account with Storage Object Admin role
3. Generate JSON key file
4. Place key file in secure location
5. Set `GCS_CREDENTIALS_PATH` to key file path

#### Local Storage (Development Only)

```bash
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./uploads
```

---

## Usage

### File Uploads

Upload endpoints automatically use the configured storage backend:

```python
POST /invoice/upload_file
POST /invoice/upload_file_auto
POST /invoice/upload_file_direct
```

**Example:**
```bash
curl -X POST "http://localhost:8000/invoice/upload_file_auto?session_id=abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@invoice.pdf"
```

Files are:
1. Validated (PDF only, size limits)
2. Uploaded to cloud storage with unique key: `invoices/{uuid}_{filename}`
3. Metadata saved to database (stores cloud key, not local path)
4. Access logged for audit trail

### File Downloads

Download endpoint generates secure, time-limited URLs:

```python
GET /invoice/download?invoice_id=123&session_id=abc
```

**For Cloud Storage** (S3/Azure/GCS):
```json
{
  "download_url": "https://bucket.s3.amazonaws.com/invoices/abc123_invoice.pdf?X-Amz-Signature=...",
  "expires_in_seconds": 3600
}
```

**For Local Storage** (Development):
Returns file directly via `FileResponse`

### Audit Logging

All file access is logged to `file_access_logs` table:

```sql
SELECT * FROM file_access_logs 
WHERE user_id = 1 
ORDER BY created_at DESC;
```

**Logged Actions:**
- `upload` - File uploaded
- `generate_url` - Download URL generated
- `delete` - File deleted

**Logged Details:**
- User ID
- Invoice ID (if applicable)
- File key (cloud storage path)
- Action type
- IP address
- User agent
- Storage backend used
- Timestamp

---

## API Reference

### Storage Backend Interface

All storage backends implement the `StorageBackend` abstract class:

```python
from services.storage import get_storage

# Get configured storage
storage = get_storage()

# Upload file
file_key = storage.upload_file(
    file_content=bytes_data,
    object_key="invoices/unique_filename.pdf",
    content_type="application/pdf"
)

# Download file
content = storage.download_file(object_key="invoices/file.pdf")

# Generate signed URL (1 hour expiration)
url = storage.generate_signed_url(
    object_key="invoices/file.pdf",
    expiration_seconds=3600
)

# Check if file exists
exists = storage.file_exists(object_key="invoices/file.pdf")

# Get file metadata
metadata = storage.get_file_metadata(object_key="invoices/file.pdf")
# Returns: {'size': 12345, 'last_modified': datetime, 'content_type': 'application/pdf'}

# Delete file
success = storage.delete_file(object_key="invoices/file.pdf")
```

---

## Migration from Local Storage

If you're upgrading from local file storage to cloud storage:

### Step 1: Backup Existing Files

```bash
# Create backup of uploads directory
cp -r backend/uploads backend/uploads_backup
```

### Step 2: Upload to Cloud

For AWS S3:
```bash
aws s3 sync backend/uploads/ s3://your-bucket-name/invoices/ --recursive
```

For Azure:
```bash
az storage blob upload-batch --source backend/uploads --destination invoices --account-name youraccountname
```

For GCS:
```bash
gsutil -m cp -r backend/uploads/* gs://your-bucket-name/invoices/
```

### Step 3: Update Database File References

Run migration to update `file_reference` column from local paths to cloud keys:

```python
# Example: Convert absolute paths to relative keys
UPDATE invoices
SET file_reference = REPLACE(file_reference, 'C:\\path\\to\\backend\\uploads\\', 'invoices/')
WHERE file_reference LIKE 'C:\\path\\to\\backend\\uploads\\%';
```

### Step 4: Update Configuration

```bash
# Change from local to cloud
STORAGE_BACKEND=s3  # or azure, gcs
```

### Step 5: Test Access

```bash
# Test file download
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/invoice/download?invoice_id=1&session_id=abc"
```

---

## Security Best Practices

### 1. Bucket/Container Permissions

**Principle: Restrict public access**

❌ **Bad:** Public read access on bucket
✅ **Good:** Private bucket with signed URLs

**AWS S3:**
- Enable "Block all public access"
- Use IAM roles for EC2/ECS (preferred over access keys)
- Rotate access keys regularly

**Azure Blob:**
- Set container access level to "Private"
- Use Managed Identity for Azure VMs
- Rotate storage account keys

**GCS:**
- Set bucket to "Fine-grained" access control
- Use service accounts with least privilege
- Rotate service account keys

### 2. Signed URL Expiration

Configure appropriate expiration times:

```bash
# Short expiration for sensitive documents
SIGNED_URL_EXPIRATION_SECONDS=300  # 5 minutes

# Medium expiration for general use
SIGNED_URL_EXPIRATION_SECONDS=3600  # 1 hour (default)

# Longer expiration for downloads
SIGNED_URL_EXPIRATION_SECONDS=86400  # 24 hours
```

### 3. Encryption

All providers offer encryption at rest (enabled by default):

- **AWS S3:** Server-side encryption (SSE-S3 or SSE-KMS)
- **Azure Blob:** Storage Service Encryption (SSE)
- **GCS:** Server-side encryption

Enable encryption in transit (HTTPS) - already configured.

### 4. File Access Audit

Review audit logs regularly:

```sql
-- Check recent file access
SELECT u.username, f.action, f.file_key, f.created_at, f.ip_address
FROM file_access_logs f
JOIN users u ON f.user_id = u.id
WHERE f.created_at > NOW() - INTERVAL '7 days'
ORDER BY f.created_at DESC;

-- Identify suspicious patterns
SELECT ip_address, COUNT(*) as access_count
FROM file_access_logs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
HAVING COUNT(*) > 100;
```

---

## Monitoring & Troubleshooting

### Health Checks

Test storage connectivity:

```python
from services.storage import get_storage

storage = get_storage()
test_key = "health-check.txt"

try:
    # Test write
    storage.upload_file(b"health check", test_key, "text/plain")
    
    # Test read
    content = storage.download_file(test_key)
    
    # Test delete
    storage.delete_file(test_key)
    
    print("✅ Storage backend healthy")
except Exception as e:
    print(f"❌ Storage backend error: {e}")
```

### Common Issues

#### Issue: "Failed to upload to S3: Access Denied"

**Solution:**
- Verify IAM permissions include `s3:PutObject`
- Check bucket policy doesn't deny uploads
- Verify credentials are correct

#### Issue: "GCS credentials not found"

**Solution:**
- Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Verify service account key file path
- Check key file has correct permissions (readable)

#### Issue: "Azure connection string invalid"

**Solution:**
- Verify connection string format
- Check for extra spaces or line breaks
- Regenerate connection string from Azure Portal

#### Issue: Download URL expired

**Solution:**
- Increase `SIGNED_URL_EXPIRATION_SECONDS`
- Generate new URL before expiration
- Implement auto-refresh in frontend

---

## Performance Optimization

### 1. Connection Pooling

Storage clients maintain connection pools automatically:

- **S3 (boto3):** Default pool size = 10
- **Azure:** Default pool size = 12
- **GCS:** Auto-managed by client library

### 2. Concurrent Uploads

For multiple file uploads, use async operations:

```python
import asyncio
from services.storage import get_storage

async def upload_multiple(files):
    storage = get_storage()
    tasks = [
        asyncio.to_thread(storage.upload_file, file.content, file.key)
        for file in files
    ]
    return await asyncio.gather(*tasks)
```

### 3. CDN Integration

For high-traffic applications, add CDN

:

**CloudFront (AWS S3):**
```bash
# Create CloudFront distribution pointing to S3 bucket
# Use signed URLs with CloudFront
```

**Azure CDN:**
```bash
# Create CDN profile and endpoint
# Point to Blob Storage container
```

**Cloud CDN (GCS):**
```bash
# Enable Cloud CDN on load balancer
# Configure backend bucket
```

---

## Cost Optimization

### Storage Costs

**AWS S3:**
- Standard: $0.023/GB/month
- Infrequent Access: $0.0125/GB/month (for old invoices)

**Azure Blob:**
- Hot tier: $0.0184/GB/month
- Cool tier: $0.01/GB/month (for old invoices)

**GCS:**
- Standard: $0.020/GB/month
- Nearline: $0.010/GB/month (for old invoices)

### Transfer Costs

- **Uploads:** Free for all providers
- **Downloads:**
  - AWS: $0.09/GB after first 1GB
  - Azure: $0.087/GB after first 5GB
  - GCS: $0.12/GB after first 1GB

### Lifecycle Policies

Auto-archive old files to reduce costs:

**AWS S3:**
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "Id": "ArchiveOldInvoices",
      "Filter": {"Prefix": "invoices/"},
      "Status": "Enabled",
      "Transitions": [{
        "Days": 365,
        "StorageClass": "STANDARD_IA"
      }]
    }]
  }'
```

**Azure:**
```bash
az storage account management-policy create \
  --account-name youraccountname \
  --policy @lifecycle-policy.json
```

---

## Testing

### Unit Tests

Test storage backends with mocks:

```python
import pytest
from unittest.mock import Mock, patch
from services.storage import get_storage, StorageFactory

def test_upload_to_s3():
    with patch('services.storage_s3.boto3.client') as mock_client:
        StorageFactory.reset()
        storage = get_storage()
        
        storage.upload_file(b"test", "test.pdf")
        
        mock_client.return_value.put_object.assert_called_once()

def test_signed_url_generation():
    storage = get_storage()
    url = storage.generate_signed_url("test.pdf", 3600)
    
    assert isinstance(url, str)
    assert len(url) > 0
```

### Integration Tests

Test with actual cloud storage (use test buckets):

```python
def test_s3_integration():
    # Requires: TEST_S3_BUCKET_NAME in environment
    storage = get_storage()
    test_key = f"test/{uuid.uuid4()}.txt"
    
    try:
        # Upload
        storage.upload_file(b"integration test", test_key, "text/plain")
        
        # Download
        content = storage.download_file(test_key)
        assert content == b"integration test"
        
        # Signed URL
        url = storage.generate_signed_url(test_key)
        response = requests.get(url)
        assert response.status_code == 200
        
    finally:
        # Cleanup
        storage.delete_file(test_key)
```

---

## Summary

✅ **Implemented:**
- Multi-cloud storage abstraction (S3, Azure, GCS, Local)
- Pre-signed URLs for secure, time-limited downloads
- File access audit logging
- Cloud storage configuration management

✅ **Phase 1 Complete:**
This completes the **Cloud File Storage** requirement, making Phase 1 (Critical Blockers) **100% complete (12/12)**.

🎉 **Production Ready:**
The application now supports scalable, secure file storage suitable for production deployment!

---

## Next Steps

1. **Choose cloud provider** based on your infrastructure
2. **Create storage bucket/container**
3. **Configure credentials** in `.env`
4. **Run database migration** to add audit log table
5. **Test file upload/download** with cloud storage
6. **Monitor audit logs** for security compliance
7. **Set lifecycle policies** for cost optimization

For questions or issues, refer to provider documentation:
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
