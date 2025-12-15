# Community Pulse

**Detecting Emerging Trends Before They Peak**

---

## The Challenge

Online communities generate thousands of discussions daily. Hidden within this noise are **emerging signals**—topics gaining momentum that indicate where collective attention is heading.

Traditional trend detection methods fail because they:

- React **after** trends have already peaked
- Miss **convergence patterns** (multiple voices independently discovering the same insight)
- Ignore the **network structure** of how information flows through communities

```mermaid
flowchart LR
    subgraph Traditional["Traditional Approach"]
        A[Count mentions] --> B[Rank by volume]
        B --> C[Report top topics]
    end

    subgraph Problem["The Problem"]
        D[Late detection]
        E[Misses emergence]
        F[No context]
    end

    Traditional --> Problem

    style Problem fill:#fee,stroke:#c00
```

**Result**: By the time a trend appears on traditional dashboards, the opportunity window has closed.

---

## The Solution

Community Pulse detects **emerging collective attention** by analyzing the *pulse* of community discussions—not just what people are talking about, but *how* conversations are evolving and connecting.

```mermaid
flowchart TB
    subgraph Input["Community Data"]
        Posts[Posts & Comments]
        Authors[Author Activity]
        Time[Temporal Patterns]
    end

    subgraph Analysis["Pulse Analysis"]
        V[Velocity Detection]
        G[Graph Analysis]
        C[Convergence Scoring]
    end

    subgraph Output["Actionable Insights"]
        Trends[Emerging Trends]
        Clusters[Topic Clusters]
        Scores[Pulse Scores]
    end

    Input --> Analysis
    Analysis --> Output

    style Analysis fill:#e6f3ff,stroke:#0066cc
    style Output fill:#e6ffe6,stroke:#009900
```

---

## Who Is This For?

| Audience | Use Case |
|----------|----------|
| **Community Managers** | Identify rising discussions before they dominate feeds |
| **Product Teams** | Spot emerging user needs and feature requests early |
| **Research Analysts** | Track technology adoption and sentiment shifts |
| **Content Strategists** | Find timely topics for engagement |
| **Investment Analysts** | Monitor technology trends in developer communities |

---

## How It Works

### The Pulse Score Formula

Community Pulse combines five signals into a single **Pulse Score** (0-100):

```mermaid
pie title Pulse Score Composition
    "Velocity" : 25
    "Eigenvector Centrality" : 25
    "Betweenness Centrality" : 20
    "PageRank" : 15
    "Author Diversity" : 15
```

| Signal | Weight | What It Measures |
|--------|--------|------------------|
| **Velocity** | 25% | How fast is this topic accelerating? |
| **Eigenvector Centrality** | 25% | Connection to other important topics |
| **Betweenness Centrality** | 20% | Is this topic a bridge between communities? |
| **PageRank** | 15% | Flow-based influence and authority |
| **Author Diversity** | 15% | How many unique voices are contributing? |

### Why These Signals Matter

**Velocity** catches momentum—a topic mentioned 10x more than last week is accelerating.

**Eigenvector Centrality** identifies convergence—topics connected to other important topics are themselves important, capturing organic emergence patterns.

**Betweenness Centrality** reveals bridges—topics that connect otherwise separate discussion clusters often indicate paradigm shifts.

**PageRank** measures authority—flow-based influence that accounts for how attention propagates through the topic network.

**Author Diversity** filters noise—topics discussed by many different people carry more weight than one person posting repeatedly.

---

## Technical Architecture

```mermaid
flowchart LR
    subgraph Data["Data Layer"]
        HN[Hacker News API]
        DB[(PostgreSQL)]
    end

    subgraph Backend["Analysis Engine"]
        Ingest[Data Ingestion]
        Extract[Topic Extraction]
        Graph[Graph Analysis]
        Pulse[Pulse Computation]
    end

    subgraph API["API Layer"]
        Fast[FastAPI]
        REST[REST Endpoints]
    end

    subgraph Frontend["Visualization"]
        Web[React Native Web]
        Viz[Force Graph]
    end

    HN --> Ingest
    Ingest --> DB
    DB --> Extract
    Extract --> Graph
    Graph --> Pulse
    Pulse --> Fast
    Fast --> REST
    REST --> Web
    Web --> Viz

    style Backend fill:#f0f0ff,stroke:#6666cc
```

### Key Technologies

| Component | Technology | Why |
|-----------|------------|-----|
| Graph Analysis | **rustworkx** | Rust-powered speed for centrality calculations |
| Database | **Supabase** | PostgreSQL with built-in GraphQL support |
| API | **FastAPI** | High-performance async Python |
| Frontend | **React Native Web** | Cross-platform (desktop + mobile) |
| Visualization | **react-force-graph** | Interactive network exploration |

---

## What You See

### Topic Network View

The primary visualization shows topics as **nodes** and their co-occurrence as **edges**:

```mermaid
graph TB
    AI((AI/ML))
    Rust((Rust))
    Python((Python))
    Cloud((Cloud))
    Security((Security))

    AI --- Rust
    AI --- Python
    Python --- Cloud
    Rust --- Security
    Cloud --- Security
    AI --- Security

    style AI fill:#22d3ee,stroke:#0891b2,stroke-width:4px
    style Rust fill:#0d9488,stroke:#065f46,stroke-width:3px
    style Python fill:#0d9488,stroke:#065f46,stroke-width:2px
    style Cloud fill:#3b5068,stroke:#1e3a5f
    style Security fill:#3b5068,stroke:#1e3a5f
```

- **Node size** = Pulse score (bigger = more momentum)
- **Node color** = Intensity (cyan = high pulse, gray = low)
- **Edge thickness** = Co-occurrence strength

### Topic Cards View

For quick scanning, topics display as cards showing:

- Topic name and current pulse score
- Velocity indicator (↑ rising, ↓ falling, → stable)
- Mention count and unique author count
- Trend sparkline

---

## Sample Insights

| Topic | Pulse | Velocity | Insight |
|-------|-------|----------|---------|
| **AI Agents** | 87 | ↑ 3.2x | Rapidly emerging—3x more mentions than baseline |
| **Rust** | 72 | ↑ 1.8x | Steady growth, high convergence from diverse authors |
| **Python** | 65 | → 1.1x | Stable baseline, always present |
| **WebAssembly** | 58 | ↑ 2.1x | Emerging bridge topic connecting frontend + systems |

---

## Deployment Options

```mermaid
flowchart TB
    subgraph Local["Local Development"]
        Docker[Docker Compose]
        LocalDB[(Local PostgreSQL)]
    end

    subgraph Cloud["Production"]
        Render[Render.com]
        Supabase[(Supabase)]
    end

    subgraph Future["Future Options"]
        AWS[AWS/GCP]
        OnPrem[On-Premises]
    end

    Local --> Cloud
    Cloud --> Future
```

| Environment | Database | API Hosting | Cost |
|-------------|----------|-------------|------|
| **Local Dev** | Docker PostgreSQL | localhost | Free |
| **POC/Demo** | Supabase Free | Render Free | Free |
| **Production** | Supabase Pro | Render Standard | ~$25/mo |
| **Enterprise** | Self-hosted PG | AWS/GCP | Variable |

---

## Roadmap

### Current: POC (v0.1)

- [x] Hacker News data ingestion
- [x] Pattern-based topic extraction
- [x] Graph-based pulse scoring
- [x] REST API with filtering
- [x] Interactive network visualization

### Next: Enhanced Analysis (v0.2)

- [ ] Real-time data streaming
- [ ] ML-based topic extraction (NER, embeddings)
- [ ] Historical trend comparison
- [ ] Alert notifications

### Future: Platform (v1.0)

- [ ] Multi-community support (Reddit, Discord, Twitter)
- [ ] Custom topic taxonomies
- [ ] Team collaboration features
- [ ] API for third-party integrations

---

## Why Community Pulse?

```mermaid
flowchart LR
    subgraph Before["Without Community Pulse"]
        B1[Manual monitoring]
        B2[Reactive decisions]
        B3[Missed opportunities]
    end

    subgraph After["With Community Pulse"]
        A1[Automated detection]
        A2[Proactive insights]
        A3[Early advantage]
    end

    Before -->|Transform| After

    style Before fill:#fee,stroke:#c00
    style After fill:#efe,stroke:#0a0
```

| Before | After |
|--------|-------|
| Manually scanning feeds | Automated pulse monitoring |
| Reacting to established trends | Detecting emergence early |
| Gut feeling decisions | Data-driven prioritization |
| Missing cross-topic connections | Visualizing topic networks |

---

## Get Started

**Try it locally in 5 minutes:**

```bash
git clone https://github.com/athola/community-pulse
cd community-pulse
docker compose up -d
open http://localhost:8081
```

**Explore the API:**

```bash
curl http://localhost:8000/pulse/current
curl http://localhost:8000/pulse/graph
```

---

## Summary

**Community Pulse** transforms noisy community discussions into actionable trend intelligence by:

1. **Detecting velocity**—finding topics accelerating faster than baseline
2. **Measuring convergence**—identifying organic emergence from independent voices
3. **Analyzing networks**—revealing how information flows between topic clusters
4. **Scoring pulse**—combining signals into a single actionable metric

The result: **See emerging trends before they peak.**

---

<div align="center">

**Community Pulse** | [GitHub](https://github.com/athola/community-pulse) | MIT License

*Detect the pulse of your community.*

</div>
