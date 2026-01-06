"""Database connection utilities."""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# Database file location
DB_PATH = Path(__file__).parent.parent / "data" / "logistics.db"


def get_engine(db_path: str | None = None):
    """Create SQLAlchemy engine."""
    path = db_path or str(DB_PATH)
    return create_engine(f"sqlite:///{path}", echo=False)


def get_session(db_path: str | None = None):
    """Create a new database session."""
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(db_path: str | None = None):
    """Initialize database schema."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
