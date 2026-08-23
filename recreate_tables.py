"""Recreate database tables with updated schema."""
from sqlalchemy import create_engine, text
from app.core.config import get_settings
from app.models.road import Road
from app.models.segment import RoadSegment
from app.database.connection import Base

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

# Drop existing tables
print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine)

# Create new tables with updated schema
print("Creating new tables...")
Base.metadata.create_all(bind=engine)

print("Tables recreated successfully!")
print("You can now restart the server and run sync.")
