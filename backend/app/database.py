"""SQLAlchemy engine and session factory.

Uses DATABASE_URL from environment with a fallback to local SQLite.
Synchronous SQLAlchemy is used for simplicity and broad compatibility.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# Handle SQLite-specific connect args (check_same_thread is SQLite-only)
connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def get_db():
    """FastAPI dependency that yields a database session.

    Ensures the session is closed after the request completes, even if
    an exception is raised.

    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
