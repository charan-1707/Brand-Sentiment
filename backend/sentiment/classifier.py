"""Sentiment classification engine.

Primary backend: TF-IDF + LogisticRegression trained on the Kaggle
Sentiment140 Twitter dataset (see sentiment/train.py). Because that
dataset is binary (positive/negative), predictions whose confidence
falls below the trained neutral_threshold are reported as neutral.
If no trained model exists yet, the engine falls back to VADER.
"""
import json
from pathlib import Path

import joblib

from config import settings
from sentiment.preprocess import clean_text, extract_topics

_TFIDF_PATH = settings.MODELS_DIR / "tfidf_vectorizer.joblib"
_MODEL_PATH = settings.MODELS_DIR / "sentiment_model.joblib"
_META_PATH = settings.MODELS_DIR / "metadata.json"


class SentimentEngine:
    def __init__(self) -> None:
        self.vectorizer = None
        self.model = None
        self.meta: dict = {}
        self._vader = None
        self.load()

    # ---------- lifecycle ----------
    def load(self) -> None:
        if _TFIDF_PATH.exists() and _MODEL_PATH.exists():
            self.vectorizer = joblib.load(_TFIDF_PATH)
            self.model = joblib.load(_MODEL_PATH)
            if _META_PATH.exists():
                self.meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        else:
            self.vectorizer = None
            self.model = None

    @property
    def loaded(self) -> bool:
        return self.vectorizer is not None and self.model is not None

    @property
    def backend(self) -> str:
        return "tfidf_logreg" if self.loaded else "vader_fallback"

    @property
    def neutral_threshold(self) -> float:
        try:
            return float(self.meta.get("neutral_threshold", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def info(self) -> dict:
        trained = list(self.meta.get("classes", [])) or (
            [str(c) for c in self.model.classes_] if self.loaded else [])
        classes = sorted(set(trained)
                         | ({"neutral"} if self.neutral_threshold else set()))
        return {
            "loaded": self.loaded,
            "backend": self.backend,
            "accuracy": self.meta.get("accuracy"),
            "trained_at": self.meta.get("trained_at"),
            "n_features": self.meta.get("n_features"),
            "classes": classes or ["positive", "neutral", "negative"],
            "neutral_threshold": self.neutral_threshold or None,
            "source_file": self.meta.get("source_file"),
            "n_samples": self.meta.get("n_samples"),
        }

    # ---------- prediction ----------
    def _vader(self):
        if self._vader is None:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._vader = SentimentIntensityAnalyzer()
        return self._vader

    def predict(self, text: str) -> tuple:
        """Return (label, confidence) for raw text."""
        cleaned = clean_text(text)
        if self.loaded and cleaned:
            vec = self.vectorizer.transform([cleaned])
            if vec.nnz == 0:
                # no known vocabulary -> abstain as neutral
                return "neutral", 0.5
            proba = self.model.predict_proba(vec)[0]
            idx = int(proba.argmax())
            label = str(self.model.classes_[idx])
            conf = round(float(proba[idx]), 3)
            thr = self.neutral_threshold
            if thr and label in ("positive", "negative") and conf < thr:
                return "neutral", conf
            return label, conf
        score = self._vader().polarity_scores(text or "")["compound"]
        if score >= 0.05:
            return "positive", round(0.5 + abs(score) / 2, 3)
        if score <= -0.05:
            return "negative", round(0.5 + abs(score) / 2, 3)
        return "neutral", round(0.5 + abs(score) / 2, 3)

    def classify(self, text: str) -> dict:
        label, conf = self.predict(text)
        return {
            "sentiment": label,
            "confidence": conf,
            "clean_text": clean_text(text),
            "topics": extract_topics(text),
        }


_engine: SentimentEngine | None = None


def get_engine() -> SentimentEngine:
    global _engine
    if _engine is None:
        _engine = SentimentEngine()
    return _engine


def reload_engine() -> SentimentEngine:
    global _engine
    _engine = SentimentEngine()
    return _engine
