"""
Admin routes: cache management, health check, root endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from models import User, get_db
from routers.dependencies import ensure_session_access
from services.cache import get_cache

router = APIRouter(tags=["Admin"])


@router.get("/cache/stats")
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """Get cache statistics including hit rate, size, and key count."""
    cache = get_cache()
    return cache.get_stats()


@router.get("/cache/health")
async def cache_health_check(current_user: User = Depends(get_current_user)):
    """Check cache health status (Redis connection). Requires authentication."""
    cache = get_cache()
    return cache.health_check()


@router.delete("/cache/flush")
async def flush_cache(current_user: User = Depends(get_current_user)):
    """Flush all cache entries. Requires superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can flush cache")
    cache = get_cache()
    success = cache.flush_all()
    if success:
        return {"message": "Cache flushed successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to flush cache")


@router.delete("/cache/session/{session_id}")
async def invalidate_session_cache(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate all cache entries for a specific session."""
    ensure_session_access(session_id, current_user, db)
    cache = get_cache()
    deleted_count = cache.invalidate_session(session_id)
    return {"message": f"Invalidated cache for session {session_id}", "deleted_keys": deleted_count}


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/")
def root():
    """API information."""
    return {
        "name": "Bank Statement Analyzer",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if __import__("config").DEBUG else None,
    }
