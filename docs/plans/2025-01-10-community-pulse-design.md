# Community Pulse Design

**Version**: initial-poc-0.1.0
**Date**: 2025-01-10
**Status**: Approved

## Overview

Community Pulse detects emerging collective attention in online communities by combining velocity-based trend detection with co-occurrence graph analysis. The system ingests community data, builds a topic-author-post graph, computes pulse scores, and renders an animated flow visualization.

### Core Concept: The Pulse

A "pulse" represents emergent collective movement in a community—like ocean currents that carry participants toward shared destinations. The system detects:

1. **Momentum (A)** — Topics gaining velocity (accelerating conversation)
2. **Convergence (B)** — Multiple independent voices clustering around the same signal
3. **Relational flow (D)** — How information moves through the community network
4. **Sentiment (C)** — Emotional texture overlay (lowest weight)

Weighting: A=30%, B=30%, D=25%, C=15%

### Academic Foundations

- **Kleinberg's Burst Detection** (KDD 2002) — State transition model for detecting elevated activity
- **Spikiness Metric** (Nature Scientific Reports, 2020) — `S = max(R) / mean(R)` for burst intensity
- **Co-word Network Dynamics** (Technological Forecasting, 2021) — Time-sliced co-occurrence for emergence prediction
- **Graph-based Event Detection** (Information Sciences, 2023) — Louvain clustering on co-occurrence graphs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Native Web Frontend                │
│   ┌─────────────────┐    ┌─────────────────────────────┐   │
│   │  Flow View      │    │  Timeline View              │   │
│   │  Force graph    │    │  Stacked area charts        │   │
│   └─────────────────┘    └─────────────────────────────┘   │
│   Mobile: Card list view as default                         │
└─────────────────────────────────────────────────────────────┘
                              │ GraphQL + REST
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway                          │
│   • Auth/rate limiting  • Pulse computation                 │
│   • Graph analysis orchestration                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              Supabase (PostgreSQL + pg_graphql)             │
│   Tables: posts, topics, authors, post_topics               │
│   Materialized views: topic_velocity, topic_cooccurrence    │
│   GraphQL: Auto-generated from schema                       │
└─────────────────────────────────────────────────────────────┘
```

### Deployment

| Component | Platform | Tier |
|-----------|----------|------|
| Database | Supabase | Free (500MB, pg_graphql) |
| API | Render | Free |
| Frontend | Render Static | Free |

## Data Model

### Core Tables

```sql
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    handle TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    author_id UUID REFERENCES authors(id),
    parent_id UUID REFERENCES posts(id),
    content TEXT,
    posted_at TIMESTAMPTZ NOT NULL,
    score INT DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE post_topics (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    relevance FLOAT DEFAULT 1.0,
    PRIMARY KEY (post_id, topic_id)
);
```

### Graph Relationships

- `Author → AUTHORED → Post` (author_id FK)
- `Post → REPLIES_TO → Post` (parent_id FK)
- `Post → MENTIONS → Topic` (post_topics junction)
- `Topic → CO_OCCURS_WITH → Topic` (derived via shared posts)

### Materialized Views

```sql
-- Topic velocity over time windows
CREATE MATERIALIZED VIEW topic_velocity AS
WITH hourly_counts AS (
    SELECT
        pt.topic_id,
        date_trunc('hour', p.posted_at) AS hour,
        COUNT(*) AS mentions,
        COUNT(DISTINCT p.author_id) AS unique_authors
    FROM post_topics pt
    JOIN posts p ON p.id = pt.post_id
    WHERE p.posted_at > NOW() - INTERVAL '7 days'
    GROUP BY pt.topic_id, date_trunc('hour', p.posted_at)
)
SELECT
    topic_id,
    hour,
    mentions,
    unique_authors,
    mentions::FLOAT / NULLIF(AVG(mentions) OVER (
        PARTITION BY topic_id
        ORDER BY hour
        ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
    ), 0) AS velocity
FROM hourly_counts;

-- Topic co-occurrence matrix
CREATE MATERIALIZED VIEW topic_cooccurrence AS
SELECT
    pt1.topic_id AS topic_a,
    pt2.topic_id AS topic_b,
    COUNT(DISTINCT pt1.post_id) AS shared_posts,
    COUNT(DISTINCT p.author_id) AS shared_authors
FROM post_topics pt1
JOIN post_topics pt2 ON pt1.post_id = pt2.post_id
    AND pt1.topic_id < pt2.topic_id
JOIN posts p ON p.id = pt1.post_id
WHERE p.posted_at > NOW() - INTERVAL '48 hours'
GROUP BY pt1.topic_id, pt2.topic_id
HAVING COUNT(DISTINCT p.author_id) >= 2;
```

## Graph Analysis

Using `rustworkx` (Rust-powered NetworkX alternative) for performance:

```python
import rustworkx as rx

def build_topic_graph(cooccurrence_data: list[dict]) -> rx.PyGraph:
    graph = rx.PyGraph()
    topic_indices = {}

    for row in cooccurrence_data:
        for topic_id in [row["topic_a"], row["topic_b"]]:
            if topic_id not in topic_indices:
                topic_indices[topic_id] = graph.add_node({"id": topic_id})

        graph.add_edge(
            topic_indices[row["topic_a"]],
            topic_indices[row["topic_b"]],
            {"weight": row["shared_authors"]}
        )

    return graph, topic_indices

def compute_centrality(graph: rx.PyGraph) -> dict:
    return {
        "betweenness": rx.betweenness_centrality(graph),
        "eigenvector": rx.eigenvector_centrality(graph),
        "pagerank": rx.pagerank(graph),
    }
```

### Pulse Score Formula

```python
def compute_pulse_score(topic_id, velocity, centrality) -> float:
    return (
        0.30 * normalize(velocity.velocity_ratio) +
        0.30 * normalize(centrality["eigenvector"]) +
        0.25 * normalize(centrality["betweenness"]) +
        0.15 * normalize(velocity.unique_authors)
    )
```

## API Design

### REST Endpoints (FastAPI)

```
GET  /pulse/current          → Current top topics by pulse score
GET  /pulse/topics/{id}/history → Topic pulse over time
GET  /pulse/clusters         → Emerging topic clusters
GET  /pulse/graph            → Co-occurrence graph for visualization
GET  /health                 → Health check
```

### GraphQL (pg_graphql via Supabase)

Auto-generated CRUD for all tables plus custom functions for pulse queries.

## Frontend

### Tech Stack

- React Native + React Native Web (cross-platform)
- Expo Router (navigation)
- react-force-graph-2d (flow visualization)
- recharts (timeline charts)
- @tanstack/react-query (data fetching)

### Views

1. **Flow View** (desktop default) — Force-directed graph showing topic relationships
2. **Timeline View** — Stacked area chart showing pulse over time
3. **Cards View** (mobile default) — Scrollable list of topic cards

### Visual Design

- Dark theme with cyan accents (ocean-inspired)
- Typography: Space Mono (display), Outfit (body)
- Subtle, functional — polished but not flashy
- Mobile-first responsive design

### Color Palette

```typescript
const colors = {
  bg: { primary: '#0f1419', secondary: '#1a1f26', elevated: '#242a33' },
  accent: { low: '#3b5068', mid: '#0d9488', high: '#22d3ee' },
  text: { primary: '#e2e8f0', secondary: '#94a3b8', muted: '#64748b' },
};
```

## Data Source (POC)

Hacker News discussions via public API:
- Pre-collected corpus for demo stability
- Topics extracted via keyword analysis
- 7 days of data for velocity calculations

## Project Structure

```
community-pulse/
├── backend/
│   └── src/community_pulse/
│       ├── api/          # FastAPI routes
│       ├── analysis/     # rustworkx, pulse scoring
│       ├── db/           # SQLAlchemy, migrations
│       ├── ingest/       # HN loader, topic extraction
│       └── models/       # Pydantic schemas
├── frontend/
│   ├── app/              # Expo Router pages
│   ├── components/       # UI components
│   ├── hooks/            # React Query wrappers
│   └── lib/              # API client, colors
├── data/                 # HN corpus
├── scripts/              # Data collection, seeding
└── docs/plans/           # This document
```

## Future Enhancements (GitHub Issues)

1. **Crawler capability** — Point at URL to discover community data
2. **Semantic graph** — Entity extraction, sentiment as edge property
3. **Social graph** — Author-to-author interaction analysis, community detection
4. **Real-time updates** — WebSocket subscriptions for live pulse changes

## Success Criteria

- [ ] Live demo accessible on mobile and desktop
- [ ] Flow visualization renders topic relationships
- [ ] Timeline shows pulse trends over 72 hours
- [ ] API responds in <200ms for current pulse
- [ ] Interviewers can open on personal devices
