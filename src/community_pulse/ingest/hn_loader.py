"""Hacker News data loader."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class HNItem:
    """Parsed Hacker News item."""

    id: int
    type: str  # "story", "comment", "job", "poll"
    by: str | None
    time: datetime
    text: str | None
    title: str | None
    url: str | None
    score: int
    parent: int | None
    kids: list[int]


def parse_hn_item(data: dict) -> HNItem | None:
    """Parse a raw HN API response into an HNItem."""
    if not data or data.get("deleted") or data.get("dead"):
        return None

    item_type = data.get("type", "unknown")
    if item_type not in ("story", "comment"):
        return None

    timestamp = data.get("time", 0)
    posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return HNItem(
        id=data.get("id", 0),
        type=item_type,
        by=data.get("by"),
        time=posted_at,
        text=data.get("text"),
        title=data.get("title"),
        url=data.get("url"),
        score=data.get("score", 0),
        parent=data.get("parent"),
        kids=data.get("kids", []),
    )


def load_hn_items(path: Path) -> list[HNItem]:
    """Load HN items from a JSON file."""
    with open(path) as f:
        raw_items = json.load(f)

    items = []
    for raw in raw_items:
        item = parse_hn_item(raw)
        if item:
            items.append(item)

    return items
