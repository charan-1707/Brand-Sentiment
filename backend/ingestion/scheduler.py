"""Scheduled ingestion jobs (Operating Systems domain).

A background APScheduler job periodically aggregates fresh mentions,
classifies them with the sentiment engine and stores them. Every run
is logged to the ingestion_jobs table. Admins can trigger/pause/resume
via /api/admin/ingest/* endpoints.
"""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

import models
from config import settings
from database import SessionLocal
from ingestion.generator import generate_mentions
from logging_conf import log
from sentiment.classifier import get_engine

_scheduler: BackgroundScheduler | None = None


def run_ingestion_job(batch_size: int | None = None,
                      days: int = 30) -> dict:
    """Aggregate -> classify -> store. Returns a summary dict."""
    db: Session = SessionLocal()
    job = models.IngestionJob(status="running", message="started")
    db.add(job)
    db.commit()
    try:
        engine = get_engine()
        items = generate_mentions(batch_size or settings.INGEST_BATCH_SIZE,
                                  settings.BRAND_NAME, days=days)
        added = 0
        for item in items:
            result = engine.classify(item["text"])
            db.add(models.Mention(
                text=item["text"],
                clean_text=result["clean_text"],
                source=item["source"],
                author=item["author"],
                brand=item["brand"],
                sentiment=result["sentiment"],
                confidence=result["confidence"],
                topics=",".join(result["topics"]),
                posted_at=item["posted_at"],
            ))
            added += 1
        db.commit()
        live_note = ""
        if settings.INGEST_SOURCE == "both":
            # also pull live public mentions (best effort, never fatal)
            from ingestion import real_sources
            try:
                live = real_sources.ingest(db, settings.BRAND_NAME,
                                           limit_each=10)
                added += live["added"]
                live_note = f" | live: {live['added']} ({'; '.join(live['sources'])})"
            except Exception as exc:
                log.warning("live ingestion failed: %s", exc)
                live_note = " | live pull failed (see logs)"
        job.status = "success"
        job.mentions_added = added
        job.message = (
            f"ingested {added} mentions via {engine.backend}{live_note}")[:500]
        job.finished_at = datetime.now()
        db.commit()
        return {"added": added, "backend": engine.backend, "job_id": job.id}
    except Exception as exc:  # never kill the scheduler thread
        db.rollback()
        job.status = "failed"
        job.message = str(exc)[:500]
        job.finished_at = datetime.now()
        db.commit()
        return {"added": 0, "error": str(exc)[:200], "job_id": job.id}
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_ingestion_job,
        "interval",
        minutes=settings.INGEST_EVERY_MINUTES,
        id="mention_ingestion",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()


def scheduler_status() -> dict:
    if _scheduler is None:
        return {"running": False, "state": "stopped",
                "interval_minutes": settings.INGEST_EVERY_MINUTES,
                "batch_size": settings.INGEST_BATCH_SIZE}
    job = _scheduler.get_job("mention_ingestion")
    paused = getattr(job, "next_run_time", None) is None
    return {"running": True, "state": "paused" if paused else "active",
            "interval_minutes": settings.INGEST_EVERY_MINUTES,
            "batch_size": settings.INGEST_BATCH_SIZE,
            "next_run": str(job.next_run_time) if job and job.next_run_time else None}


def pause_scheduler() -> None:
    if _scheduler is not None:
        _scheduler.pause_job("mention_ingestion")


def resume_scheduler() -> None:
    if _scheduler is not None:
        _scheduler.resume_job("mention_ingestion")
