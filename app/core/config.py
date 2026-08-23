"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",#utf-universal-text-format
        extra="ignore"
    )
    # Application
    APP_NAME: str = "Gwynedd Road Infrastructure API"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    VERSION: str = "4.0.0"
    # Database
    DATABASE_URL: str = "postgresql://postgres:123@localhost:5432/gwynedd_roads"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_ECHO: bool = False
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600  # 1 hour
    
    # Elevation API
    ELEVATION_API_URL: str = "https://api.open-elevation.com/api/v1/lookup"
    
    # OSM Settings
    OSM_PLACE: str = "Gwynedd, Wales, United Kingdom"
    OSM_NETWORK_TYPE: str = "drive"
    OSM_CACHE_DIR: str = "./cache"
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache() # Cache settings instance for performance
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

