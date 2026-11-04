"""Text preprocessing + rule-based topic tagging for the NLP pipeline."""
import re

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"@\w+")
_NON_ALPHA_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")

# keyword -> topic tag (checked in order; first matches win, max 3 kept)
# Universal product topics: work for any product/service, not just gadgets.
_TOPIC_KEYWORDS = [
    (("refund", "return", "replace", "exchange"), "refund"),
    (("deliver", "delivery", "shipping", "shipment", "arrived",
      "package", "packaging", "courier"), "delivery"),
    (("support", "helpline", "customer care", "agent"), "support"),
    (("warranty", "guarantee"), "warranty"),
    (("price", "expensive", "cheap", "cost", "overpriced",
      "affordable", "discount"), "price"),
    (("quality", "defective", "damaged", "broke", "broken",
      "durab", "sturdy"), "quality"),
    (("slow", "lag", "freeze", "performance", "speed", "fast",
      "smooth", "responsive"), "performance"),
    (("update", "software", "bug", "crash", "firmware"), "software"),
    (("app", "apps", "website", "site"), "apps"),
    (("design", "look", "color", "colour", "sleek", "premium"), "design"),
    (("stock", "available", "availability", "sold out"), "availability"),
]


def clean_text(text: str) -> str:
    """Lowercase, strip URLs/mentions/hashtags/punctuation for TF-IDF."""
    t = (text or "").lower()
    t = _URL_RE.sub(" ", t)
    t = _MENTION_RE.sub(" ", t)
    t = t.replace("#", "")
    t = _NON_ALPHA_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip()


def extract_topics(text: str) -> list:
    """Return up to 3 topic tags for a mention (keyword based).

    Short keywords (<=3 chars, e.g. 'os', 'app') match whole words only
    so 'post' doesn't tag 'software'; longer ones match substrings.
    """
    t = (text or "").lower()
    words = set(_WS_RE.split(t))
    found = []
    for keywords, tag in _TOPIC_KEYWORDS:
        hit = any((k in words if len(k) <= 3 else k in t) for k in keywords)
        if hit:
            found.append(tag)
        if len(found) == 3:
            break
    return found or ["general"]
