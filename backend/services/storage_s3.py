"""
AWS S3 Storage Backend

Production storage using Amazon S3 with:
- Secure file upload/download
- Pre-signed URLs for time-limited access
- Automatic content-type detection
- Server-side encryption
"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig
from datetime import datetime
from typing import Optional
from .storage import StorageBackend


class S3Storage(StorageBackend):
    """AWS S3 storage implementation"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1', 
                 access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        Initialize S3 storage
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region (default: us-east-1)
            access_key: AWS access key ID (optional, uses IAM role if not provided)
            secret_key: AWS secret access key (optional, uses IAM role if not provided)
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Configure boto3 with signature version 4 for signed URLs
        boto_config = BotoConfig(
            signature_version='s3v4',
            region_name=region
        )
        
        # Create S3 client
        if access_key and secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=boto_config
            )
        else:
            # Use IAM role credentials (recommended for EC2/ECS)
            self.s3_client = boto3.client('s3', config=boto_config)
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> str:
        """Upload file to S3 with server-side encryption"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=content_type,
                ServerSideEncryption='AES256',  # Server-side encryption
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            return object_key
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")
    
    def download_file(self, object_key: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {object_key}")
            raise Exception(f"Failed to download from S3: {e}")
    
    def generate_signed_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """Generate a pre-signed URL for secure, time-limited access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration_seconds
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate signed URL: {e}")
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, object_key: str) -> dict:
        """Get file metadata from S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', 'application/octet-stream')
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found in S3: {object_key}")
            raise Exception(f"Failed to get metadata from S3: {e}")
