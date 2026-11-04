"""Report Generation (pipeline stage 5): CSV + PDF exports."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, require_manager
from database import get_db
from reports import generator as reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=schemas.ReportOut, status_code=201,
             summary="Generate a report (manager+)")
def create_report(data: schemas.ReportCreate,
                  db: Session = Depends(get_db),
                  user: models.User = Depends(require_manager)):
    if data.format == "csv":
        path, count, summary = reports.generate_csv(db, data.days)
    else:
        path, count, summary = reports.generate_pdf(db, data.days)
    row = models.Report(filename=Path(path).name, format=data.format,
                        days=data.days, mention_count=count,
                        summary=reports.summary_json(summary),
                        created_by=user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[schemas.ReportOut],
            summary="List generated reports")
def list_reports(db: Session = Depends(get_db),
                 _: models.User = Depends(get_current_user)):
    return db.query(models.Report).order_by(
        models.Report.created_at.desc()).limit(50).all()


@router.get("/{report_id}/download", summary="Download a report file")
def download_report(report_id: int, db: Session = Depends(get_db),
                    _: models.User = Depends(get_current_user)):
    from config import settings

    row = db.query(models.Report).filter(
        models.Report.id == report_id).first()
    if not row:
        raise HTTPException(404, "Report not found")
    path = settings.REPORTS_DIR / row.filename
    if not path.exists():
        raise HTTPException(404, "Report file missing on server")
    media = ("text/csv" if row.format == "csv" else "application/pdf")
    return FileResponse(path, media_type=media, filename=row.filename)


@router.delete("/{report_id}", summary="Delete a report (manager+)")
def delete_report(report_id: int, db: Session = Depends(get_db),
                  _: models.User = Depends(require_manager)):
    from config import settings

    row = db.query(models.Report).filter(
        models.Report.id == report_id).first()
    if not row:
        raise HTTPException(404, "Report not found")
    try:
        os.remove(settings.REPORTS_DIR / row.filename)
    except OSError:
        pass
    db.delete(row)
    db.commit()
    return {"msg": f"report {report_id} deleted"}
