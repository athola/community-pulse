"""Simple keyword-based topic extraction."""

import re
from collections import Counter

# Input validation constants
MAX_TEXT_LENGTH = 100_000  # 100KB limit
MAX_TITLE_LENGTH = 1000

# Common tech topics to extract
TOPIC_PATTERNS: dict[str, list[str]] = {
    "ai": [
        "artificial intelligence",
        "ai ",
        " ai",
        "machine learning",
        "ml ",
        "llm",
        "gpt",
        "chatgpt",
        "claude",
    ],
    "rust": ["rust ", " rust", "rustlang", "cargo"],
    "python": ["python", "django", "fastapi", "flask"],
    "javascript": [
        "javascript",
        "typescript",
        "node.js",
        "nodejs",
        "react",
        "vue",
        "angular",
    ],
    "golang": ["golang", " go ", "go1."],
    "database": [
        "postgres",
        "postgresql",
        "mysql",
        "sqlite",
        "mongodb",
        "redis",
    ],
    "cloud": ["aws", "azure", "gcp", "kubernetes", "k8s", "docker"],
    "security": ["security", "vulnerability", "cve-", "exploit", "breach"],
    "startup": [
        "startup",
        "founder",
        "yc ",
        "y combinator",
        "funding",
        "series a",
    ],
    "open-source": ["open source", "opensource", "github", "gitlab", "foss"],
}


def extract_topics(
    text: str | None, title: str | None = None
) -> list[tuple[str, float]]:
    """Extract topics from text content.

    Returns list of (topic_slug, relevance_score) tuples.
    """
    if not text and not title:
        return []

    # Truncate excessively long inputs to prevent performance issues
    safe_text = (text or "")[:MAX_TEXT_LENGTH]
    safe_title = (title or "")[:MAX_TITLE_LENGTH]

    combined = f"{safe_title} {safe_text}".lower()
    found_topics: list[tuple[str, float]] = []

    for slug, patterns in TOPIC_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                # Simple relevance: title match = 1.0, text match = 0.8
                relevance = 1.0 if safe_title and pattern in safe_title.lower() else 0.8
                found_topics.append((slug, relevance))
                break  # Only count each topic once

    return found_topics


def extract_keywords(text: str | None, top_n: int = 10) -> list[str]:
    """Extract top keywords from text (simple frequency-based)."""
    if not text:
        return []

    # Simple tokenization
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())

    # Filter common words
    stopwords = {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "are",
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "will",
        "would",
        "could",
        "should",
        "can",
        "may",
        "might",
        "must",
        "shall",
        "not",
        "but",
        "you",
        "your",
        "they",
        "their",
        "them",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "only",
        "over",
        "own",
        "same",
    }

    filtered = [w for w in words if w not in stopwords]
    counts = Counter(filtered)

    return [word for word, _ in counts.most_common(top_n)]
