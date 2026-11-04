"""Exportable brand analytics reports (CSV + PDF)."""
import json
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import analytics
import models
from config import settings

# Product-neutral app identity (tracked brand lives in mention data/env)
APP_TITLE = "Brand Sentiment Analyzer"


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _summary(db, days: int) -> dict:
    s = analytics.summary_stats(db, days)
    s["days"] = days
    s["brand"] = settings.BRAND_NAME
    s["generated_at"] = datetime.now().isoformat(timespec="seconds")
    s["top_topics"] = analytics.topic_stats(db, days, limit=5)
    return s


def generate_csv(db, days: int) -> tuple:
    """Write mentions CSV. Returns (filepath, count, summary)."""
    mentions = (analytics.base_query(db, days)
                .order_by(models.Mention.posted_at.desc()).all())
    df = pd.DataFrame([{
        "id": m.id, "posted_at": m.posted_at, "source": m.source,
        "author": m.author, "brand": m.brand, "text": m.text,
        "sentiment": m.sentiment, "confidence": m.confidence,
        "topics": m.topics,
    } for m in mentions])
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.REPORTS_DIR / f"brand_report_{_stamp()}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return str(path), len(df), _summary(db, days)


def generate_pdf(db, days: int) -> tuple:
    """Write a one/multi-page analytics PDF. Returns (filepath, count, summary)."""
    summary = _summary(db, days)
    complaints = analytics.recent_complaints(db, limit=10, days=days)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.REPORTS_DIR / f"brand_report_{_stamp()}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            title=f"{APP_TITLE} - Report")
    story = [
        Paragraph(f"{APP_TITLE} - Report",
                  styles["Title"]),
        Paragraph(
            f"Brand: {summary['brand']} &nbsp;|&nbsp; Period: last {days} days "
            f"&nbsp;|&nbsp; Generated: "
            f"{summary['generated_at']}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Overall sentiment", styles["Heading2"]),
        _table([
            ["Total mentions", summary["total_mentions"]],
            ["Positive", f"{summary['positive']} ({summary['positive_pct']}%)"],
            ["Neutral", summary["neutral"]],
            ["Negative", f"{summary['negative']} ({summary['negative_pct']}%)"],
            ["Mentions today", summary["today_count"]],
            ["Top topic", summary["top_topic"] or "-"],
        ]),
        Spacer(1, 12),
        Paragraph("Top topics", styles["Heading2"]),
        _table([["Topic", "Mentions", "Positive", "Neutral", "Negative"]] + [
            [t["topic"], t["count"], t["positive"], t["neutral"], t["negative"]]
            for t in summary["top_topics"]
        ]),
        Spacer(1, 12),
        Paragraph("Recent complaints (negative mentions)", styles["Heading2"]),
    ]
    for c in complaints:
        story.append(Paragraph(
            f"<b>@{c.author}</b> [{c.source}] "
            f"{c.posted_at.strftime('%Y-%m-%d')}: {c.text[:220]}",
            styles["Normal"]))
        story.append(Spacer(1, 6))
    if not complaints:
        story.append(Paragraph("No complaints in this period.", styles["Normal"]))
    doc.build(story)
    return str(path), summary["total_mentions"], summary


def _table(rows: list) -> Table:
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def summary_json(summary: dict) -> str:
    return json.dumps(summary, indent=2, default=str)
