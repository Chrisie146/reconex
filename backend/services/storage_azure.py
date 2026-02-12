"""
Azure Blob Storage Backend

Production storage using Azure Blob Storage with:
- Secure file upload/download
- Shared Access Signature (SAS) URLs for time-limited access
- Automatic content-type detection
- Server-side encryption (enabled by default in Azure)
"""

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime, timedelta
from typing import Optional
from .storage import StorageBackend


class AzureBlobStorage(StorageBackend):
    """Azure Blob Storage implementation"""
    
    def __init__(self, connection_string: str, container_name: str):
        """
        Initialize Azure Blob Storage
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Blob container name
        """
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
        
        # Ensure container exists
        try:
            self.container_client.create_container()
        except Exception:
            # Container already exists
            pass
        
        # Extract account name and key for SAS generation
        conn_parts = dict(part.split('=', 1) for part in connection_string.split(';') if '=' in part)
        self.account_name = conn_parts.get('AccountName')
        self.account_key = conn_parts.get('AccountKey')
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> str:
        """Upload file to Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={
                    'content_type': content_type
                },
                metadata={
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            return object_key
        except Exception as e:
            raise Exception(f"Failed to upload to Azure Blob Storage: {e}")
    
    def download_file(self, object_key: str) -> bytes:
        """Download file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File not found in Azure Blob Storage: {object_key}")
        except Exception as e:
            raise Exception(f"Failed to download from Azure Blob Storage: {e}")
    
    def generate_signed_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """Generate a SAS URL for secure, time-limited access"""
        try:
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=object_key,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expiration_seconds)
            )
            
            # Construct full URL
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            
            return f"{blob_client.url}?{sas_token}"
        except Exception as e:
            raise Exception(f"Failed to generate SAS URL: {e}")
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            blob_client.delete_blob()
            return True
        except Exception:
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception:
            return False
    
    def get_file_metadata(self, object_key: str) -> dict:
        """Get file metadata from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=object_key
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                'size': properties.size,
                'last_modified': properties.last_modified,
                'content_type': properties.content_settings.content_type or 'application/octet-stream'
            }
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File not found in Azure Blob Storage: {object_key}")
        except Exception as e:
            raise Exception(f"Failed to get metadata from Azure Blob Storage: {e}")
