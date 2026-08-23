"""
Admin endpoints: health checks, database initialization, data sync, cache management.
"""
from datetime import datetime

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.connection import get_db, get_db_context, init_db
from app.models.road import Road
from app.schemas.responses import HealthCheck
from app.services.sync_service import DataSyncService
from app.utils.cache import get_cache

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health", response_model=HealthCheck)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    cache = get_cache()
    cache_status = "connected"
    try:
        cache.set("health_check", "ok", ttl=60)
        if cache.get("health_check") != "ok":
            cache_status = "error"
    except Exception:
        cache_status = "error"

    try:
        roads_loaded = db.query(Road).count()
    except Exception:
        roads_loaded = 0

    return HealthCheck(
        status="ok",
        version=settings.VERSION,
        database="connected",
        cache=cache_status,
        roads_loaded=roads_loaded,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/init-db")
def initialize_database():
    """Initialize the database (PostGIS + tables)."""
    try:
        init_db()
        return {"status": "success", "message": "Database initialized successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/sync", status_code=202)
async def sync_roads():
    """Trigger a full OpenStreetMap data synchronization (background task)."""
    async def _run_sync():
        with get_db_context() as db:
            sync_service = DataSyncService(db)
            try:
                await sync_service.sync_all_roads()
            finally:
                await sync_service.close()

    asyncio.create_task(_run_sync())
    return {
        "status": "accepted",
        "message": "Road sync started in the background. This may take 1-3 minutes."
    }


@router.post("/cache/clear")
def clear_cache():
    """Clear all cached data."""
    try:
        get_cache().clear()
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
