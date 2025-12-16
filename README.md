# Community Pulse

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-58%20passed-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](htmlcov/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Identifies trending topics using velocity and co-occurrence graph analysis.

## Overview

Community Pulse ranks topics by combining five signals:

- **Velocity (25%)** - Rate of change in topic mentions
- **Eigenvector Centrality (25%)** - Connection to other important topics (convergence)
- **Betweenness Centrality (20%)** - Bridge topics connecting different communities
- **PageRank (15%)** - Flow-based influence and authority in the topic graph
- **Author Spread (15%)** - Diversity of contributors discussing the topic

## Architecture

```
React Native Web (Expo) -> FastAPI -> Supabase (PostgreSQL + pg_graphql)
                                   -> rustworkx (graph analysis)
```

## Quick Start

### Docker (Recommended)

Requires Docker Compose v2.

```bash
# 1. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 2. Start the database
docker compose up -d db

# 3. Configure environment
cp .env.example .env

# 4. Start the frontend
cd frontend && npm start
# Open http://localhost:8081

# 5. Start the backend (new terminal)
uv run uvicorn community_pulse.api.app:app --reload
# API docs at http://localhost:8001/docs
```

### Manual Setup

If you prefer running PostgreSQL locally without Docker:

```bash
# Backend
uv sync
cp .env.example .env
uv run uvicorn community_pulse.api.app:app --reload

# Frontend
cd frontend
npm install
npm start
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /pulse/current` | Current trending topics with pulse scores |
| `GET /pulse/graph` | Topic co-occurrence graph for visualization |

### Query Parameters

- `/pulse/current?limit=10&min_score=0.5` - Filter by count and minimum pulse score
- `/pulse/graph?min_edge_weight=2` - Filter edges by minimum co-occurrence weight

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Lint
uv run ruff check src tests

# Type check
uv run mypy src tests
```

## Deployment

### Supabase (Database)

1. Create a free Supabase project
2. Copy the connection string from Project Settings > Database
3. Set `DATABASE_URL` in your deployment environment

### Render (API + Frontend)

Deploy using the included `render.yaml` blueprint:

1. Connect your GitHub repository
2. Set `DATABASE_URL` from Supabase
3. Deploy

## Project Structure

```
src/community_pulse/
├── api/              # FastAPI application
│   ├── app.py        # App factory with CORS
│   └── routes/       # Health and pulse endpoints
├── analysis/         # Graph analysis
│   ├── graph.py      # rustworkx graph building, centrality
│   └── velocity.py   # Velocity and pulse score computation
├── db/               # Database models
│   ├── models.py     # SQLAlchemy models
│   └── connection.py # Connection management
├── ingest/           # Data ingestion
│   ├── hn_loader.py  # Hacker News data loader
│   └── topic_extractor.py  # Pattern-based topic extraction
└── models/           # Pydantic schemas
    └── pulse.py      # API response models

frontend/
├── app/              # Expo Router screens
├── components/       # React components (FlowGraph)
├── hooks/            # Custom hooks (usePulseGraph)
└── lib/              # API client
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Graph Analysis**: rustworkx (Rust-powered NetworkX alternative)
- **Frontend**: React Native Web, Expo Router, TanStack Query, react-force-graph-2d
- **Database**: PostgreSQL via Supabase (includes pg_graphql)
- **Deployment**: Render (API + static), Docker Compose (local)

## License

[MIT](LICENSE)
