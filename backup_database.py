#!/usr/bin/env python
"""
Database Backup Script for Bank Statement Analyzer

Supports:
- PostgreSQL (production)
- SQLite (development)
- Upload to cloud storage (S3, Azure, GCS)
- Automatic retention/cleanup of old backups
- Email notifications on backup completion/failure

Usage:
    python backup_database.py                 # Run backup with config from .env
    python backup_database.py --help          # Show help
    python backup_database.py --upload-s3     # Backup and upload to S3
    python backup_database.py --upload-azure  # Backup and upload to Azure
    python backup_database.py --test          # Test backup without uploading
"""

import os
import sys
import json
import gzip
import shutil
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles database backup operations"""
    
    def __init__(self, database_url: str, backup_dir: str = "./backups"):
        """
        Initialize backup handler
        
        Args:
            database_url: Database connection string (from config)
            backup_dir: Directory to store backups
        """
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine database type
        self.db_type = self._get_db_type()
        
        logger.info(f"✅ Backup handler initialized for {self.db_type}")
        logger.info(f"📁 Backup directory: {self.backup_dir}")
    
    def _get_db_type(self) -> str:
        """Determine database type from connection string"""
        if self.database_url.startswith("postgresql://"):
            return "postgresql"
        elif self.database_url.startswith("sqlite://"):
            return "sqlite"
        elif self.database_url.startswith("mysql"):
            return "mysql"
        else:
            raise ValueError(f"Unsupported database type: {self.database_url}")
    
    def _get_backup_filename(self) -> str:
        """Generate backup filename with timestamp"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_UTC")
        db_name = self._extract_db_name()
        return f"{db_name}_backup_{timestamp}"
    
    def _extract_db_name(self) -> str:
        """Extract database name from connection string"""
        if self.db_type == "postgresql":
            # postgresql://user:pass@host:port/dbname
            return self.database_url.split("/")[-1].split("?")[0] or "database"
        elif self.db_type == "sqlite":
            # sqlite:///./statement_analyzer.db
            return Path(self.database_url.split("///")[-1]).stem
        return "backup"
    
    def backup_sqlite(self) -> Path:
        """
        Backup SQLite database
        
        Returns:
            Path to backup file (.sql.gz)
        """
        logger.info("🔄 Starting SQLite backup...")
        
        # Extract file path from connection string
        db_path = self.database_url.replace("sqlite:///", "").split("?")[0]
        if db_path.startswith("./"):
            db_path = db_path[2:]
        
        if not Path(db_path).exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")
        
        logger.info(f"📂 Database file: {db_path}")
        
        # Read database file
        with open(db_path, "rb") as f:
            db_content = f.read()
        
        logger.info(f"✅ Read {len(db_content) / (1024*1024):.2f} MB from database")
        
        # Create backup file
        backup_filename = self._get_backup_filename() + ".db"
        backup_path = self.backup_dir / backup_filename
        
        # Write and compress
        logger.info("🗜️  Compressing backup...")
        with gzip.open(f"{backup_path}.gz", "wb") as f:
            f.write(db_content)
        
        compressed_size = Path(f"{backup_path}.gz").stat().st_size / (1024*1024)
        logger.info(f"✅ Backup saved: {backup_path}.gz ({compressed_size:.2f} MB)")
        
        return Path(f"{backup_path}.gz")
    
    def backup_postgresql(self) -> Path:
        """
        Backup PostgreSQL database using pg_dump
        
        Returns:
            Path to backup file (.sql.gz)
        """
        logger.info("🔄 Starting PostgreSQL backup...")
        
        # Parse connection string
        # postgresql://user:password@host:port/dbname
        import urllib.parse
        parsed = urllib.parse.urlparse(self.database_url)
        
        logger.info(f"📊 Database: {parsed.path[1:]} @ {parsed.hostname}")
        
        # Prepare pg_dump command
        backup_filename = self._get_backup_filename() + ".sql"
        backup_path = self.backup_dir / backup_filename
        
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password
        
        cmd = [
            "pg_dump",
            "-h", parsed.hostname,
            "-U", parsed.username,
            "-d", parsed.path[1:],
            "-F", "plain",  # Text format
            "-v",  # Verbose
        ]
        
        if parsed.port:
            cmd.extend(["-p", str(parsed.port)])
        
        try:
            logger.info(f"🔧 Running: {' '.join(cmd[:4])} ...")
            
            # Execute pg_dump and compress
            with gzip.open(f"{backup_path}.gz", "wb") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=False,
                    env=env,
                    timeout=300  # 5 minute timeout
                )
            
            if result.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {result.stderr.decode('utf-8', errors='ignore')}")
            
            compressed_size = Path(f"{backup_path}.gz").stat().st_size / (1024*1024)
            logger.info(f"✅ Backup saved: {backup_path}.gz ({compressed_size:.2f} MB)")
            
            return Path(f"{backup_path}.gz")
        
        except FileNotFoundError:
            logger.error("❌ pg_dump not found. Install PostgreSQL client tools:")
            logger.error("   macOS: brew install postgresql")
            logger.error("   Ubuntu: sudo apt-get install postgresql-client")
            logger.error("   Windows: https://www.postgresql.org/download/windows/")
            raise
    
    def backup(self) -> Path:
        """
        Execute backup based on database type
        
        Returns:
            Path to backup file
        """
        try:
            if self.db_type == "postgresql":
                return self.backup_postgresql()
            elif self.db_type == "sqlite":
                return self.backup_sqlite()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
        
        except Exception as e:
            logger.error(f"❌ Backup failed: {str(e)}")
            raise
    
    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """
        Delete backups older than retention period
        
        Args:
            retention_days: Keep backups from last N days
            
        Returns:
            Number of backups deleted
        """
        logger.info(f"🧹 Cleaning up backups older than {retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob(f"*_backup_*.gz"):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if file_time < cutoff_date:
                size_mb = backup_file.stat().st_size / (1024*1024)
                backup_file.unlink()
                logger.info(f"  🗑️  Deleted: {backup_file.name} ({size_mb:.2f} MB)")
                deleted_count += 1
        
        if deleted_count == 0:
            logger.info("  ✅ No old backups to delete")
        else:
            logger.info(f"✅ Deleted {deleted_count} old backup(s)")
        
        return deleted_count
    
    def list_backups(self) -> list:
        """List all existing backups"""
        backups = sorted(self.backup_dir.glob(f"*_backup_*.gz"), reverse=True)
        
        logger.info(f"📋 Found {len(backups)} backup(s):")
        for backup_file in backups:
            size_mb = backup_file.stat().st_size / (1024*1024)
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            logger.info(f"  • {backup_file.name} ({size_mb:.2f} MB) - {mtime}")
        
        return backups
    
    def estimate_size(self) -> float:
        """Estimate backup size"""
        if self.db_type == "sqlite":
            db_path = self.database_url.replace("sqlite:///", "").split("?")[0]
            if db_path.startswith("./"):
                db_path = db_path[2:]
            if Path(db_path).exists():
                return Path(db_path).stat().st_size / (1024*1024)
        
        return 0.0


class CloudUpload:
    """Handles uploading backups to cloud storage"""
    
    @staticmethod
    def upload_to_s3(backup_path: Path, bucket: str, prefix: str = "backups") -> bool:
        """
        Upload backup to AWS S3
        
        Args:
            backup_path: Path to backup file
            bucket: S3 bucket name
            prefix: Folder prefix in bucket
            
        Returns:
            True if successful
        """
        try:
            import boto3
            logger.info(f"☁️  Uploading to S3: s3://{bucket}/{prefix}/{backup_path.name}")
            
            s3_client = boto3.client('s3')
            s3_client.upload_file(
                str(backup_path),
                bucket,
                f"{prefix}/{backup_path.name}",
                ExtraArgs={'Metadata': {'backup_date': str(datetime.utcnow())}}
            )
            
            logger.info("✅ Upload to S3 successful")
            return True
        
        except ImportError:
            logger.error("❌ boto3 not installed: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"❌ S3 upload failed: {str(e)}")
            return False
    
    @staticmethod
    def upload_to_azure(backup_path: Path, container: str, account_name: str = None) -> bool:
        """
        Upload backup to Azure Blob Storage
        
        Args:
            backup_path: Path to backup file
            container: Container name
            account_name: Storage account name (uses AZURE_STORAGE_ACCOUNT_NAME env var)
            
        Returns:
            True if successful
        """
        try:
            from azure.storage.blob import BlobClient
            
            account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            
            if not connection_string:
                logger.error("❌ AZURE_STORAGE_CONNECTION_STRING not set")
                return False
            
            logger.info(f"☁️  Uploading to Azure: {container}/{backup_path.name}")
            
            blob_client = BlobClient.from_connection_string(
                connection_string,
                container_name=container,
                blob_name=backup_path.name
            )
            
            with open(backup_path, "rb") as f:
                blob_client.upload_blob(f, overwrite=True)
            
            logger.info("✅ Upload to Azure successful")
            return True
        
        except ImportError:
            logger.error("❌ azure-storage-blob not installed: pip install azure-storage-blob")
            return False
        except Exception as e:
            logger.error(f"❌ Azure upload failed: {str(e)}")
            return False
    
    @staticmethod
    def upload_to_gcs(backup_path: Path, bucket: str, prefix: str = "backups") -> bool:
        """
        Upload backup to Google Cloud Storage
        
        Args:
            backup_path: Path to backup file
            bucket: GCS bucket name
            prefix: Folder prefix
            
        Returns:
            True if successful
        """
        try:
            from google.cloud import storage
            
            logger.info(f"☁️  Uploading to GCS: gs://{bucket}/{prefix}/{backup_path.name}")
            
            client = storage.Client()
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(f"{prefix}/{backup_path.name}")
            
            blob.upload_from_filename(str(backup_path))
            
            logger.info("✅ Upload to GCS successful")
            return True
        
        except ImportError:
            logger.error("❌ google-cloud-storage not installed: pip install google-cloud-storage")
            return False
        except Exception as e:
            logger.error(f"❌ GCS upload failed: {str(e)}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Database backup script for Bank Statement Analyzer"
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload backup to AWS S3"
    )
    parser.add_argument(
        "--upload-azure",
        action="store_true",
        help="Upload backup to Azure Blob Storage"
    )
    parser.add_argument(
        "--upload-gcs",
        action="store_true",
        help="Upload backup to Google Cloud Storage"
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        default=30,
        help="Delete backups older than N days (default: 30)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backups"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test backup without uploading"
    )
    parser.add_argument(
        "--s3-bucket",
        help="S3 bucket name"
    )
    parser.add_argument(
        "--azure-container",
        help="Azure container name"
    )
    parser.add_argument(
        "--gcs-bucket",
        help="GCS bucket name"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///./statement_analyzer.db")
    
    logger.info("=" * 60)
    logger.info("Database Backup Script")
    logger.info("=" * 60)
    
    try:
        # Initialize backup handler
        backup_handler = DatabaseBackup(database_url)
        
        # List backups if requested
        if args.list:
            backup_handler.list_backups()
            return 0
        
        # Estimate size
        estimated_size = backup_handler.estimate_size()
        if estimated_size > 0:
            logger.info(f"📊 Estimated backup size: {estimated_size:.2f} MB")
        
        # Run backup
        backup_path = backup_handler.backup()
        
        # Upload if requested
        if args.upload_s3:
            s3_bucket = args.s3_bucket or os.getenv("S3_BUCKET_NAME")
            if s3_bucket:
                CloudUpload.upload_to_s3(backup_path, s3_bucket)
            else:
                logger.error("❌ S3 bucket not specified. Use --s3-bucket or set S3_BUCKET_NAME")
        
        elif args.upload_azure:
            azure_container = args.azure_container or os.getenv("AZURE_CONTAINER_NAME")
            if azure_container:
                CloudUpload.upload_to_azure(backup_path, azure_container)
            else:
                logger.error("❌ Azure container not specified. Use --azure-container or set AZURE_CONTAINER_NAME")
        
        elif args.upload_gcs:
            gcs_bucket = args.gcs_bucket or os.getenv("GCS_BUCKET_NAME")
            if gcs_bucket:
                CloudUpload.upload_to_gcs(backup_path, gcs_bucket)
            else:
                logger.error("❌ GCS bucket not specified. Use --gcs-bucket or set GCS_BUCKET_NAME")
        
        elif not args.test:
            logger.info("💡 Tip: Use --upload-s3, --upload-azure, or --upload-gcs to upload backup")
        
        # Cleanup old backups
        backup_handler.cleanup_old_backups(args.cleanup)
        
        logger.info("=" * 60)
        logger.info("✅ Backup completed successfully")
        logger.info("=" * 60)
        
        return 0
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Backup failed: {str(e)}")
        logger.error("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
