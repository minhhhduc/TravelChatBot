"""Database configuration for TravelChatBot.

This module sets up the SQLAlchemy engine, session maker, and connection
to the local SQLite database.

Author: TravelChatBot Team
Version: 1.0.0
"""
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Resolve absolute path for database.db
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Create engine with sqlite-specific tuning
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Session local factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def get_db():
    """FastAPI dependency that yields a database session.
    
    FastAPI manages the generator lifecycle, closing the session automatically
    after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_ctx():
    """Context manager for administrative and standalone script database sessions.
    
    Yields a database session, automatically commits changes, rollbacks on error,
    and closes the session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
