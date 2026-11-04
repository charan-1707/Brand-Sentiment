"""Centralised logging configuration (stdlib only)."""
import logging
import sys


def configure_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # quieten noisy third-party loggers
    for noisy in ("apscheduler", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("brand")


log = logging.getLogger("brand")
