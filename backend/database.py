"""SQLAlchemy engine / session / Base for the MySQL database."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # recover dropped MySQL connections automatically
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (imports models so they register on Base)."""
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
