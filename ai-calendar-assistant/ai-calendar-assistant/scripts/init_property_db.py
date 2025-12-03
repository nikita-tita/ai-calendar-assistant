"""Initialize Property Bot database tables."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.models.property import Base
from app.config import settings
import structlog

logger = structlog.get_logger()


def init_database():
    """Create all tables in the database."""

    # Get database URL from settings
    database_url = settings.property_database_url

    if not database_url:
        logger.error("PROPERTY_DATABASE_URL not set in environment")
        return False

    logger.info("Initializing database", database_url=database_url[:50] + "...")

    try:
        # Create engine
        engine = create_engine(database_url, echo=True)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully")

        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        logger.info("Created tables", count=len(tables), tables=tables)

        return True

    except Exception as e:
        logger.error("Failed to create tables", error=str(e))
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
