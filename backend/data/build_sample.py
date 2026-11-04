"""Builds data/sample_tweets.csv - a bundled, Kaggle-style labelled dataset.

Handcrafted polarised templates x products/variants (deterministic seed)
so the project trains a real model offline. To use the actual Kaggle
Twitter Sentiment dataset instead, download it and place it at
backend/data/kaggle_twitter.csv (sentiment140 format: target,text where
target is 0/2/4) - the trainer and /api/admin/retrain endpoint will pick
it up automatically.
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sample_tweets.csv"
BRANDS = ["NovaPhone", "novaphone", "Nova Phone"]
PRODUCTS = ["NovaPhone 15", "Nova Buds Pro", "Nova Watch 2", "NovaBook Air"]

POS = [
    "I absolutely love my {p}! Best purchase ever {b}",
    "{b} {p} is amazing, battery lasts two full days",
    "Just got the {p} and the camera quality is stunning {b}",
    "Huge shoutout to {b} support, they fixed my issue in minutes",
    "The {p} exceeded all my expectations, super fast and smooth",
    "{b} delivery was super quick, arrived a day early!",
    "Really impressed with {b}, great value for the price",
    "My {p} looks premium and feels great in hand, love it",
    "{b} customer service is the best I have ever experienced",
    "Switched to {p} and I am never going back, fantastic phone",
    "The display on my {p} is gorgeous, colors really pop {b}",
    "Got a great discount on {p}, totally worth every penny",
    "{b} nailed it with this update, everything is smoother now",
    "Battery backup on {p} is insane, easily lasts me all day",
    "Unboxing the {p} was such a delight, premium packaging {b}",
    "Performance of {p} is top notch, no lag at all",
    "{b} replaced my damaged unit without any hassle, great service",
    "The camera on {p} takes incredible night shots, blown away",
    "Loving the new features on my {p}, {b} keeps improving",
    "Affordable and powerful, {p} is the perfect budget flagship {b}",
    "Sound quality of {p} is crystal clear, highly recommend",
    "Setup of my {p} took five minutes, so easy {b}",
    "Three years with {b} products and zero complaints so far",
    "{p} charges from 0 to 100 in under an hour, crazy fast",
    "The design of {p} is sleek and modern, getting compliments {b}",
]

NEG = [
    "Terrible experience with {b}, my {p} stopped working in a week",
    "Worst customer support ever, {b} ignored my complaint for days",
    "My {p} battery drains in 3 hours, completely useless {b}",
    "Regret buying {p}, camera is blurry and full of noise",
    "{b} delivery took three weeks and the box arrived damaged",
    "Overpriced junk, {p} lags like a five year old phone",
    "Never buying {b} again, they refused my refund request",
    "{p} overheats constantly, cannot even hold it {b}",
    "The latest {b} update bricked my {p}, furious right now",
    "Screen cracked within a month, {p} build quality is awful",
    "{b} support hung up on me twice, pathetic service",
    "Do not waste your money on {p}, total disappointment",
    "My {p} keeps freezing and crashing every single day {b}",
    "Charging port on {p} broke after two months, cheap quality",
    "{b} promised a replacement but ghosted me after payment",
    "Speaker on {p} sounds muffled and distorted, avoid it",
    "False advertising by {b}, {p} does not match the specs at all",
    "Waiting 40 minutes on {b} helpline and still no answer",
    "{p} storage fills up so fast, worst purchase decision",
    "Return process for {p} is a nightmare, {b} keeps delaying",
    "My {p} arrived with scratches all over, disgusting packaging",
    "{b} pushed a buggy update and now my apps keep crashing",
    "Battery swelled up on my {p}, dangerous product {b}",
    "Paid premium price for {p} and got budget performance",
    "Software on {p} is full of bloatware and ads, shame {b}",
]

NEU = [
    "Thinking of buying {p}, is the battery really that good {b}",
    "Can anyone compare {p} with other phones in this range",
    "Just saw the {b} ad for {p}, looks interesting",
    "Does {p} support wireless charging, asking for a friend",
    "{b} launched a new color variant of {p} today",
    "What is the exchange offer on {p} right now",
    "Visited the {b} store to check out {p}, seems decent",
    "Is {p} available in offline stores yet",
    "Reading reviews of {p} before deciding, mixed opinions so far",
    "How long does {b} usually take to deliver {p}",
    "Anyone knows the service center timings for {b}",
    "Considering {p} vs its competitor, need suggestions",
    "The {b} event announcing {p} starts at 12pm today",
    "{p} comes in three storage options apparently",
    "Wondering if {p} will get the next major OS update",
]

SUFFIXES = ["", "", "", " #NovaPhone", " @NovaPhone", " :)", " :(", "!!", "...", " #tech"]


def build(seed: int = 42) -> Path:
    rng = random.Random(seed)
    rows = []

    def add(templates, label):
        per = 26  # rows per template -> balanced classes
        for t in templates:
            for _ in range(per):
                b = rng.choice(BRANDS)
                p = rng.choice(PRODUCTS)
                text = t.format(b=b, p=p) + rng.choice(SUFFIXES)
                rows.append((label, text.strip()))

    add(POS, "positive")
    add(NEG, "negative")
    add(NEU, "neutral")
    # trim neutral to keep balance reasonable (~POS count each)
    rng.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "text"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT}")
    return OUT


if __name__ == "__main__":
    build()
