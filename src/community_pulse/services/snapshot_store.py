"""Snapshot storage for temporal velocity calculation.

Stores topic mention counts over time to enable true velocity calculation
(current mentions vs. historical baseline for the same topic).
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Minimum time between snapshots (1 hour = 24 snapshots covers 24 hours)
MIN_SNAPSHOT_INTERVAL = timedelta(hours=1)

# Default storage location (can be overridden)
DEFAULT_SNAPSHOT_DIR = Path.home() / ".community_pulse" / "snapshots"


@dataclass
class TopicSnapshot:
    """A snapshot of a single topic's metrics at a point in time."""

    slug: str
    mention_count: int
    unique_authors: int
    timestamp: str  # ISO format


@dataclass
class PulseSnapshot:
    """A complete snapshot of all topics at a point in time."""

    timestamp: str  # ISO format
    topics: dict[str, TopicSnapshot]  # slug -> snapshot


class SnapshotStore:
    """Simple file-based snapshot storage for POC.

    Stores snapshots as JSON files, one per capture.
    Keeps only the most recent N snapshots to avoid unbounded growth.
    """

    def __init__(
        self,
        storage_dir: Path | None = None,
        max_snapshots: int = 24,  # ~24 hours of hourly snapshots
    ):
        """Initialize the snapshot store.

        Args:
            storage_dir: Directory to store snapshots
                (default: ~/.community_pulse/snapshots)
            max_snapshots: Maximum number of snapshots to keep

        """
        self.storage_dir = storage_dir or DEFAULT_SNAPSHOT_DIR
        self.max_snapshots = max_snapshots
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, timestamp: str) -> Path:
        """Get path for a snapshot file."""
        # Use timestamp as filename (sanitized for filesystem)
        safe_ts = timestamp.replace(":", "-").replace("+", "_")
        return self.storage_dir / f"snapshot_{safe_ts}.json"

    def should_save_snapshot(self) -> bool:
        """Check if enough time has passed since the last snapshot.

        Returns:
            True if no snapshots exist or MIN_SNAPSHOT_INTERVAL has passed

        """
        snapshots = sorted(self.storage_dir.glob("snapshot_*.json"))
        if not snapshots:
            return True

        # Get timestamp from latest snapshot filename
        latest_path = snapshots[-1]
        try:
            with open(latest_path) as f:
                data = json.load(f)
            last_timestamp = datetime.fromisoformat(data["timestamp"])
            elapsed = datetime.now(timezone.utc) - last_timestamp
            return elapsed >= MIN_SNAPSHOT_INTERVAL
        except (json.JSONDecodeError, KeyError, OSError, ValueError) as e:
            logger.warning(f"Failed to read snapshot timestamp: {e}")
            return True  # Save if we can't determine last time

    def save_snapshot(
        self, topics: list[dict], force: bool = False
    ) -> PulseSnapshot | None:
        """Save a new snapshot of topic data.

        Args:
            topics: List of topic dicts with slug, mention_count, unique_authors
            force: If True, save even if MIN_SNAPSHOT_INTERVAL hasn't passed

        Returns:
            The saved PulseSnapshot, or None if skipped (too soon)

        """
        if not force and not self.should_save_snapshot():
            logger.debug("Skipping snapshot - less than 1 hour since last save")
            return None

        timestamp = datetime.now(timezone.utc).isoformat()

        topic_snapshots = {}
        for t in topics:
            slug = t.get("slug", "")
            if slug:
                topic_snapshots[slug] = TopicSnapshot(
                    slug=slug,
                    mention_count=t.get("mention_count", 0),
                    unique_authors=t.get("unique_authors", 0),
                    timestamp=timestamp,
                )

        snapshot = PulseSnapshot(timestamp=timestamp, topics=topic_snapshots)

        # Save to file
        path = self._snapshot_path(timestamp)
        with open(path, "w") as f:
            json.dump(
                {
                    "timestamp": snapshot.timestamp,
                    "topics": {
                        slug: asdict(ts) for slug, ts in snapshot.topics.items()
                    },
                },
                f,
                indent=2,
            )

        logger.info(f"Saved snapshot with {len(topic_snapshots)} topics to {path}")

        # Cleanup old snapshots
        self._cleanup_old_snapshots()

        return snapshot

    def get_previous_snapshot(self) -> PulseSnapshot | None:
        """Get the most recent previous snapshot.

        Returns:
            The previous snapshot, or None if no snapshots exist

        """
        snapshots = sorted(self.storage_dir.glob("snapshot_*.json"))

        # Need at least 2 snapshots (current + previous)
        # But since we call this BEFORE saving current, we need at least 1
        if not snapshots:
            return None

        # Get the most recent one
        latest_path = snapshots[-1]

        try:
            with open(latest_path) as f:
                data = json.load(f)

            topics = {}
            for slug, t_data in data.get("topics", {}).items():
                topics[slug] = TopicSnapshot(
                    slug=t_data["slug"],
                    mention_count=t_data["mention_count"],
                    unique_authors=t_data["unique_authors"],
                    timestamp=t_data["timestamp"],
                )

            return PulseSnapshot(timestamp=data["timestamp"], topics=topics)
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to load snapshot {latest_path}: {e}")
            return None

    def _cleanup_old_snapshots(self) -> None:
        """Remove old snapshots beyond max_snapshots limit."""
        snapshots = sorted(self.storage_dir.glob("snapshot_*.json"))

        if len(snapshots) > self.max_snapshots:
            to_remove = snapshots[: len(snapshots) - self.max_snapshots]
            for path in to_remove:
                try:
                    path.unlink()
                    logger.debug(f"Removed old snapshot: {path}")
                except OSError as e:
                    logger.warning(f"Failed to remove old snapshot {path}: {e}")


def compute_temporal_velocity(
    current_mentions: int,
    previous_mentions: int | None,
) -> float | None:
    """Compute true temporal velocity.

    Args:
        current_mentions: Current mention count
        previous_mentions: Previous mention count (or None if no history)

    Returns:
        Velocity ratio (current/previous), or None if no baseline
        - >1.0 = growing over time
        - 1.0 = stable
        - <1.0 = declining over time
        - None = no historical data available

    """
    if previous_mentions is None:
        return None

    if previous_mentions <= 0:
        # No previous mentions - if we have current, it's new/emerging
        return 2.0 if current_mentions > 0 else None

    return current_mentions / previous_mentions


@cache
def get_snapshot_store() -> SnapshotStore:
    """Get the default snapshot store singleton."""
    return SnapshotStore()
