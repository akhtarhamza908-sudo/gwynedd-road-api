"""
Aggregate all API routers under the /api/v1 prefix.
"""
from fastapi import APIRouter

from app.routes.admin import router as admin_router
from app.routes.roads import router as roads_router
from app.routes.search import router as search_router
from app.routes.analysis import router as analysis_router

api_router = APIRouter()
api_router.include_router(admin_router)
# Search must be registered before parameterized roads routes so
# /search, /search/suggestions, and /nearby are matched before /{road_id}.
api_router.include_router(search_router)
api_router.include_router(roads_router)
api_router.include_router(analysis_router)
