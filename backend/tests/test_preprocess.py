"""Unit tests for the NLP preprocessing pipeline (no DB needed)."""
from sentiment.preprocess import clean_text, extract_topics


def test_clean_text_removes_noise():
    out = clean_text("Check this out https://example.com @user #SomeBrand!!")
    assert out == "check this out somebrand"


def test_clean_text_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""


def test_topics_quality():
    assert "quality" in extract_topics("product broke fast, damaged on arrival")


def test_topics_multiple():
    topics = extract_topics("delivery took forever and support ignored me")
    assert "delivery" in topics and "support" in topics


def test_topics_default_general():
    assert extract_topics("just a random hello world post") == ["general"]


def test_topics_capped_at_three():
    text = ("refund delivery support price quality performance update slow "
            "broken warranty exchange")
    assert len(extract_topics(text)) <= 3
