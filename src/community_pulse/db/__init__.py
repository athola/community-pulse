"""Database package for Community Pulse.

FUTURE EXPANSION MODULE
-----------------------
This module defines the persistence layer for Community Pulse, but is NOT currently
used in the POC implementation. The models and connection management are defined here
as architectural groundwork for future features.

Current POC Architecture:
    - Fetches live data from Hacker News API on demand
    - Computes pulse metrics in-memory without persistence
    - Stateless: no database connection required

Future Use Cases (when this module becomes active):
    1. Caching: Store fetched HN data to reduce API calls
    2. Historical Analysis: Track pulse trends over time
    3. Comparative Studies: Compare current vs past community sentiment
    4. Offline Mode: Allow analysis without live API access
    5. Performance: Pre-compute expensive metrics

Models Defined:
    - Author: Community members who create posts
    - Post: Stories and comments from the community
    - Topic: Extracted themes/topics from content
    - PostTopic: Many-to-many relationship between posts and topics

This is NOT dead code - it's intentional forward planning. When persistence is needed,
this layer is ready to be activated by implementing a repository pattern in the
data_sources/ module.
"""

from community_pulse.db.connection import get_engine, get_session
from community_pulse.db.models import Author, Post, PostTopic, Topic

__all__ = ["get_engine", "get_session", "Author", "Post", "Topic", "PostTopic"]
