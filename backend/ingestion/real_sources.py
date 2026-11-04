"""Live data connectors: pull REAL public mentions (no API keys needed).

Each fetcher returns (items, note) and never raises - a dead source only
produces a note, never a failed ingestion. Sources tried:

  * HackerNews  - Algolia search API, tech stories (very reliable)
  * Reddit      - public search RSS feeds (no auth)
  * Mastodon    - open public timelines of several instances, keyword match
  * Bluesky     - public search API (network-dependent, opportunistic)
  * GDELT       - world news API, article titles (opportunistic)

Tip: BRAND_NAME is configurable in backend/.env (default "Brand") for
scheduled pulls; the Admin UI accepts any brand per pull (e.g. Samsung).
"""
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

import models
from logging_conf import log
from sentiment.classifier import get_engine
from sentiment.preprocess import extract_topics

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0 Safari/537.36"}
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None, limit: int = 1000) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text))).strip()[:limit]


def _parse_dt(value, default_now: bool = True) -> datetime:
    if not value:
        return datetime.now() if default_now else None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        s = str(value).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError, OSError):
        return datetime.now()


# ---------------- HackerNews ----------------
def fetch_hn(brand: str, limit: int = 25, timeout: int = 15):
    try:
        r = httpx.get("https://hn.algolia.com/api/v1/search",
                      params={"query": brand, "tags": "story"},
                      headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return [], f"hackernews http {r.status_code}"
        items = []
        for h in r.json().get("hits", [])[:limit]:
            title = _clean(h.get("title"), 500)
            if len(title) < 10:
                continue
            items.append({"text": f"{title} ({h.get('points', 0)} points on HN)",
                          "author": str(h.get("author") or "hn_user")[:80],
                          "source": "hackernews", "brand": brand,
                          "posted_at": _parse_dt(h.get("created_at"))})
        return items, f"hackernews ok ({len(items)} found)"
    except Exception as exc:
        log.warning("hn fetch failed: %s", exc)
        return [], f"hackernews error: {str(exc)[:120]}"


# ---------------- Reddit (public RSS) ----------------
def fetch_reddit(brand: str, limit: int = 25, timeout: int = 20):
    try:
        r = httpx.get("https://www.reddit.com/search.rss",
                      params={"q": brand, "sort": "new",
                              "limit": max(1, min(limit, 25))},
                      headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200 or not r.text.strip().startswith("<"):
            return [], f"reddit http {r.status_code}"
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(r.text)
        items = []
        for entry in root.findall("a:entry", ns)[:limit]:
            title = _clean(entry.findtext("a:title", "", ns), 500)
            author_el = entry.find("a:author/a:name", ns)
            if len(title) < 10:
                continue
            items.append({"text": title,
                          "author": str(author_el.text if author_el is not None
                                        else "redditor")[:80],
                          "source": "reddit", "brand": brand,
                          "posted_at": _parse_dt(
                              entry.findtext("a:updated", "", ns))})
        return items, f"reddit ok ({len(items)} found)"
    except Exception as exc:
        log.warning("reddit fetch failed: %s", exc)
        return [], f"reddit error: {str(exc)[:120]}"


# ---------------- Mastodon (open instances) ----------------
_INSTANCES = ("mastodon.world", "mas.to", "fosstodon.org",
              "infosec.exchange", "mstdn.social")


def fetch_mastodon(brand: str, limit: int = 40, timeout: int = 15):
    tried = []
    for host in _INSTANCES:
        try:
            r = httpx.get(f"https://{host}/api/v1/timelines/public",
                          params={"limit": max(1, min(limit, 40))},
                          headers=_UA, timeout=timeout, follow_redirects=True)
            if r.status_code != 200:
                tried.append(f"{host}:{r.status_code}")
                continue
            items = []
            for s in r.json():
                text = _clean(s.get("content"), 1000)
                if brand.lower() not in text.lower() or len(text) < 10:
                    continue
                items.append({
                    "text": text,
                    "author": str((s.get("account") or {}).get("acct")
                                  or "mastodon_user")[:80],
                    "source": "mastodon", "brand": brand,
                    "posted_at": _parse_dt(s.get("created_at"))})
            return items, f"mastodon ok via {host} ({len(items)} matching)"
        except Exception as exc:
            tried.append(f"{host}:err")
            log.warning("mastodon %s failed: %s", host, exc)
    return [], f"mastodon unreachable ({', '.join(tried)[:120]})"


# ---------------- Bluesky (opportunistic) ----------------
def fetch_bluesky(brand: str, limit: int = 25, timeout: int = 15):
    try:
        r = httpx.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                      params={"q": brand, "limit": max(1, min(limit, 25))},
                      headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return [], f"bluesky http {r.status_code}"
        items = []
        for p in r.json().get("posts", [])[:limit]:
            rec = p.get("record") or {}
            text = _clean(rec.get("text"), 1000)
            if len(text) < 10:
                continue
            items.append({
                "text": text,
                "author": str((p.get("author") or {}).get("handle")
                              or "bsky_user")[:80],
                "source": "bluesky", "brand": brand,
                "posted_at": _parse_dt(rec.get("createdAt"))})
        return items, f"bluesky ok ({len(items)} found)"
    except Exception as exc:
        log.warning("bluesky fetch failed: %s", exc)
        return [], f"bluesky error: {str(exc)[:120]}"


# ---------------- GDELT world news (opportunistic) ----------------
def fetch_gdelt(brand: str, limit: int = 20, timeout: int = 25):
    try:
        r = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",
                      params={"query": brand, "mode": "artlist",
                              "maxrecords": max(1, min(limit, 50)),
                              "format": "json"},
                      headers=_UA, timeout=timeout, follow_redirects=True)
        data = r.json() if r.status_code == 200 else {}
        articles = data.get("articles") or []
        items = []
        for a in articles[:limit]:
            title = _clean(a.get("title"), 500)
            if len(title) < 10:
                continue
            items.append({
                "text": f"{title} - {a.get('domain', 'news')}",
                "author": str(a.get("domain") or "news")[:80],
                "source": "news", "brand": brand,
                "posted_at": _parse_dt(a.get("seendate"))})
        return items, f"news/gdelt ok ({len(items)} found)"
    except Exception as exc:
        log.warning("gdelt fetch failed: %s", exc)
        return [], f"news/gdelt error: {str(exc)[:120]}"


_FETCHERS = (fetch_hn, fetch_reddit, fetch_mastodon, fetch_bluesky,
             fetch_gdelt)


def ingest(db: Session, brand: str, limit_each: int = 25) -> dict:
    """Fetch -> classify -> store. Never raises; returns a summary."""
    engine = get_engine()
    items, details = [], []
    for fetcher in _FETCHERS:
        found, note = fetcher(brand, limit_each)
        details.append(note)
        items.extend(found)
    added = 0
    for item in items:
        label, conf = engine.predict(item["text"])
        db.add(models.Mention(
            text=item["text"], clean_text=item["text"].lower(),
            source=item["source"], author=item["author"], brand=item["brand"],
            sentiment=label, confidence=conf,
            topics=",".join(extract_topics(item["text"])),
            posted_at=item["posted_at"]))
        added += 1
    if added:
        db.commit()
    return {"added": added, "sources": details, "backend": engine.backend}
