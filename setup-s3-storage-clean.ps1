# AWS S3 Storage Setup Script for Statement Analyzer (PowerShell)
# Run this to set up production file storage

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AWS S3 Storage Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Use full path to AWS CLI to avoid PATH issues
$AWS_CLI = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

# Configuration
$BUCKET_NAME = "statementbur-invoices-prod"
$REGION = "us-west-2"
$IAM_USER = "statementbur-s3-access"
$POLICY_NAME = "S3InvoiceStoragePolicy"

Write-Host "Configuration:"
Write-Host "  Bucket Name: $BUCKET_NAME"
Write-Host "  Region: $REGION"
Write-Host "  IAM User: $IAM_USER"
Write-Host ""

# Check if AWS CLI is installed
try {
    $null = & $AWS_CLI --version
    Write-Host "AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "AWS CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "   https://aws.amazon.com/cli/" -ForegroundColor Yellow
    exit 1
}

# Check if AWS credentials are configured
try {
    $null = & $AWS_CLI sts get-caller-identity 2>&1
    Write-Host "AWS credentials configured" -ForegroundColor Green
} catch {
    Write-Host "AWS credentials not configured. Run: aws configure" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 1: Create S3 bucket
Write-Host "Step 1: Creating S3 bucket..." -ForegroundColor Yellow
try {
    $bucketExists = & $AWS_CLI s3 ls "s3://$BUCKET_NAME" 2>&1
    if ($LASTEXITCODE -ne 0) {
        & $AWS_CLI s3 mb "s3://$BUCKET_NAME" --region $REGION
        Write-Host "Bucket created: $BUCKET_NAME" -ForegroundColor Green
    } else {
        Write-Host "Bucket already exists, skipping..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Bucket already exists or error occurred" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Enable versioning
Write-Host "Step 2: Enabling versioning..." -ForegroundColor Yellow
& $AWS_CLI s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled
Write-Host "Versioning enabled" -ForegroundColor Green
Write-Host ""

# Step 3: Enable encryption
Write-Host "Step 3: Enabling encryption..." -ForegroundColor Yellow
$encryptionConfig = '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
& $AWS_CLI s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration $encryptionConfig
Write-Host "Encryption enabled (AES256)" -ForegroundColor Green
Write-Host ""

# Step 4: Block public access
Write-Host "Step 4: Blocking public access..." -ForegroundColor Yellow
& $AWS_CLI s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
Write-Host "Public access blocked" -ForegroundColor Green
Write-Host ""

# Step 5: Create IAM policy
Write-Host "Step 5: Creating IAM policy..." -ForegroundColor Yellow
$policyJson = @"
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
        "arn:aws:s3:::$BUCKET_NAME",
        "arn:aws:s3:::$BUCKET_NAME/*"
      ]
    }
  ]
}
"@
$policyPath = "$env:TEMP\s3-policy.json"
$policyJson | Out-File -FilePath $policyPath -Encoding utf8
Write-Host "Policy created at $policyPath" -ForegroundColor Green
Write-Host ""

# Step 6: Create IAM user (if doesn't exist)
Write-Host "Step 6: Creating IAM user..." -ForegroundColor Yellow
try {
    $null = & $AWS_CLI iam get-user --user-name $IAM_USER 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "User already exists, skipping..." -ForegroundColor Yellow
    }
} catch {
    & $AWS_CLI iam create-user --user-name $IAM_USER
    Write-Host "User created: $IAM_USER" -ForegroundColor Green
}
Write-Host ""

# Step 7: Attach policy to user
Write-Host "Step 7: Attaching policy to user..." -ForegroundColor Yellow
& $AWS_CLI iam put-user-policy --user-name $IAM_USER --policy-name $POLICY_NAME --policy-document "file://$policyPath"
Write-Host "Policy attached" -ForegroundColor Green
Write-Host ""

# Step 8: Create access keys
Write-Host "Step 8: Creating access keys..." -ForegroundColor Yellow
Write-Host "IMPORTANT: Save these credentials securely!" -ForegroundColor Red
Write-Host ""

$accessKeyOutput = & $AWS_CLI iam create-access-key --user-name $IAM_USER 2>&1 | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not create access key. You may already have 2 keys (AWS limit)." -ForegroundColor Red
    Write-Host "    List existing keys:" -ForegroundColor Yellow
    Write-Host "    aws iam list-access-keys --user-name $IAM_USER" -ForegroundColor White
    Write-Host ""
    Write-Host "    Delete an old key:" -ForegroundColor Yellow
    Write-Host "    aws iam delete-access-key --user-name $IAM_USER --access-key-id OLD_KEY_ID" -ForegroundColor White
    Write-Host ""
    exit 1
}

$ACCESS_KEY_ID = $accessKeyOutput.AccessKey.AccessKeyId
$SECRET_ACCESS_KEY = $accessKeyOutput.AccessKey.SecretAccessKey

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Copy these values to Render.com:" -ForegroundColor Yellow
Write-Host ""
Write-Host "STORAGE_BACKEND=s3" -ForegroundColor White
Write-Host "S3_BUCKET_NAME=$BUCKET_NAME" -ForegroundColor White
Write-Host "S3_REGION=$REGION" -ForegroundColor White
Write-Host "S3_ACCESS_KEY=$ACCESS_KEY_ID" -ForegroundColor White
Write-Host "S3_SECRET_KEY=$SECRET_ACCESS_KEY" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.render.com" -ForegroundColor White
Write-Host "2. Select your statementbur-api service" -ForegroundColor White
Write-Host "3. Go to Environment tab" -ForegroundColor White
Write-Host "4. Update STORAGE_BACKEND to s3" -ForegroundColor White
Write-Host "5. Add the 4 S3 variables above" -ForegroundColor White
Write-Host "6. Save changes (will trigger auto-deploy)" -ForegroundColor White
Write-Host ""
Write-Host "Save these credentials in a password manager!" -ForegroundColor Red
Write-Host "Never commit them to git!" -ForegroundColor Red
Write-Host ""

# Save credentials to a file for reference
$credentialsFile = "aws-s3-credentials.txt"
$credContent = "AWS S3 Storage Credentials`n"
$credContent += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n`n"
$credContent += "STORAGE_BACKEND=s3`n"
$credContent += "S3_BUCKET_NAME=$BUCKET_NAME`n"
$credContent += "S3_REGION=$REGION`n"
$credContent += "S3_ACCESS_KEY=$ACCESS_KEY_ID`n"
$credContent += "S3_SECRET_KEY=$SECRET_ACCESS_KEY`n`n"
$credContent += "WARNING: DELETE THIS FILE AFTER ADDING TO RENDER.COM`n"
$credContent += "WARNING: NEVER COMMIT THIS TO GIT"
$credContent | Out-File -FilePath $credentialsFile -Encoding utf8

Write-Host "Credentials saved to: $credentialsFile" -ForegroundColor Green
Write-Host "DELETE this file after adding to Render!" -ForegroundColor Red
Write-Host ""
