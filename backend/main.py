"""Brand Sentiment Dashboard API (production).

Pipeline (see architecture diagram):
  User -> Auth & Role Mgmt -> Mention Aggregation -> Sentiment
  Classification Engine -> Trend Visualization Dashboard ->
  Report Generation -> Output/Dashboard

Interactive docs: http://localhost:8000/docs
Readiness probe:  GET /api/ready
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

import auth
import models
from config import settings
from database import SessionLocal, engine, get_db, init_db
from ingestion import scheduler as ingestion
from logging_conf import configure_logging, log
from middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from routers import admin, auth as auth_router, dashboard, mentions, reports

configure_logging(settings.LOG_LEVEL)

app = FastAPI(
    title="Brand Sentiment Dashboard API",
    description="Aggregate brand mentions, classify sentiment (NLP), "
                "visualize trends and export analytics reports.",
    version="1.0.0",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware,
                   max_requests=settings.RATE_LIMIT_PER_MIN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(mentions.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def unhandled_exception(request, exc):  # noqa: ARG001
    log.exception("unhandled error on %s", request.url.path)
    detail = "Internal server error. Please try again later."
    if not settings.is_prod:
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse({"detail": detail}, status_code=500)


@app.get("/api/health", tags=["meta"], summary="Liveness check")
def health():
    return {"status": "ok", "brand": settings.BRAND_NAME}


@app.get("/api/ready", tags=["meta"], summary="Readiness probe (DB + model)")
def ready():
    from sentiment.classifier import get_engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        log.warning("readiness: db unavailable: %s", exc)
        db_ok = False
    model_backend = get_engine().backend
    ok = db_ok and model_backend != "missing"
    return JSONResponse(
        {"ready": ok, "db": db_ok, "model": model_backend,
         "brand": settings.BRAND_NAME},
        status_code=200 if ok else 503)


@app.get("/api/config", tags=["meta"], summary="Public frontend config")
def config():
    from sentiment.classifier import get_engine

    info = get_engine().info()
    return {"brand": settings.BRAND_NAME,
            "ingest_every_minutes": settings.INGEST_EVERY_MINUTES,
            "ingest_source": settings.INGEST_SOURCE,
            "model_backend": info["backend"],
            "model_accuracy": info["accuracy"],
            "model_source": info.get("source_file"),
            "model_samples": info.get("n_samples")}


def ensure_admin(db: Session) -> None:
    if db.query(models.User).filter(
            models.User.username == settings.ADMIN_USERNAME).first():
        return
    db.add(models.User(
        username=settings.ADMIN_USERNAME, email=settings.ADMIN_EMAIL,
        hashed_password=auth.hash_password(settings.ADMIN_PASSWORD),
        role=models.ROLE_ADMIN))
    db.commit()
    log.info("seeded admin user '%s'", settings.ADMIN_USERNAME)


@app.on_event("startup")
def on_startup() -> None:
    if settings.SECRET_KEY.startswith("change-this"):
        log.warning("SECRET_KEY is the default value - set a strong "
                    "secret in backend/.env before production use!")
    if settings.MYSQL_PASSWORD == "CHANGE_ME":
        log.warning("MYSQL_PASSWORD is still the placeholder - "
                    "set the real password in backend/.env")
    try:
        init_db()
    except Exception as exc:
        log.error("cannot reach MySQL - check backend/.env credentials "
                  "and that the MySQL service is running: %s", exc)
        return
    db = SessionLocal()
    try:
        ensure_admin(db)
    finally:
        db.close()
    from sentiment.classifier import get_engine
    log.info("sentiment backend: %s", get_engine().backend)
    ingestion.start_scheduler()
    log.info("ingestion every %s min, batch=%s, source=%s",
             settings.INGEST_EVERY_MINUTES, settings.INGEST_BATCH_SIZE,
             settings.INGEST_SOURCE)
