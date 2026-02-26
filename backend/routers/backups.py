"""
Backup routes.

Provides a streaming backup download and restore using pure Python / psycopg2
(no pg_dump / psql binaries required — works on Render and any Python runtime).

Backup format: gzip-compressed custom text format
  Line 1: RECONEX_V1
  Line 2: JSON metadata (tables list, sequence values, timestamp)
  Line 3: DATA
  Per table:
    TABLE <name>\n
    <psycopg2 COPY TEXT output>\n
    \.\n          ← end-of-table marker
"""

import io
import json
import os
import gzip
import shutil
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import get_current_user
from config import DATABASE_URL, ENVIRONMENT
from models import BackupRecord, User, get_db, engine

router = APIRouter(tags=["Backups"])


# ---------------------------------------------------------------------------
# PostgreSQL helpers — pure psycopg2, no external binaries
# ---------------------------------------------------------------------------

def _pg_connect(db_url: str):
    """Open a psycopg2 connection from a postgresql:// URL."""
    import psycopg2  # already in requirements.txt
    parsed = urlparse(db_url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip("/"),
        connect_timeout=30,
    )


def _pg_backup_stream(db_url: str):
    """
    Generator that yields a gzip-compressed RECONEX_V1 backup.
    Uses psycopg2 COPY TO STDOUT — no pg_dump binary required.
    """
    conn = _pg_connect(db_url)
    try:
        # Repeatable-read snapshot for consistency across tables
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        cur = conn.cursor()

        # Tables in alphabetical order (FK-safe because we disable triggers on restore)
        cur.execute(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = [row[0] for row in cur.fetchall()]

        # Current sequence values so restore can reset them correctly
        cur.execute(
            "SELECT sequencename, last_value FROM pg_sequences "
            "WHERE schemaname = 'public'"
        )
        sequences = {row[0]: row[1] for row in cur.fetchall()}

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(b"RECONEX_V1\n")
            meta = {
                "format": "reconex_v1",
                "exported_at": datetime.utcnow().isoformat(),
                "tables": tables,
                "sequences": sequences,
            }
            gz.write((json.dumps(meta) + "\n").encode())
            gz.write(b"DATA\n")

            for table in tables:
                gz.write(f"TABLE {table}\n".encode())
                copy_buf = io.BytesIO()
                cur.copy_expert(
                    f'COPY "{table}" TO STDOUT WITH (FORMAT TEXT)', copy_buf
                )
                copy_buf.seek(0)
                gz.write(copy_buf.read())
                gz.write(b"\\.\n")  # end-of-table marker (pg COPY convention)

        buf.seek(0)
        while True:
            chunk = buf.read(65536)
            if not chunk:
                break
            yield chunk
    finally:
        conn.close()


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


# ---------------------------------------------------------------------------
# Restore helpers
# ---------------------------------------------------------------------------


def _sqlite_restore(db_url: str, gz_data: bytes) -> None:
    """Overwrite the SQLite database file with the content from a .gz backup."""
    db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "..", db_path)
    db_path = os.path.normpath(db_path)

    decompressed = gzip.decompress(gz_data)

    # Validate SQLite magic header
    if not decompressed[:16].startswith(b"SQLite format 3\x00"):
        raise ValueError("Uploaded file is not a valid SQLite database")

    tmp_path = db_path + ".restore_tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(decompressed)
        # Release all pooled connections so the file can be replaced
        engine.dispose()
        shutil.move(tmp_path, db_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _pg_restore(db_url: str, gz_data: bytes) -> None:
    """
    Restore a PostgreSQL database from a RECONEX_V1 gzip backup.
    Uses psycopg2 COPY FROM STDIN — no psql binary required.

    Does NOT require superuser — only table-ownership (the Render user owns
    all tables because Alembic migrations created them).
    """
    import logging
    logger = logging.getLogger(__name__)

    raw = gzip.decompress(gz_data).decode("utf-8")
    lines = raw.split("\n")

    if not lines or lines[0] != "RECONEX_V1":
        raise ValueError(
            "Unrecognised backup format. "
            "Only backups created by this application (RECONEX_V1) can be restored here."
        )

    meta = json.loads(lines[1])
    tables: list = meta["tables"]
    sequences: dict = meta.get("sequences", {})

    try:
        data_idx = lines.index("DATA") + 1
    except ValueError:
        raise ValueError("Backup file is corrupt: missing DATA section.")

    conn = _pg_connect(db_url)
    try:
        conn.autocommit = False
        cur = conn.cursor()

        # Disable FK-constraint triggers on every table.  This only requires
        # table ownership (not superuser), so it works on Render's managed PG.
        for t in tables:
            cur.execute(f'ALTER TABLE "{t}" DISABLE TRIGGER ALL')

        # Wipe all tables in one shot (CASCADE handles FK order)
        if tables:
            truncate_expr = ", ".join(f'"{t}"' for t in tables)
            cur.execute(f"TRUNCATE {truncate_expr} RESTART IDENTITY CASCADE")

        # Parse table blocks and COPY data back in
        i = data_idx
        while i < len(lines):
            line = lines[i]
            if line.startswith("TABLE "):
                table = line[6:].strip()
                i += 1
                copy_lines = []
                while i < len(lines) and lines[i] != "\\.":
                    copy_lines.append(lines[i])
                    i += 1
                i += 1  # skip the \. marker
                if copy_lines:
                    copy_data = "\n".join(copy_lines) + "\n"
                    copy_buf = io.BytesIO(copy_data.encode())
                    cur.copy_expert(
                        f'COPY "{table}" FROM STDIN WITH (FORMAT TEXT)', copy_buf
                    )
                    logger.info("Restored table %s (%d rows of COPY data)", table, len(copy_lines))
            else:
                i += 1

        # Reset sequences to their backed-up values
        for seq_name, last_val in sequences.items():
            if last_val is not None:
                cur.execute(
                    f"SELECT setval('{seq_name}', %s, true)", (last_val,)
                )

        # Re-enable triggers on every table
        for t in tables:
            cur.execute(f'ALTER TABLE "{t}" ENABLE TRIGGER ALL')

        conn.commit()
        logger.info("PostgreSQL restore committed successfully")
    except Exception as exc:
        logger.error("PostgreSQL restore failed: %s", exc, exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


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
    # Filename depends on DB type: SQL dump for PostgreSQL, binary DB file for SQLite
    url_check = DATABASE_URL
    if url_check.startswith("postgres://"):
        url_check = url_check.replace("postgres://", "postgresql://", 1)
    _ext = "bak.gz" if url_check.startswith("postgresql") else "db.gz"
    filename = f"reconex_backup_{timestamp}.{_ext}"

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
            stream = _pg_backup_stream(url)
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


@router.post("/backups/restore")
async def restore_backup(
    file: UploadFile = File(...),
    confirm: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restore the database from an uploaded .gz backup file.

    WARNING: This overwrites ALL current data irreversibly.
    The `confirm=true` query parameter must be present.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Restore aborted: add confirm=true to proceed. This will overwrite all current data.",
        )

    if not (file.filename or "").endswith(".gz"):
        raise HTTPException(status_code=400, detail="Backup file must be a .gz compressed file")

    # Read upload (2 GB hard cap)
    content = await file.read(2 * 1024 * 1024 * 1024)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    is_postgres = url.startswith("postgresql")
    is_sqlite = url.startswith("sqlite")

    if not is_postgres and not is_sqlite:
        raise HTTPException(status_code=500, detail="Unsupported database type for restore")

    try:
        # --- Drain ALL connections before replacing the DB ---
        # render.yaml starts uvicorn with --workers 2, so there are (at least) two
        # separate OS processes each with their own SQLAlchemy connection pool.
        # engine.dispose() only drains the current worker's pool; the other worker
        # keeps its connections alive and holds table-level locks.  When psql then
        # replays the --clean dump and runs DROP TABLE the locks cause every DROP to
        # fail inside --single-transaction, which rolls the entire restore back
        # without raising an error visible to the caller.
        #
        # Fix: use pg_terminate_backend to forcibly close every OTHER backend
        # connected to this database (across all workers / external tools) BEFORE
        # we close our own session and dispose the pool.
        if is_postgres:
            try:
                db.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = current_database() "
                        "  AND pid <> pg_backend_pid()"
                    )
                )
                db.commit()
            except Exception:
                # Non-fatal — best effort; dispose will still run
                pass

        db.close()
        engine.dispose()

        if is_sqlite:
            _sqlite_restore(url, content)
        else:
            _pg_restore(url, content)

        return {
            "success": True,
            "message": "Database restored successfully. Refresh the application to see restored data.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


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
