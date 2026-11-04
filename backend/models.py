"""ORM models: users, brand mentions, ingestion jobs, generated reports."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base

# Role constants (also enforced at the API layer)
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_VIEWER = "viewer"
VALID_ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER)

SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEUTRAL = "neutral"
SENTIMENT_NEGATIVE = "negative"
VALID_SENTIMENTS = (SENTIMENT_POSITIVE, SENTIMENT_NEUTRAL, SENTIMENT_NEGATIVE)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=ROLE_VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    reports = relationship("Report", back_populates="author")


class Mention(Base):
    """One aggregated social-media mention of the brand."""

    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=True)
    source = Column(String(30), default="twitter", nullable=False)
    author = Column(String(80), default="anonymous", nullable=False)
    brand = Column(String(80), default="NovaPhone", nullable=False)
    sentiment = Column(String(20), index=True, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    topics = Column(String(500), default="", nullable=False)  # comma separated
    posted_at = Column(DateTime, default=datetime.now, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class IngestionJob(Base):
    """Log row for every (scheduled or manual) ingestion run."""

    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running", nullable=False)
    mentions_added = Column(Integer, default=0, nullable=False)
    message = Column(String(500), default="", nullable=False)


class Report(Base):
    """Metadata for every generated analytics report file."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    format = Column(String(10), nullable=False)  # csv | pdf
    days = Column(Integer, default=30, nullable=False)
    mention_count = Column(Integer, default=0, nullable=False)
    summary = Column(Text, default="{}", nullable=False)  # JSON string
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    author = relationship("User", back_populates="reports")
