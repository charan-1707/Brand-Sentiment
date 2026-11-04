"""Shared analytics queries used by the dashboard and report modules."""
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

import models


def range_start(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def base_query(db: Session, days: int):
    return db.query(models.Mention).filter(
        models.Mention.posted_at >= range_start(days))


def summary_stats(db: Session, days: int) -> dict:
    q = base_query(db, days)
    total = q.count()
    pos = q.filter(models.Mention.sentiment == "positive").count()
    neu = q.filter(models.Mention.sentiment == "neutral").count()
    neg = q.filter(models.Mention.sentiment == "negative").count()
    today = db.query(models.Mention).filter(
        models.Mention.posted_at >= datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)).count()
    # most frequent single topic tag
    counter: Counter = Counter()
    for (topics,) in base_query(db, days).with_entities(models.Mention.topics):
        for t in (topics or "").split(","):
            t = t.strip()
            if t:
                counter[t] += 1
    top_topic = counter.most_common(1)[0][0] if counter else None
    return {
        "total_mentions": total,
        "positive": pos, "neutral": neu, "negative": neg,
        "positive_pct": round(100 * pos / total, 1) if total else 0.0,
        "negative_pct": round(100 * neg / total, 1) if total else 0.0,
        "today_count": today,
        "active_complaints": neg,
        "top_topic": top_topic,
    }


def daily_trends(db: Session, days: int) -> list:
    start = range_start(days)
    rows = (
        db.query(func.date(models.Mention.posted_at).label("d"),
                 models.Mention.sentiment, func.count().label("c"))
        .filter(models.Mention.posted_at >= start)
        .group_by("d", models.Mention.sentiment)
        .all()
    )
    by_day: dict = {}
    for d, sentiment, c in rows:
        day = str(d)
        by_day.setdefault(day, {"positive": 0, "neutral": 0, "negative": 0})
        by_day[day][sentiment] = c
    out = []
    for i in range(days):
        day = (datetime.now() - timedelta(days=days - 1 - i)).date().isoformat()
        cell = by_day.get(day, {"positive": 0, "neutral": 0, "negative": 0})
        out.append({"date": day, **cell,
                    "total": cell["positive"] + cell["neutral"] + cell["negative"]})
    return out


def topic_stats(db: Session, days: int, limit: int = 10) -> list:
    counter: Counter = Counter()
    per_topic: dict = {}
    for m in base_query(db, days).with_entities(
            models.Mention.topics, models.Mention.sentiment):
        topics, sentiment = m
        for t in (topics or "").split(","):
            t = t.strip()
            if not t:
                continue
            counter[t] += 1
            cell = per_topic.setdefault(
                t, {"positive": 0, "neutral": 0, "negative": 0})
            if sentiment in cell:
                cell[sentiment] += 1
    return [{"topic": t, "count": counter[t], **per_topic[t]}
            for t, _ in counter.most_common(limit)]


def recent_complaints(db: Session, limit: int = 10, days: int = 30) -> list:
    return (
        base_query(db, days)
        .filter(models.Mention.sentiment == "negative")
        .order_by(models.Mention.posted_at.desc())
        .limit(limit)
        .all()
    )


def source_stats(db: Session, days: int) -> list:
    """Mention counts per origin (twitter/upload/reddit/mastodon/…)."""
    rows = (
        base_query(db, days)
        .with_entities(models.Mention.source, func.count())
        .group_by(models.Mention.source)
        .order_by(func.count().desc())
        .all()
    )
    return [{"source": s or "unknown", "count": c} for s, c in rows]
