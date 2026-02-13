#!/bin/bash
# AWS S3 Storage Setup Script for Statement Analyzer
# Run this to set up production file storage

set -e  # Exit on error

echo "=========================================="
echo "AWS S3 Storage Setup"
echo "=========================================="
echo ""

# Configuration
BUCKET_NAME="statementbur-invoices-prod"
REGION="us-west-2"
IAM_USER="statementbur-s3-access"
POLICY_NAME="S3InvoiceStoragePolicy"

echo "Configuration:"
echo "  Bucket Name: $BUCKET_NAME"
echo "  Region: $REGION"
echo "  IAM User: $IAM_USER"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"
echo ""

# Step 1: Create S3 bucket
echo "Step 1: Creating S3 bucket..."
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
    echo "✅ Bucket created: $BUCKET_NAME"
else
    echo "⚠️  Bucket already exists, skipping..."
fi
echo ""

# Step 2: Enable versioning
echo "Step 2: Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled
echo "✅ Versioning enabled"
echo ""

# Step 3: Enable encryption
echo "Step 3: Enabling encryption..."
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
echo "✅ Encryption enabled (AES256)"
echo ""

# Step 4: Block public access
echo "Step 4: Blocking public access..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "✅ Public access blocked"
echo ""

# Step 5: Create IAM policy
echo "Step 5: Creating IAM policy..."
cat > /tmp/s3-policy.json <<EOF
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
EOF
echo "✅ Policy created at /tmp/s3-policy.json"
echo ""

# Step 6: Create IAM user (if doesn't exist)
echo "Step 6: Creating IAM user..."
if aws iam get-user --user-name "$IAM_USER" &> /dev/null; then
    echo "⚠️  User already exists, skipping..."
else
    aws iam create-user --user-name "$IAM_USER"
    echo "✅ User created: $IAM_USER"
fi
echo ""

# Step 7: Attach policy to user
echo "Step 7: Attaching policy to user..."
aws iam put-user-policy \
    --user-name "$IAM_USER" \
    --policy-name "$POLICY_NAME" \
    --policy-document file:///tmp/s3-policy.json
echo "✅ Policy attached"
echo ""

# Step 8: Create access keys
echo "Step 8: Creating access keys..."
echo "⚠️  IMPORTANT: Save these credentials securely!"
echo ""

ACCESS_KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER" 2>&1)

if echo "$ACCESS_KEY_OUTPUT" | grep -q "LimitExceeded"; then
    echo "⚠️  User already has 2 access keys (AWS limit)."
    echo "    You need to delete an old key first:"
    echo ""
    echo "    aws iam list-access-keys --user-name $IAM_USER"
    echo "    aws iam delete-access-key --user-name $IAM_USER --access-key-id OLD_KEY_ID"
    echo ""
    echo "    Then run this script again."
    exit 1
fi

echo "$ACCESS_KEY_OUTPUT" | jq '.'

# Extract credentials
ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Copy these values to Render.com:"
echo ""
echo "S3_BUCKET_NAME=$BUCKET_NAME"
echo "S3_REGION=$REGION"
echo "S3_ACCESS_KEY=$ACCESS_KEY_ID"
echo "S3_SECRET_KEY=$SECRET_ACCESS_KEY"
echo ""
echo "Next steps:"
echo "1. Go to Render.com → Your Service → Environment"
echo "2. Set STORAGE_BACKEND=s3"
echo "3. Add the 4 variables above"
echo "4. Deploy your application"
echo ""
echo "⚠️  Save these credentials in a password manager!"
echo "⚠️  Never commit them to git!"
echo ""
