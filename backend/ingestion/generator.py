"""Simulated social-media mention generator.

Produces realistic brand mentions spread over the recent past so the
trend dashboard looks alive. Weighted sentiment mix with a slight
recent drift toward complaints (makes the 'trending complaints' panel
meaningful in demos). Product-neutral: works for any tracked brand.
"""
import random
from datetime import datetime, timedelta

SOURCES = ["twitter", "instagram", "reddit", "facebook"]
HANDLES = [
    "shopper_riya", "value_hunter", "deal_digger", "casual_buyer22", "review_raj",
    "brand_fan", "daily_shopper", "unbox_zone", "worth_it_wendy", "quality_check",
    "silent_reader", "early_adopter", "budget_buyer", "curious_case", "gift_hunter",
    "student_sam", "office_kiran", "travel_tara", "feedback_fan", "mom_of_two",
]

_POS = [
    "Absolutely loving my new {brand} product, quality is phenomenal",
    "The {brand} product works perfectly, zero complaints so far",
    "Shoutout to {brand} support, resolved my issue in 10 minutes",
    "Just unboxed my {brand} order and it feels so premium",
    "Got my {brand} order delivered a day early, great service",
    "{brand} keeps getting better with every release",
    "Best value for money right now, {brand} is totally worth it",
    "Two years using {brand} products and still zero complaints",
    "My {brand} experience has been amazing from start to finish",
    "The new {brand} release exceeded all my expectations",
    "Impressed with the premium packaging on my {brand} order",
    "Solid quality from {brand}, exactly as advertised",
]
_NEG = [
    "My {brand} product broke within a week, really disappointed",
    "{brand} support ignored my complaint for a week, pathetic",
    "Regret buying from {brand}, poor quality overall",
    "{brand} delivery took forever and the box arrived damaged",
    "Do not buy this {brand} product, quality is awful for the price",
    "{brand} refused my refund even though the product is defective",
    "The latest {brand} release is a downgrade, very disappointing",
    "Waiting 40 mins on the {brand} helpline with no answer, furious",
    "False advertising, these {brand} specs do not match reality",
    "Return process at {brand} is a nightmare",
    "Overpriced for what it is, {brand} lost a customer",
    "My {brand} order arrived damaged, packaging was useless",
]
_NEU = [
    "Thinking of buying from {brand}, how is the quality",
    "Can someone compare {brand} with rivals in this range",
    "Saw the new {brand} ad, looks interesting",
    "Is the {brand} product available in stores yet",
    "Reading {brand} reviews, opinions seem mixed",
    "What exchange offer is running at {brand} right now",
    "Does {brand} ship internationally or domestic only",
    "Visited a {brand} store today, seems decent",
]

EXTRA_TAGS = ["", "", "", " #{brand}", " @{brand}", " #review", " #shopping"]


def generate_mentions(n: int, brand: str, days: int = 30,
                      seed: int | None = None) -> list:
    rng = random.Random(seed if seed is not None else random.randint(0, 10**9))
    now = datetime.now()
    out = []
    for _ in range(n):
        age_days = int(rng.expovariate(1 / (days / 3)))  # recent-heavy
        age_days = min(age_days, days)
        # drift: older mentions skew positive, recent skew negative
        neg_bias = 0.25 + 0.25 * (1 - age_days / max(days, 1))
        r = rng.random()
        if r < 0.40:
            pool = _POS
        elif r < 0.40 + neg_bias:
            pool = _NEG
        else:
            pool = _NEU
        text = rng.choice(pool).format(brand=brand)
        tag = rng.choice(EXTRA_TAGS).format(brand=brand.replace(" ", ""))
        out.append({
            "text": (text + tag).strip(),
            "source": rng.choice(SOURCES),
            "author": rng.choice(HANDLES) + str(rng.randint(1, 99)),
            "brand": brand,
            "posted_at": now - timedelta(
                days=age_days,
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            ),
        })
    return out
