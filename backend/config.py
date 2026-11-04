"""Central application settings loaded from environment / backend/.env.

A tiny .env parser is included so no extra dependency (python-dotenv)
is required. Every value can also be supplied as a real environment
variable, which takes precedence over the .env file.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    # --- runtime environment ---
    APP_ENV: str = _get("APP_ENV", "dev")  # dev | prod
    LOG_LEVEL: str = _get("LOG_LEVEL", "INFO")

    # --- MySQL ---
    MYSQL_HOST: str = _get("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = _get_int("MYSQL_PORT", 3306)
    MYSQL_USER: str = _get("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = _get("MYSQL_PASSWORD", "CHANGE_ME")
    MYSQL_DB: str = _get("MYSQL_DB", "brand_sentiment")
    # Full URL override (Railway/Heroku style), e.g. mysql://user:pass@host:port/db
    DATABASE_URL_OVERRIDE: str = _get("DATABASE_URL", "") or _get("MYSQL_URL", "")

    # --- Auth ---
    SECRET_KEY: str = _get("SECRET_KEY", "change-this-secret-key-for-production-use-a-long-random-string")
    ALGORITHM: str = _get("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 120)

    # --- CORS (comma separated origins) ---
    CORS_ORIGINS: list = [
        o.strip() for o in _get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if o.strip()
    ]
    # Optional regex for wildcard origins (e.g. Vercel preview deployments)
    CORS_ORIGIN_REGEX: str = _get("CORS_ORIGIN_REGEX", "")

    # --- Tracked brand (use a real brand name for live sources; shown in data, not UI) ---
    BRAND_NAME: str = _get("BRAND_NAME", "Brand")

    # --- Scheduled ingestion (Operating Systems domain: background jobs) ---
    INGEST_EVERY_MINUTES: int = _get_int("INGEST_EVERY_MINUTES", 5)
    INGEST_BATCH_SIZE: int = _get_int("INGEST_BATCH_SIZE", 8)
    # simulated = generator only; both = generator + live Reddit/Mastodon pull
    INGEST_SOURCE: str = _get("INGEST_SOURCE", "simulated")

    # --- Upload / abuse guards ---
    MAX_UPLOAD_MB: int = _get_int("MAX_UPLOAD_MB", 25)
    RATE_LIMIT_PER_MIN: int = _get_int("RATE_LIMIT_PER_MIN", 300)

    # --- Training ---
    TRAIN_SAMPLE_ROWS: int = _get_int("TRAIN_SAMPLE_ROWS", 200000)

    # --- Seeded administrator (created on first startup) ---
    ADMIN_USERNAME: str = _get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = _get("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL: str = _get("ADMIN_EMAIL", "admin@brand.local")

    BASE_DIR: Path = BASE_DIR
    MODELS_DIR: Path = BASE_DIR / "models_out"
    REPORTS_DIR: Path = BASE_DIR / "generated_reports"
    DATA_DIR: Path = BASE_DIR / "data"

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            url = self.DATABASE_URL_OVERRIDE
            if url.startswith("mysql://"):
                url = "mysql+pymysql://" + url[len("mysql://"):]
            return url
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            "?charset=utf8mb4"
        )

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() == "prod"


settings = Settings()
