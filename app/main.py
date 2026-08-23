"""
Gwynedd Road Infrastructure API - Production Entry Point
Phases 2-4: Data Enrichment, Database Integration, and Advanced Geo Analysis
"""
# synchronous: instantly
# asynchronous:waiting for response
#green:classes/types
#yellow:functions
#white:modules/packages/libraries
#purple:keywords/statements
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.database.connection import init_db
from app.routes import api_router
from app.utils.cache import get_cache

settings = get_settings()
#(=) precedence: from right to left
#(@) decorators: modify behavior of functions/classes

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    
    - Initializes database on startup
    - Sets up cache connection
    - Cleans up resources on shutdown
    """
    print(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    # Initialize database
    try:
        init_db()#functioning call
        print("Database initialized")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        print("   Database may already be set up.")
    
    # Initialize cache
    try:
        cache = get_cache()
        cache.set("app_startup", "ok", ttl=60)#parameters
        print("Cache connected")
    except Exception as e:
        print(f"Cache connection warning: {e}")
    
    print(f"Application ready at http://0.0.0.0:8000")
    print(f"API Documentation: http://0.0.0.0:8000/docs")
    print(f"OpenAPI Schema: http://0.0.0.0:8000/openapi.json")
    
    try:
        yield #application is running and can handle requests
    finally:
        # Cleanup
        print("Shutting down application...")
        try:
            cache = get_cache()
            await cache.close() if hasattr(cache, 'close') else None
        except Exception:
            pass
        print("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Production-grade Geo-Spatial Road Infrastructure API for Gwynedd, Wales, UK.
    
    ## Features
    
    ### Phase 2 - Data Enrichment
    - Smart road search with partial matching
    - Road attributes: type, speed limit, surface
    - Multi-segment aggregation with bounding boxes
    
    ### Phase 3 - Database & Performance
    - PostgreSQL + PostGIS for spatial data
    - SQLAlchemy ORM with connection pooling
    - Redis/in-memory caching
    - Pagination and filtering
    
    ### Phase 4 - Advanced Geo Analysis
    - Curvature and turn count analysis
    - Elevation profile integration
    - Width estimation
    - GeoJSON export
    
    ## Data Source
    OpenStreetMap via OSMnx
    
    ## Authentication
    Currently no authentication required (public API).
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Gwynedd Roads API Team",
    },
    license_info={
        "name": "MIT",
    },
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(api_router, prefix="/api/v1")

# Legacy endpoint for backward compatibility
@app.get("/", tags=["Health"], summary="API Root")
def root():
    """Root endpoint - API information and health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "api": "/api/v1",
            "health": "/api/v1/admin/health",
            "roads": "/api/v1/roads"
        }
    }

# Keep backward compatibility with Phase 1 & 2 endpoints
@app.get("/road/{road_name}", tags=["Legacy"], deprecated=True)
def legacy_get_road(road_name: str):
    """
    Legacy endpoint - redirects to new API.
    
    Use `/api/v1/roads/by-name/{road_name}` instead.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/api/v1/roads/by-name/{road_name}")
