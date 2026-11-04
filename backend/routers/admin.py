"""Admin controls: model retraining + ingestion scheduler (admin only)."""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
from auth import require_admin
from config import settings
from database import get_db
from ingestion import scheduler as ingestion
from routers import read_upload_capped
from sentiment.classifier import get_engine, reload_engine

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/model", response_model=schemas.ModelInfo,
            summary="Sentiment model info")
def model_info(_: models.User = Depends(require_admin)):
    return get_engine().info()


@router.post("/retrain", summary="Retrain on bundled or uploaded Kaggle CSV")
def retrain(file: UploadFile | None = File(default=None),
            db_unused: Session = Depends(get_db),  # keeps OpenAPI auth uniform
            _: models.User = Depends(require_admin)):
    from sentiment import train as trainer

    csv_path = None
    if file is not None:
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(400, "Only .csv files are accepted")
        tmp = Path(tempfile.gettempdir()) / "kaggle_upload.csv"
        tmp.write_bytes(read_upload_capped(file))
        csv_path = str(tmp)
    try:
        meta = trainer.train(csv_path)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc))
    reload_engine()
    return {"msg": "model retrained", **meta,
            "active_backend": get_engine().backend}


@router.get("/ingest/status", summary="Scheduler status")
def ingest_status(_: models.User = Depends(require_admin)):
    return ingestion.scheduler_status()


@router.post("/ingest/trigger", summary="Run an ingestion batch now")
def ingest_trigger(batch: int = Query(default=8, ge=1, le=500),
                   _: models.User = Depends(require_admin)):
    return ingestion.run_ingestion_job(batch_size=batch)


@router.post("/seed-demo", summary="Populate 30 days of demo mentions")
def seed_demo(_: models.User = Depends(require_admin)):
    return ingestion.run_ingestion_job(batch_size=150, days=30)


@router.post("/ingest/real", summary="Pull REAL mentions (Reddit + Mastodon)")
def ingest_real(brand: str | None = Query(
                    default=None, description="defaults to BRAND_NAME"),
                limit_each: int = Query(default=25, ge=1, le=50),
                db: Session = Depends(get_db),
                _: models.User = Depends(require_admin)):
    from ingestion import real_sources

    return real_sources.ingest(db, brand or settings.BRAND_NAME, limit_each)


@router.post("/ingest/pause", summary="Pause scheduled ingestion")
def ingest_pause(_: models.User = Depends(require_admin)):
    ingestion.pause_scheduler()
    return {"msg": "scheduler paused"}


@router.post("/ingest/resume", summary="Resume scheduled ingestion")
def ingest_resume(_: models.User = Depends(require_admin)):
    ingestion.resume_scheduler()
    return {"msg": "scheduler resumed"}


@router.get("/ingest/jobs", response_model=list[schemas.IngestionJobOut],
            summary="Recent ingestion runs")
def ingest_jobs(limit: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db),
                _: models.User = Depends(require_admin)):
    return (db.query(models.IngestionJob)
            .order_by(models.IngestionJob.started_at.desc())
            .limit(limit).all())


@router.post("/reset", summary="Wipe all mention data (demo reset)")
def reset_data(db: Session = Depends(get_db),
               _: models.User = Depends(require_admin)):
    """Clean-slate for demos: mentions, jobs and reports are wiped.

    Users / logins / roles and the trained model are preserved,
    so the app can be repopulated from zero (seed-demo, CSV, live pull).
    """
    counts = {
        "mentions": db.query(models.Mention).delete(),
        "jobs": db.query(models.IngestionJob).delete(),
        "reports": db.query(models.Report).delete(),
    }
    db.commit()
    files = 0
    if settings.REPORTS_DIR.exists():
        for f in settings.REPORTS_DIR.glob("brand_report_*"):
            f.unlink(missing_ok=True)
            files += 1
    return {"msg": "all demo data wiped - clean slate", **counts,
            "files_deleted": files}
