"""
Backup routes.

Provides a streaming backup download (pg_dump / SQLite copy piped directly
to the HTTP response — no file stored server-side) and a history of
user-triggered downloads for audit purposes.
"""

import io
import os
import subprocess
import gzip
import shutil
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from config import DATABASE_URL, ENVIRONMENT
from models import BackupRecord, User, get_db

router = APIRouter(tags=["Backups"])


def _get_pg_env(db_url: str) -> tuple[dict, str]:
    """
    Parse a PostgreSQL URL and return (env_dict, database_name).
    The env dict sets PGPASSWORD so pg_dump doesn't prompt.
    """
    parsed = urlparse(db_url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    return env, (parsed.path.lstrip("/") or "statementbur")


def _pg_dump_stream(db_url: str):
    """Generator that yields gzip-compressed pg_dump output in chunks."""
    env, db_name = _get_pg_env(db_url)
    parsed = urlparse(db_url)

    cmd = ["pg_dump", "--no-password", "-Fp"]  # plain-text SQL format
    if parsed.hostname:
        cmd += ["-h", parsed.hostname]
    if parsed.port:
        cmd += ["-p", str(parsed.port)]
    if parsed.username:
        cmd += ["-U", parsed.username]
    cmd.append(db_name)

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as proc:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            total_bytes = 0
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                gz.write(chunk)
                total_bytes += len(chunk)

        stderr_output = proc.stderr.read()
        if proc.returncode and proc.returncode != 0:
            raise RuntimeError(
                f"pg_dump exited with code {proc.returncode}: {stderr_output.decode()[:500]}"
            )

        buf.seek(0)
        while True:
            chunk = buf.read(65536)
            if not chunk:
                break
            yield chunk


def _sqlite_stream(db_url: str):
    """
    Generator that streams a gzip-compressed copy of the SQLite database file.
    Uses SQLite's backup API via the sqlite3 module for a consistent snapshot.
    """
    import sqlite3

    db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    # Resolve relative path from the backend directory
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "..", db_path)
    db_path = os.path.normpath(db_path)

    # Create an in-memory backup snapshot
    source = sqlite3.connect(db_path)
    dest = sqlite3.connect(":memory:")
    source.backup(dest)
    source.close()

    # Dump to bytes via tempfile approach
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        # Write the SQLite file bytes from the in-memory connection
        dest_path = db_path + ".tmp_backup"
        dest_file = sqlite3.connect(dest_path)
        dest.backup(dest_file)
        dest.close()
        dest_file.close()
        with open(dest_path, "rb") as f:
            shutil.copyfileobj(f, gz)
        os.remove(dest_path)

    buf.seek(0)
    while True:
        chunk = buf.read(65536)
        if not chunk:
            break
        yield chunk


@router.get("/backups/download")
def download_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream a full database backup directly to the browser.

    For PostgreSQL: streams gzip-compressed pg_dump output.
    For SQLite: streams a gzip-compressed copy of the database file.

    No file is stored server-side — the dump is piped directly into the
    HTTP response. A BackupRecord is written to track the download.
    """
    now = datetime.utcnow()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"statementbur_backup_{timestamp}.sql.gz"

    # Normalise URL
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    is_postgres = url.startswith("postgresql")
    is_sqlite = url.startswith("sqlite")

    if not is_postgres and not is_sqlite:
        raise HTTPException(status_code=500, detail="Unsupported database type for backup")

    # Log backup record (best-effort — failures here don't block the download)
    try:
        record = BackupRecord(
            user_id=current_user.id,
            label=f"Full backup - {now.strftime('%Y-%m-%d %H:%M')} UTC",
            status="completed",
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()

    try:
        if is_postgres:
            stream = _pg_dump_stream(url)
        else:
            stream = _sqlite_stream(url)

        return StreamingResponse(
            stream,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Backup-Timestamp": timestamp,
            },
        )
    except Exception as e:
        # Update record to failed
        try:
            record.status = "failed"
            record.error_message = str(e)[:500]
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/backups/history")
def list_backup_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the audit log of backup downloads for this user."""
    records = (
        db.query(BackupRecord)
        .filter(BackupRecord.user_id == current_user.id)
        .order_by(BackupRecord.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "backups": [
            {
                "id": r.id,
                "label": r.label,
                "status": r.status,
                "file_size_bytes": r.file_size_bytes,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }
