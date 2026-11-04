"""Mention Aggregation Service (pipeline stage 2).

Browse/search the aggregated mentions, add one manually, or bulk-import
a CSV. Every stored mention passes through the Sentiment Classification
Engine unless a trusted label is supplied in the CSV.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

import analytics
import models
import schemas
from auth import get_current_user, require_manager
from config import settings
from database import get_db
from ingestion import csv_import
from routers import read_upload_capped
from sentiment.classifier import get_engine
from sentiment.preprocess import extract_topics

router = APIRouter(prefix="/api/mentions", tags=["mentions"])


@router.get("", response_model=schemas.PaginatedMentions, summary="List mentions")
def list_mentions(
    sentiment: str | None = Query(default=None,
                                  description="positive|neutral|negative"),
    topic: str | None = Query(default=None),
    q: str | None = Query(default=None, description="text/author search"),
    days: int = Query(default=365, ge=1, le=3650),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    query = analytics.base_query(db, days)
    if sentiment:
        if sentiment not in models.VALID_SENTIMENTS:
            raise HTTPException(400, "Invalid sentiment filter")
        query = query.filter(models.Mention.sentiment == sentiment)
    if topic:
        query = query.filter(models.Mention.topics.like(f"%{topic}%"))
    if q:
        like = f"%{q}%"
        query = query.filter((models.Mention.text.like(like))
                             | (models.Mention.author.like(like)))
    total = query.count()
    items = (query.order_by(models.Mention.posted_at.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return schemas.PaginatedMentions(total=total, page=page,
                                     page_size=page_size, items=items)


@router.post("", response_model=schemas.MentionOut, status_code=201,
             summary="Add a mention (auto-classified)")
def add_mention(data: schemas.MentionCreate,
                db: Session = Depends(get_db),
                _: models.User = Depends(require_manager)):
    result = get_engine().classify(data.text)
    mention = models.Mention(
        text=data.text[:2000], clean_text=result["clean_text"],
        source=(data.source or "manual")[:30],
        author=(data.author or "anonymous")[:80],
        brand=(data.brand or settings.BRAND_NAME)[:80],
        sentiment=result["sentiment"], confidence=result["confidence"],
        topics=",".join(result["topics"]), posted_at=datetime.now())
    db.add(mention)
    db.commit()
    db.refresh(mention)
    return mention


@router.post("/upload-csv", summary="Bulk import mentions from CSV")
def upload_csv(file: UploadFile = File(...),
               db: Session = Depends(get_db),
               _: models.User = Depends(require_manager)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")
    try:
        rows = csv_import.parse_csv(read_upload_capped(file),
                                    settings.BRAND_NAME)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    engine = get_engine()
    added, trusted = 0, 0
    for row in rows:
        if row["given_sentiment"]:
            sentiment, confidence = row["given_sentiment"], 1.0
            trusted += 1
        else:
            sentiment, confidence = engine.predict(row["text"])
        db.add(models.Mention(
            text=row["text"], clean_text=row["text"].lower(),
            source=row["source"], author=row["author"], brand=row["brand"],
            sentiment=sentiment, confidence=confidence,
            topics=",".join(extract_topics(row["text"])),
            posted_at=row["posted_at"]))
        added += 1
    db.commit()
    return {"added": added, "trusted_labels": trusted,
            "auto_classified": added - trusted}


@router.get("/{mention_id}", response_model=schemas.MentionOut,
            summary="Get one mention")
def get_mention(mention_id: int, db: Session = Depends(get_db),
                _: models.User = Depends(get_current_user)):
    mention = db.query(models.Mention).filter(
        models.Mention.id == mention_id).first()
    if not mention:
        raise HTTPException(404, "Mention not found")
    return mention


@router.delete("/{mention_id}", summary="Delete a mention (manager+)")
def delete_mention(mention_id: int, db: Session = Depends(get_db),
                   _: models.User = Depends(require_manager)):
    mention = db.query(models.Mention).filter(
        models.Mention.id == mention_id).first()
    if not mention:
        raise HTTPException(404, "Mention not found")
    db.delete(mention)
    db.commit()
    return {"msg": f"mention {mention_id} deleted"}
