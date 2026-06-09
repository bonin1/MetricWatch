"""
Lightweight keyword-based sentiment analysis (no ML dependencies).
"""
from typing import Tuple

POSITIVE = {
    "good", "great", "excellent", "amazing", "love", "happy", "awesome",
    "fantastic", "wonderful", "best", "perfect", "nice", "beautiful",
}
NEGATIVE = {
    "bad", "terrible", "awful", "hate", "worst", "horrible", "poor",
    "disappointing", "sad", "angry", "broken", "fail", "failed", "slow",
}


def analyze_keyword_sentiment(text: str) -> Tuple[str, float]:
    """Return (sentiment, confidence) using simple lexicon scoring."""
    words = {w.strip(".,!?\"'").lower() for w in text.split()}
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    total = pos + neg

    if total == 0:
        return "neutral", 0.55

    if pos > neg:
        return "positive", min(0.95, 0.6 + 0.1 * (pos - neg))
    if neg > pos:
        return "negative", min(0.95, 0.6 + 0.1 * (neg - pos))
    return "neutral", 0.6
