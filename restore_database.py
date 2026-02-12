#!/usr/bin/env python
"""
Database Restore Script for Bank Statement Analyzer

Restores database from a backup created by backup_database.py

Usage:
    python restore_database.py                              # Interactive restore
    python restore_database.py --backup statement_analyzer_backup_20260212_142154_UTC.db.gz
    python restore_database.py --list-backups              # List available backups
"""

import os
import sys
import gzip
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseRestore:
    """Handles database restore operations"""
    
    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./statement_analyzer.db")
        self.db_type = self._get_db_type()
        
        logger.info(f"✅ Restore handler initialized for {self.db_type}")
    
    def _get_db_type(self) -> str:
        """Determine database type from connection string"""
        if self.database_url.startswith("postgresql://"):
            return "postgresql"
        elif self.database_url.startswith("sqlite://"):
            return "sqlite"
        else:
            raise ValueError(f"Unsupported database type: {self.database_url}")
    
    def list_backups(self) -> list:
        """List available backups"""
        backups = sorted(self.backup_dir.glob(f"*_backup_*.gz"), reverse=True)
        
        logger.info(f"📋 Found {len(backups)} backup(s):")
        for i, backup_file in enumerate(backups, 1):
            size_mb = backup_file.stat().st_size / (1024*1024)
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            logger.info(f"  {i}. {backup_file.name} ({size_mb:.2f} MB) - {mtime}")
        
        return backups
    
    def restore_sqlite(self, backup_file: Path) -> bool:
        """Restore SQLite database from backup"""
        
        if not backup_file.exists():
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        # Extract database path
        db_path = self.database_url.replace("sqlite:///", "").split("?")[0]
        if db_path.startswith("./"):
            db_path = db_path[2:]
        
        logger.warning(f"⚠️  This will overwrite: {db_path}")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != "yes":
            logger.info("❌ Restore cancelled")
            return False
        
        # Backup current database first
        if Path(db_path).exists():
            backup_current = f"{db_path}.backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"💾 Saving current database as: {backup_current}")
            import shutil
            shutil.copy2(db_path, backup_current)
        
        try:
            logger.info("🔄 Decompressing backup...")
            with gzip.open(backup_file, "rb") as f_in:
                backup_content = f_in.read()
            
            logger.info("💿 Writing to database...")
            with open(db_path, "wb") as f_out:
                f_out.write(backup_content)
            
            # Verify database
            logger.info("✓ Verifying database...")
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] == "ok":
                logger.info("✅ Restore completed successfully")
                return True
            else:
                logger.error(f"❌ Database integrity check failed: {result[0]}")
                logger.error("   Attempting to restore from backup...")
                import shutil
                shutil.copy2(backup_current, db_path)
                return False
        
        except Exception as e:
            logger.error(f"❌ Restore failed: {str(e)}")
            if backup_current:
                logger.info("   Restoring previous database version...")
                import shutil
                shutil.copy2(backup_current, db_path)
            return False
    
    def restore_postgresql(self, backup_file: Path) -> bool:
        """Restore PostgreSQL database from backup"""
        
        if not backup_file.exists():
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        import urllib.parse
        parsed = urllib.parse.urlparse(self.database_url)
        db_name = parsed.path[1:]
        
        logger.warning(f"⚠️  This will overwrite: {db_name}")
        logger.warning("   All data in this database will be replaced")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != "yes":
            logger.info("❌ Restore cancelled")
            return False
        
        try:
            env = os.environ.copy()
            if parsed.password:
                env["PGPASSWORD"] = parsed.password
            
            # Create temporary database for restore
            temp_db = f"{db_name}_restore_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            logger.info(f"📊 Creating temporary database: {temp_db}")
            subprocess.run(
                ["createdb", "-U", parsed.username, "-h", parsed.hostname, temp_db],
                env=env,
                check=True
            )
            
            logger.info("🔄 Restoring from backup...")
            with gzip.open(backup_file, "rt") as f:
                subprocess.run(
                    ["psql", "-U", parsed.username, "-h", parsed.hostname, temp_db],
                    stdin=f,
                    env=env,
                    check=True,
                    capture_output=True
                )
            
            logger.info("✓ Verifying restored database...")
            result = subprocess.run(
                ["psql", "-U", parsed.username, "-h", parsed.hostname, "-d", temp_db, "-c", "SELECT COUNT(*) FROM transactions;"],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.warning(f"⚠️  Renaming databases (this might take a moment)...")
                
                # Rename databases
                subprocess.run(
                    ["psql", "-U", parsed.username, "-h", parsed.hostname, "-d", "postgres", 
                     "-c", f"ALTER DATABASE {db_name} RENAME TO {db_name}_old;"],
                    env=env,
                    check=True
                )
                
                subprocess.run(
                    ["psql", "-U", parsed.username, "-h", parsed.hostname, "-d", "postgres",
                     "-c", f"ALTER DATABASE {temp_db} RENAME TO {db_name};"],
                    env=env,
                    check=True
                )
                
                logger.info("✅ Restore completed successfully")
                logger.info(f"💾 Old database saved as: {db_name}_old")
                logger.info("   You can drop it with: DROP DATABASE [db_name]_old;")
                
                return True
            else:
                logger.error(f"❌ Restored database verification failed")
                logger.info(f"   Dropping temporary database: {temp_db}")
                subprocess.run(
                    ["dropdb", "-U", parsed.username, "-h", parsed.hostname, temp_db],
                    env=env
                )
                return False
        
        except FileNotFoundError as e:
            logger.error(f"❌ PostgreSQL tools not found: {str(e)}")
            logger.error("   Install PostgreSQL client tools:")
            logger.error("   macOS: brew install postgresql")
            logger.error("   Ubuntu: sudo apt-get install postgresql-client")
            logger.error("   Windows: https://www.postgresql.org/download/windows/")
            return False
        
        except Exception as e:
            logger.error(f"❌ Restore failed: {str(e)}")
            return False
    
    def restore(self, backup_file: Path) -> bool:
        """Execute restore based on database type"""
        
        if self.db_type == "sqlite":
            return self.restore_sqlite(backup_file)
        elif self.db_type == "postgresql":
            return self.restore_postgresql(backup_file)
        else:
            logger.error(f"Unsupported database type: {self.db_type}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Database restore script for Bank Statement Analyzer"
    )
    parser.add_argument(
        "--backup",
        help="Backup file to restore from (filename only, searches in ./backups)"
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available backups"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Database Restore Script")
    logger.info("=" * 60)
    
    try:
        restore_handler = DatabaseRestore()
        
        if args.list_backups:
            restore_handler.list_backups()
            return 0
        
        # Select backup
        if args.backup:
            backup_file = Path("./backups") / args.backup
        else:
            backups = restore_handler.list_backups()
            
            if not backups:
                logger.error("❌ No backups found in ./backups directory")
                return 1
            
            print("\nSelect backup to restore from:")
            choice = input(f"Enter backup number (1-{len(backups)}): ")
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    backup_file = backups[index]
                else:
                    logger.error("❌ Invalid selection")
                    return 1
            except ValueError:
                logger.error("❌ Invalid input")
                return 1
        
        logger.info(f"📦 Selected backup: {backup_file.name}")
        
        # Execute restore
        if restore_handler.restore(backup_file):
            logger.info("=" * 60)
            logger.info("✅ Restore completed successfully")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("❌ Restore failed")
            logger.error("=" * 60)
            return 1
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
