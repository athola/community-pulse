# Community Pulse

**Detecting Emerging Topics via Velocity and Graph Analysis**

---

## The Challenge

Online communities generate high message volumes. Count-based trend detection methods often lag because they:

- React after mention counts have already peaked.
- Miss convergence patterns where multiple voices independently discuss a topic.
- Ignore the network structure of how information flows between topics.

```mermaid
flowchart LR
    subgraph Traditional["Traditional Approach"]
        A[Count mentions] --> B[Rank by volume]
        B --> C[Report top topics]
    end

    subgraph Problem["Limitations"]
        D[Late detection]
        E[Misses convergence]
        F[No context]
    end

    Traditional --> Problem

    style Problem fill:#fee,stroke:#c00
```

**Result**: Count-based dashboards often report trends only after they have become mainstream.

---

## Methodology

Community Pulse identifies emerging topics by combining mention velocity with graph centrality metrics.

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

    subgraph Output["Output"]
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

## Use Cases

| Audience | Application |
|----------|-------------|
| **Community Managers** | Identify rising discussions early. |
| **Product Teams** | Spot emerging user needs and feature requests. |
| **Research Analysts** | Track technology adoption shifts. |
| **Content Strategists** | Identify timely topics for content creation. |

---

## How It Works

### The Pulse Score Formula

The Pulse Score (0-100) combines five signals:

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
| **Velocity** | 25% | Rate of acceleration in mentions. |
| **Eigenvector Centrality** | 25% | Connection to other high-scoring topics. |
| **Betweenness Centrality** | 20% | Bridge topics connecting different clusters. |
| **PageRank** | 15% | Flow-based importance in the topic graph. |
| **Author Diversity** | 15% | Count of unique contributing authors. |

### Signal Rationale

- **Velocity**: Captures momentum (acceleration relative to baseline).
- **Eigenvector Centrality**: Identifies convergence (topics connected to other important topics).
- **Betweenness Centrality**: Reveals bridges (topics connecting separate clusters).
- **PageRank**: Measures authority (influence propagation).
- **Author Diversity**: Filters noise (prevents single-author dominance).

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

| Component | Technology | Reasoning |
|-----------|------------|-----------|
| Graph Analysis | **rustworkx** | Rust-based performance for centrality calculations. |
| Database | **Supabase** | PostgreSQL with `pg_graphql`. |
| API | **FastAPI** | Async Python support. |
| Frontend | **React Native Web** | Cross-platform compatibility. |
| Visualization | **react-force-graph** | Interactive network rendering. |

---

## Visualization Views

### Topic Network

Topics appear as **nodes** connected by co-occurrence **edges**:

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

- **Node size**: Pulse score.
- **Node color**: Intensity.
- **Edge thickness**: Co-occurrence strength.

### Topic Cards

A list view showing:
- Topic name and pulse score.
- Velocity indicator.
- Mention and author counts.
- Trend sparkline.

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

    Local --> Cloud
```

| Environment | Database | API Hosting |
|-------------|----------|-------------|
| **Local Dev** | Docker PostgreSQL | localhost |
| **POC/Demo** | Supabase Free | Render Free |
| **Production** | Supabase Pro | Render Standard |

---

## Comparison

```mermaid
flowchart LR
    subgraph Before["Count-Based"]
        B1[Manual monitoring]
        B2[Reactive]
    end

    subgraph After["Pulse-Based"]
        A1[Automated detection]
        A2[Proactive]
    end

    Before -->|vs| After

    style Before fill:#fee,stroke:#c00
    style After fill:#efe,stroke:#0a0
```

| Metric | Count-Based | Pulse-Based |
|--------|-------------|-------------|
| Detection Time | Post-peak | Emerging |
| Signal | Volume only | Velocity + Network |
| Context | List | Graph |

---

## Get Started

**Local Setup:**

```bash
git clone https://github.com/athola/community-pulse
cd community-pulse
docker compose up -d
open http://localhost:8081
```

**API Check:**

```bash
curl http://localhost:8001/pulse/current
```

---

## Summary

**Community Pulse** provides actionable trend intelligence by:

1. **Detecting velocity**: Finding topics accelerating faster than baseline.
2. **Measuring convergence**: Identifying organic emergence.
3. **Analyzing networks**: Mapping information flow between topics.
4. **Scoring pulse**: Combining signals into a single metric.

The result: **Early detection of rising topics.**

---

<div align="center">

**Community Pulse** | [GitHub](https://github.com/athola/community-pulse) | MIT License

</div>
