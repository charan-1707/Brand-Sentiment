"""Pydantic v2 request/response schemas for the whole API."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "manager", "viewer"]
Sentiment = Literal["positive", "neutral", "negative"]


# ---------------- Auth / users ----------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=120)
    password: str = Field(min_length=8, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: Role


class UserActiveUpdate(BaseModel):
    is_active: bool


class Login(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------- Mentions ----------------
class MentionCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source: str = Field(default="manual", max_length=30)
    author: Optional[str] = Field(default="anonymous", max_length=80)
    brand: Optional[str] = Field(default=None, max_length=80)


class MentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    source: str
    author: str
    brand: str
    sentiment: str
    confidence: float
    topics: str
    posted_at: datetime
    created_at: datetime


class PaginatedMentions(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[MentionOut]


# ---------------- Dashboard ----------------
class SummaryOut(BaseModel):
    total_mentions: int
    positive: int
    neutral: int
    negative: int
    positive_pct: float
    negative_pct: float
    today_count: int
    active_complaints: int
    top_topic: Optional[str] = None


class TrendPoint(BaseModel):
    date: str
    positive: int
    neutral: int
    negative: int
    total: int


class TopicStat(BaseModel):
    topic: str
    count: int
    positive: int
    neutral: int
    negative: int


class ComplaintOut(BaseModel):
    id: int
    text: str
    author: str
    source: str
    topics: str
    confidence: float
    posted_at: datetime


# ---------------- Reports ----------------
class ReportCreate(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    format: Literal["csv", "pdf"] = "pdf"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    format: str
    days: int
    mention_count: int
    created_at: datetime


# ---------------- Admin / ML / ingestion ----------------
class ModelInfo(BaseModel):
    loaded: bool
    backend: str
    accuracy: Optional[float] = None
    trained_at: Optional[str] = None
    n_features: Optional[int] = None
    classes: List[str] = []
    neutral_threshold: Optional[float] = None
    source_file: Optional[str] = None
    n_samples: Optional[int] = None


class IngestionJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    mentions_added: int
    message: str


class Message(BaseModel):
    msg: str
