"""Database connection module for the shop."""
import os
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine with connection pool settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Enables automatic reconnection
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=5,         # Maximum number of connections in pool
    max_overflow=10      # Maximum number of connections that can be created beyond pool_size
)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """Get database session with automatic reconnection."""
    session = SessionLocal()
    try:
        # Test the connection using SQLAlchemy text()
        session.execute(text("SELECT 1"))
        logger.debug("Database connection successful")
        return session
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        session.close()
        # Create a new session
        logger.info("Attempting to create new database session")
        session = SessionLocal()
        return session

def init_db():
    """Initialize database tables."""
    try:
        logger.info("Starting database initialization...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:  # Only create tables if they don't exist
            logger.info("No tables found, creating database schema")
            Base.metadata.create_all(engine)
            logger.info("Database tables created successfully")

            # Verify tables were created
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Created tables: {', '.join(tables)}")
        else:
            logger.info(f"Existing tables found: {', '.join(tables)}")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise