#!/usr/bin/env python3
"""Fetch recent Hacker News data for Community Pulse POC."""

import asyncio
import json
from pathlib import Path

import httpx

HN_API = "https://hacker-news.firebaseio.com/v0"
OUTPUT_DIR = Path("data")


async def fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    """Fetch a single HN item."""
    try:
        resp = await client.get(f"{HN_API}/item/{item_id}.json")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching {item_id}: {e}")
        return None


async def fetch_top_stories(client: httpx.AsyncClient, limit: int = 100) -> list[int]:
    """Fetch top story IDs."""
    resp = await client.get(f"{HN_API}/topstories.json")
    resp.raise_for_status()
    return resp.json()[:limit]


async def fetch_with_comments(
    client: httpx.AsyncClient, story_id: int, max_comments: int = 20
) -> list[dict]:
    """Fetch a story and its top comments."""
    items = []

    story = await fetch_item(client, story_id)
    if story:
        items.append(story)

        # Fetch top comments
        kids = story.get("kids", [])[:max_comments]
        for kid_id in kids:
            comment = await fetch_item(client, kid_id)
            if comment:
                items.append(comment)

    return items


async def main() -> None:
    """Fetch HN data and save to JSON."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Fetching top stories...")
        story_ids = await fetch_top_stories(client, limit=50)

        all_items = []
        for i, story_id in enumerate(story_ids):
            print(f"Fetching story {i + 1}/{len(story_ids)}: {story_id}")
            items = await fetch_with_comments(client, story_id, max_comments=10)
            all_items.extend(items)
            await asyncio.sleep(0.1)  # Be nice to the API

        # Save to file
        output_path = OUTPUT_DIR / "hn_sample.json"
        with open(output_path, "w") as f:
            json.dump(all_items, f, indent=2)

        print(f"Saved {len(all_items)} items to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
