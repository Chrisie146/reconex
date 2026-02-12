"""
Local Filesystem Storage Backend

For development and testing only. Not recommended for production.
Stores files on the local filesystem and generates file:// URLs.
"""

import os
import shutil
from datetime import datetime
from typing import Optional
from .storage import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage implementation"""
    
    def __init__(self, base_path: str = None):
        """
        Initialize local storage
        
        Args:
            base_path: Base directory for file storage (default: backend/uploads)
        """
        if base_path is None:
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> str:
        """Upload file to local filesystem"""
        # Ensure subdirectories exist
        full_path = os.path.join(self.base_path, object_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'wb') as f:
            f.write(file_content)
        
        return object_key
    
    def download_file(self, object_key: str) -> bytes:
        """Download file from local filesystem"""
        full_path = os.path.join(self.base_path, object_key)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {object_key}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def generate_signed_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """
        Generate a file:// URL for local files
        
        Note: In development, this returns a path that can be used with FileResponse.
        For production, use cloud storage with real signed URLs.
        """
        full_path = os.path.join(self.base_path, object_key)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {object_key}")
        
        # Return absolute path for local development
        # The endpoint will use FileResponse for local storage
        return full_path
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from local filesystem"""
        full_path = os.path.join(self.base_path, object_key)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception:
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists on local filesystem"""
        full_path = os.path.join(self.base_path, object_key)
        return os.path.exists(full_path)
    
    def get_file_metadata(self, object_key: str) -> dict:
        """Get file metadata from local filesystem"""
        full_path = os.path.join(self.base_path, object_key)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {object_key}")
        
        stat = os.stat(full_path)
        
        return {
            'size': stat.st_size,
            'last_modified': datetime.fromtimestamp(stat.st_mtime),
            'content_type': 'application/pdf'  # Default, could use mimetypes module
        }
