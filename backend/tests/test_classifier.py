"""Unit tests for the sentiment engine (uses trained artifacts, no DB)."""
from sentiment.classifier import get_engine


def test_engine_uses_trained_model():
    engine = get_engine()
    assert engine.loaded
    assert engine.backend == "tfidf_logreg"


def test_strong_positive():
    label, conf = get_engine().predict(
        "I absolutely love this phone, amazing camera and battery!")
    assert label == "positive"
    assert conf >= 0.6


def test_strong_negative():
    label, conf = get_engine().predict(
        "Terrible phone, worst purchase ever, screen arrived broken")
    assert label == "negative"
    assert conf >= 0.6


def test_neutral_fallback_on_gibberish():
    label, _ = get_engine().predict("xyzzy plugh frobnicate quux wibble")
    assert label == "neutral"


def test_classify_shape():
    out = get_engine().classify("Fast delivery but the product arrived damaged")
    assert set(out) == {"sentiment", "confidence", "clean_text", "topics"}
    assert out["sentiment"] in ("positive", "neutral", "negative")
    assert "delivery" in out["topics"]
