# Mathematical Foundations

This document describes the mathematical algorithms and formulas used in Community Pulse for trend detection and pulse score computation.

## Pulse Score Formula

The pulse score combines five normalized metrics to detect emerging collective attention.

### Formula Evolution: 4-Signal to 5-Signal Design

The initial design used 4 signals (30% velocity, 30% eigenvector, 25% betweenness, 15% sentiment). The current implementation evolved to 5 signals:

**Rationale for Evolution:**

1. **Added PageRank (15%)** - Complements eigenvector centrality with flow-based authority. Eigenvector measures importance via connections to important nodes; PageRank measures influence via information flow patterns.

2. **Replaced sentiment with author diversity (15%)** - More objective (count-based vs. subjective), easier to compute (no NLP model), and a better proxy for convergence (diverse voices = genuine emergence).

3. **Rebalanced weights** - Velocity and eigenvector remain primary (25% each), betweenness reduced to 20% to accommodate new signals.

See [velocity.py](../src/community_pulse/analysis/velocity.py) for implementation details.

### Current Formula

```
score = 0.25 * velocity
      + 0.25 * eigenvector_centrality
      + 0.20 * betweenness_centrality
      + 0.15 * pagerank
      + 0.15 * author_diversity
```

**Weight rationale:**
- **Velocity (25%)** - Momentum: topics gaining conversation rate
- **Eigenvector centrality (25%)** - Convergence: connection to other important topics
- **Betweenness centrality (20%)** - Bridge topics connecting different clusters
- **PageRank (15%)** - Network importance in directed topic flow
- **Author diversity (15%)** - Multiple independent voices (prevents single-author spikes)

All components are normalized to [0, 1] before combination; the final score falls within [0, 1].

---

## Velocity Calculation

Velocity measures how fast a topic's mention rate is accelerating compared to its historical baseline.

```
velocity = current_mentions / baseline_mentions
```

**Interpretation:**
- `velocity = 1.0` - Stable (no change from baseline)
- `velocity > 1.0` - Trending up
- `velocity < 1.0` - Declining
- `velocity = 2.0` - Emerging topic (no baseline data)

**Normalization:**
```
norm_velocity = min(velocity / 3.0, 1.0)
```

This caps velocity contribution at 3x growth, preventing extreme spikes from dominating the score.

---

## Graph Centrality Metrics

Community Pulse builds a topic co-occurrence graph where:
- **Nodes** = Topics
- **Edges** = Topics mentioned together in the same post
- **Edge weight** = Number of shared authors

### Eigenvector Centrality

Measures a topic's connection to other highly-connected topics.

```
Av = λv
```

Where A is the adjacency matrix and λ is the largest eigenvalue. Topics connected to many important topics score higher.

**Normalization:** L2-normalized by rustworkx (||v||₂ = 1), capped at 1.0.

### Betweenness Centrality

Measures how often a topic lies on the shortest path between other topics.

```
C_B(v) = Σ(σ_st(v) / σ_st) / [(n-1)(n-2)/2]
```

Where σ_st is the number of shortest paths between s and t, and σ_st(v) is paths through v.

Topics with high betweenness act as bridges between clusters.

**Normalization:** Automatically normalized to [0, 1] by rustworkx.

### PageRank

Measures topic importance based on directed graph flow (which topics lead to discussions of other topics).

```
PR(u) = (1-α)/N + α * Σ(PR(v)/L(v))
```

Where α = 0.85 (damping factor), N = number of nodes, L(v) = out-degree.

**Normalization:** Values sum to 1.0 across all nodes; individual values capped at 1.0.

---

## Author Diversity

Prevents single-author spikes from artificially inflating scores:

```
norm_authors = min(unique_authors / max_authors, 1.0)
```

A topic discussed by many different authors is more likely to represent genuine collective attention than one dominated by a single prolific poster.

---

## Academic Foundations

The algorithms are based on established research:

- **Burst Detection**: Kleinberg's state transition model (KDD 2002)
- **Spikiness Metric**: `S = max(R) / mean(R)` for burst intensity (Nature Scientific Reports, 2020)
- **Co-word Networks**: Time-sliced co-occurrence for emergence prediction (Technological Forecasting, 2021)
- **Graph-based Event Detection**: Louvain clustering on co-occurrence graphs (Information Sciences, 2023)

---

## Implementation Notes

### Input Constraints

All inputs to `compute_pulse_score` must be non-negative:
- `velocity >= 0`
- `eigenvector_centrality >= 0`
- `betweenness_centrality >= 0`
- `pagerank >= 0`
- `unique_authors >= 0`
- `max_authors > 0`

### Numerical Stability

- Division-by-zero is prevented by validating `max_authors > 0`
- Final score is clamped to [0, 1] and rounded to 4 decimal places
- All centrality metrics are capped at 1.0 before combination
