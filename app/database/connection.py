"""
Database connection management using SQLAlchemy and GeoAlchemy2.
"""
from contextlib import contextmanager
from typing import Generator

from geoalchemy2 import Geometry
from sqlalchemy import create_engine, event, Index, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import get_settings

settings = get_settings()

# SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)#function definition

# Base class for declarative models
Base = declarative_base()

#initialize->init
def init_db() -> None:
    """Initialize database with PostGIS extension and tables."""
    # Enable PostGIS extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
        conn.commit()#actual connection to the database and commit the changes to enable PostGIS extensions
    
    # Create all tables
    Base.metadata.create_all(bind=engine)#declarative_base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully")


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()#function calling
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions (for background tasks)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()#act upon
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
