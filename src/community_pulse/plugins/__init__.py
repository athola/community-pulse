"""Data source plugins for Community Pulse.

Plugins provide a way to ingest data from different community platforms.
Each plugin must implement the DataSourcePlugin protocol.
"""

from community_pulse.plugins.base import DataSourcePlugin, RawPost
from community_pulse.plugins.hackernews import HackerNewsPlugin

__all__ = [
    "DataSourcePlugin",
    "RawPost",
    "HackerNewsPlugin",
]
