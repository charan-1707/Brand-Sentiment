"""Trend Visualization Dashboard data API (pipeline stage 4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import analytics
import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.SummaryOut, summary="KPI cards")
def summary(days: int = Query(30, ge=1, le=365),
            db: Session = Depends(get_db),
            _: models.User = Depends(get_current_user)):
    return analytics.summary_stats(db, days)


@router.get("/trends", response_model=list[schemas.TrendPoint],
            summary="Daily sentiment series")
def trends(days: int = Query(30, ge=1, le=365),
            db: Session = Depends(get_db),
            _: models.User = Depends(get_current_user)):
    return analytics.daily_trends(db, days)


@router.get("/distribution", summary="Sentiment share for donut chart")
def distribution(days: int = Query(30, ge=1, le=365),
                 db: Session = Depends(get_db),
                 _: models.User = Depends(get_current_user)):
    s = analytics.summary_stats(db, days)
    return [{"name": "Positive", "value": s["positive"]},
            {"name": "Neutral", "value": s["neutral"]},
            {"name": "Negative", "value": s["negative"]}]


@router.get("/topics", response_model=list[schemas.TopicStat],
            summary="Trending topics with sentiment split")
def topics(days: int = Query(30, ge=1, le=365),
           limit: int = Query(10, ge=1, le=30),
           db: Session = Depends(get_db),
           _: models.User = Depends(get_current_user)):
    return analytics.topic_stats(db, days, limit)


@router.get("/complaints", response_model=list[schemas.ComplaintOut],
            summary="Latest negative mentions")
def complaints(limit: int = Query(10, ge=1, le=50),
               days: int = Query(30, ge=1, le=365),
               db: Session = Depends(get_db),
               _: models.User = Depends(get_current_user)):
    return analytics.recent_complaints(db, limit, days)


@router.get("/sources", summary="Mention counts per origin (provenance)")
def sources(days: int = Query(30, ge=1, le=365),
            db: Session = Depends(get_db),
            _: models.User = Depends(get_current_user)):
    return analytics.source_stats(db, days)
