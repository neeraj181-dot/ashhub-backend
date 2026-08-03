from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Handle SQLite vs PostgreSQL engine configuration
connect_args = {}
if "sqlite" in settings.DATABASE_URL.lower():
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if "sqlite" not in settings.DATABASE_URL.lower() else False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency to yield a database session per request
    and ensure proper cleanup upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
