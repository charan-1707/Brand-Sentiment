"""Parse an uploaded mentions CSV into normalized dicts.

Accepted (case-insensitive) columns:
  text (required; also accepts: content, tweet, message, post)
  sentiment/label (optional: positive/neutral/negative or 0/2/4)
  author/user (optional), source (optional), posted_at/date (optional),
  brand (optional)
"""
import csv
import io
from datetime import datetime

_TEXT_COLS = ("text", "content", "tweet", "message", "post")
_LABEL_MAP = {"positive": "positive", "negative": "negative", "neutral": "neutral",
              "pos": "positive", "neg": "negative", "neu": "neutral",
              "0": "negative", "2": "neutral", "4": "positive"}


def _pick(row: dict, names: tuple, default=None):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return default


def parse_csv(content: bytes, default_brand: str) -> list:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("Empty CSV file")
    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
    rows = []
    for i, row in enumerate(reader, start=2):
        raw_text = _pick(row, _TEXT_COLS)
        if not raw_text or not str(raw_text).strip():
            continue  # skip blank lines
        raw_label = _pick(row, ("sentiment", "label"))
        label = _LABEL_MAP.get(str(raw_label).strip().lower()) if raw_label else None
        posted = _pick(row, ("posted_at", "date", "created_at", "timestamp"))
        posted_at = None
        if posted:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y",
                        "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y %H:%M"):
                try:
                    posted_at = datetime.strptime(str(posted).strip(), fmt)
                    break
                except ValueError:
                    continue
        rows.append({
            "text": str(raw_text).strip()[:2000],
            "given_sentiment": label,
            "author": str(_pick(row, ("author", "user", "username"),
                                "csv_user")).strip()[:80] or "csv_user",
            "source": str(_pick(row, ("source", "platform"),
                                "upload")).strip().lower()[:30] or "upload",
            "brand": str(_pick(row, ("brand",), default_brand)).strip()[:80]
            or default_brand,
            "posted_at": posted_at or datetime.now(),
            "line": i,
        })
    if not rows:
        raise ValueError("No valid mention rows found in CSV")
    return rows
