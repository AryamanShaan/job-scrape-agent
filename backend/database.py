"""
Database setup using SQLAlchemy.

- engine: the connection to Postgres
- SessionLocal: creates a new database session (used per-request in FastAPI)
- Base: all ORM models inherit from this
- get_db(): FastAPI dependency that provides a session and auto-closes it
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

# Create the database engine from our connection string
engine = create_engine(settings.DATABASE_URL)

# Each call to SessionLocal() gives us a fresh database session
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base class for all our ORM models (Company, Job, Resume)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency: yields a database session, then closes it.
    Usage in a route:  def my_route(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
