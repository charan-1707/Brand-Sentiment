"""Train the TF-IDF + LogisticRegression sentiment model (production).

Dataset priority:
  1. backend/data/kaggle_twitter.csv
     - real Kaggle/Sentiment140 file: headerless target,text (target 0/4), or
       full sentiment140 6-column format (target,ids,date,flag,user,text)
     - bundled-sample header format (label,text) also accepted
  2. backend/data/sample_tweets.csv (bundled labelled data)

Large real datasets are stratified-sampled (TRAIN_SAMPLE_ROWS, default
200k) so training stays fast. Sentiment140 has no neutral class, so a
neutral_threshold is stored in metadata: at inference time, low-confidence
binary predictions fall back to neutral (see sentiment/classifier.py).

Usage:
    cd backend
    python sentiment/train.py
    python sentiment/train.py --csv data/kaggle_twitter.csv --sample-rows 300000
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from config import settings
from sentiment.preprocess import clean_text

NEUTRAL_THRESHOLD = 0.6  # below this binary confidence -> neutral

_LABEL_MAP = {
    "0": "negative", "4": "positive", "2": "neutral",
    0: "negative", 4: "positive", 2: "neutral",
    "negative": "negative", "positive": "positive", "neutral": "neutral",
}

_TFIDF_PATH = settings.MODELS_DIR / "tfidf_vectorizer.joblib"
_MODEL_PATH = settings.MODELS_DIR / "sentiment_model.joblib"
_META_PATH = settings.MODELS_DIR / "metadata.json"


def find_dataset(explicit: str | None = None) -> tuple[Path, str]:
    if explicit:
        return Path(explicit), "explicit"
    kaggle = settings.DATA_DIR / "kaggle_twitter.csv"
    if kaggle.exists():
        return kaggle, "kaggle-sentiment140"
    return settings.DATA_DIR / "sample_tweets.csv", "bundled-sample"


def _read_sentiment140(path: Path) -> pd.DataFrame | None:
    """Try headerless sentiment140 parsing (6-col full or 2-col compact)."""
    try:
        peek = pd.read_csv(path, header=None, encoding="latin-1",
                           nrows=5, on_bad_lines="skip")
    except Exception:
        return None
    ncols = peek.shape[1]
    first = str(peek.iloc[0, 0]).strip().strip('"')
    if ncols in (2, 6) and first in ("0", "2", "4"):
        text_col = 1 if ncols == 2 else 5
        df = pd.read_csv(path, header=None, encoding="latin-1",
                         usecols=[0, text_col], names=["target", "text"],
                         on_bad_lines="skip")
        return pd.DataFrame({"label": df["target"], "text": df["text"]})
    return None


def load_frame(path: Path) -> pd.DataFrame:
    df = _read_sentiment140(path)
    if df is None:
        raw = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        cols = [c.lower() for c in raw.columns]
        if "label" in cols and "text" in cols:
            df = pd.DataFrame({
                "label": raw[raw.columns[cols.index("label")]],
                "text": raw[raw.columns[cols.index("text")]]})
        else:
            df = pd.DataFrame({"label": raw.iloc[:, 0], "text": raw.iloc[:, 1]})
    df["label"] = df["label"].astype(str).str.strip().map(_LABEL_MAP)
    df = df.dropna(subset=["label", "text"])
    df = df[df["label"].isin(["positive", "neutral", "negative"])]
    df["text"] = df["text"].astype(str)
    df["clean"] = df["text"].apply(clean_text)
    return df[df["clean"].str.len() > 0].reset_index(drop=True)


def stratified_sample(df: pd.DataFrame, total: int) -> pd.DataFrame:
    classes = sorted(df["label"].unique())
    per = max(1000, total // len(classes))
    parts = [g.sample(n=min(len(g), per), random_state=42)
             for _, g in df.groupby("label")]
    out = pd.concat(parts).sample(frac=1.0, random_state=42).reset_index(drop=True)
    print(f"stratified sample: {len(out)} rows "
          f"({out['label'].value_counts().to_dict()})")
    return out


def train(csv_path: str | None = None,
          sample_rows: int | None = None) -> dict:
    path, source = find_dataset(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Run `python data/build_sample.py` first.")
    df = load_frame(path)
    print(f"dataset: {path.name} (source={source}) rows={len(df)}")
    print(df["label"].value_counts().to_dict())

    if sample_rows is None:
        try:
            sample_rows = int(os.environ.get("TRAIN_SAMPLE_ROWS", "200000"))
        except ValueError:
            sample_rows = 200000
    if len(df) > sample_rows:
        df = stratified_sample(df, sample_rows)

    binary = set(df["label"].unique()) <= {"positive", "negative"}
    X_train, X_test, y_train, y_test = train_test_split(
        df["clean"], df["label"], test_size=0.2,
        random_state=42, stratify=df["label"])
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=15000,
                                 min_df=3, sublinear_tf=True)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(vectorizer.fit_transform(X_train), y_train)
    pred = clf.predict(vectorizer.transform(X_test))
    acc = float(accuracy_score(y_test, pred))
    print(f"accuracy: {acc:.4f}")
    print(classification_report(y_test, pred))

    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, _TFIDF_PATH)
    joblib.dump(clf, _MODEL_PATH)
    meta = {
        "accuracy": round(acc, 4),
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "n_samples": len(df),
        "classes": sorted(df["label"].unique().tolist()),
        "n_features": len(vectorizer.vocabulary_),
        "source_file": path.name,
        "neutral_threshold": NEUTRAL_THRESHOLD if binary else 0.0,
    }
    _META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"saved model -> {settings.MODELS_DIR}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--sample-rows", type=int, default=None)
    args = ap.parse_args()
    train(args.csv, args.sample_rows)
