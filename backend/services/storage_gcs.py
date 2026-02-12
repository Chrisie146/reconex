"""
Google Cloud Storage Backend

Production storage using Google Cloud Storage with:
- Secure file upload/download
- Signed URLs for time-limited access
- Automatic content-type detection
- Server-side encryption (enabled by default in GCS)
"""

from google.cloud import storage
from google.auth import default as default_auth
from google.auth.exceptions import DefaultCredentialsError
from datetime import datetime, timedelta
from typing import Optional
from .storage import StorageBackend
import os


class GCSStorage(StorageBackend):
    """Google Cloud Storage implementation"""
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None, 
                 project_id: Optional[str] = None):
        """
        Initialize Google Cloud Storage
        
        Args:
            bucket_name: GCS bucket name
            credentials_path: Path to service account JSON file (optional, uses ADC if not provided)
            project_id: GCP project ID (optional, inferred from credentials)
        """
        self.bucket_name = bucket_name
        
        # Set credentials path if provided
        if credentials_path and os.path.exists(credentials_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Create storage client
        try:
            if project_id:
                self.storage_client = storage.Client(project=project_id)
            else:
                self.storage_client = storage.Client()
        except DefaultCredentialsError:
            raise Exception(
                "GCS credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or provide credentials_path"
            )
        
        # Get bucket
        try:
            self.bucket = self.storage_client.bucket(bucket_name)
            if not self.bucket.exists():
                raise Exception(f"GCS bucket '{bucket_name}' does not exist")
        except Exception as e:
            raise Exception(f"Failed to access GCS bucket: {e}")
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> str:
        """Upload file to Google Cloud Storage"""
        try:
            blob = self.bucket.blob(object_key)
            
            # Set metadata
            blob.metadata = {
                'uploaded_at': datetime.utcnow().isoformat()
            }
            
            # Upload with content type
            blob.upload_from_string(
                file_content,
                content_type=content_type
            )
            
            return object_key
        except Exception as e:
            raise Exception(f"Failed to upload to GCS: {e}")
    
    def download_file(self, object_key: str) -> bytes:
        """Download file from Google Cloud Storage"""
        try:
            blob = self.bucket.blob(object_key)
            
            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {object_key}")
            
            return blob.download_as_bytes()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to download from GCS: {e}")
    
    def generate_signed_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """Generate a signed URL for secure, time-limited access"""
        try:
            blob = self.bucket.blob(object_key)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration_seconds),
                method="GET"
            )
            
            return url
        except Exception as e:
            raise Exception(f"Failed to generate signed URL: {e}")
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from Google Cloud Storage"""
        try:
            blob = self.bucket.blob(object_key)
            blob.delete()
            return True
        except Exception:
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in Google Cloud Storage"""
        try:
            blob = self.bucket.blob(object_key)
            return blob.exists()
        except Exception:
            return False
    
    def get_file_metadata(self, object_key: str) -> dict:
        """Get file metadata from Google Cloud Storage"""
        try:
            blob = self.bucket.blob(object_key)
            
            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {object_key}")
            
            # Reload to get latest metadata
            blob.reload()
            
            return {
                'size': blob.size,
                'last_modified': blob.updated,
                'content_type': blob.content_type or 'application/octet-stream'
            }
        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get metadata from GCS: {e}")
