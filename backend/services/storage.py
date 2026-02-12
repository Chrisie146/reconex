"""
Storage Abstraction Layer for Cloud File Storage

Provides a unified interface for file storage across different cloud providers:
- AWS S3
- Azure Blob Storage
- Google Cloud Storage
- Local filesystem (development only)

Supports:
- File upload/download
- Pre-signed URL generation for secure, time-limited access
- File deletion
- File existence checks
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from datetime import datetime


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> str:
        """
        Upload a file to storage
        
        Args:
            file_content: Raw bytes of the file
            object_key: Unique identifier/path for the file (e.g., "invoices/uuid_filename.pdf")
            content_type: MIME type of the file
            
        Returns:
            object_key: The key/path where the file was stored
        """
        pass
    
    @abstractmethod
    def download_file(self, object_key: str) -> bytes:
        """
        Download a file from storage
        
        Args:
            object_key: The key/path of the file
            
        Returns:
            File content as bytes
        """
        pass
    
    @abstractmethod
    def generate_signed_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """
        Generate a pre-signed URL for secure, time-limited access to a file
        
        Args:
            object_key: The key/path of the file
            expiration_seconds: How long the URL should be valid (default: 1 hour)
            
        Returns:
            Pre-signed URL as string
        """
        pass
    
    @abstractmethod
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            object_key: The key/path of the file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in storage
        
        Args:
            object_key: The key/path of the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_metadata(self, object_key: str) -> dict:
        """
        Get metadata about a file
        
        Args:
            object_key: The key/path of the file
            
        Returns:
            Dictionary with keys: size (bytes), last_modified (datetime), content_type
        """
        pass


class StorageFactory:
    """Factory for creating storage backend instances"""
    
    _instance = None
    
    @classmethod
    def get_storage(cls, config=None) -> StorageBackend:
        """
        Get a storage backend instance (singleton pattern)
        
        Args:
            config: Configuration dict or Config object with storage settings
            
        Returns:
            StorageBackend instance configured based on STORAGE_BACKEND setting
        """
        if cls._instance is None:
            if config is None:
                from config import Config
                config = Config
            
            backend_type = getattr(config, 'STORAGE_BACKEND', 'local').lower()
            
            if backend_type == 's3':
                from .storage_s3 import S3Storage
                cls._instance = S3Storage(
                    bucket_name=config.S3_BUCKET_NAME,
                    region=config.S3_REGION,
                    access_key=config.S3_ACCESS_KEY,
                    secret_key=config.S3_SECRET_KEY
                )
            elif backend_type == 'azure':
                from .storage_azure import AzureBlobStorage
                cls._instance = AzureBlobStorage(
                    connection_string=config.AZURE_STORAGE_CONNECTION_STRING,
                    container_name=config.AZURE_CONTAINER_NAME
                )
            elif backend_type == 'gcs':
                from .storage_gcs import GCSStorage
                cls._instance = GCSStorage(
                    bucket_name=config.GCS_BUCKET_NAME,
                    credentials_path=config.GCS_CREDENTIALS_PATH,
                    project_id=config.GCS_PROJECT_ID
                )
            elif backend_type == 'local':
                from .storage_local import LocalStorage
                cls._instance = LocalStorage(
                    base_path=config.LOCAL_STORAGE_PATH
                )
            else:
                raise ValueError(f"Unknown storage backend: {backend_type}. Supported: s3, azure, gcs, local")
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)"""
        cls._instance = None


# Convenience function for getting storage
def get_storage() -> StorageBackend:
    """Get the configured storage backend"""
    return StorageFactory.get_storage()
