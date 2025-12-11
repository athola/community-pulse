# Mathematical Review: Community Pulse - Numerical Stability and Correctness

**Review Date:** 2025-12-10
**Reviewer:** Claude Code (Mathematical Review Agent)
**Scope:** Pulse score calculation, graph centrality metrics, velocity computations, and normalization

---

## Executive Summary

This review identified **3 critical issues**, **2 high-severity issues**, and **4 medium-severity concerns** in the mathematical operations of the Community Pulse codebase. The system uses complex graph centrality metrics and weighted combinations that are vulnerable to edge cases, particularly around division by zero and negative values.

**Critical Issues:**
1. Division by zero in pulse score calculation when `max_authors=0`
2. Negative input values produce invalid negative pulse scores
3. Missing input validation allows mathematically invalid states

**Recommendation:** Address critical issues before production deployment.

---

## 1. Critical Issues

### 1.1 Division by Zero: max_authors=0

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:62`

**Severity:** CRITICAL

**Description:**
When computing the pulse score, the code normalizes unique author count by dividing by `max_authors`. If the input data contains no authors (empty dataset), `max_authors=0` causes a `ZeroDivisionError`.

```python
# Line 62 in velocity.py
norm_authors = min(unique_authors / max_authors, 1.0)  # Division by zero!
```

**Mathematical Context:**
Author diversity normalization: `norm_authors = unique_authors / max_authors`

When `max_authors = 0`:
- Division is undefined
- Python raises `ZeroDivisionError`

**Reproduction:**
```python
compute_pulse_score(
    velocity=1.0,
    eigenvector_centrality=0.5,
    betweenness_centrality=0.3,
    unique_authors=5,
    max_authors=0,  # Triggers error
    pagerank=0.5
)
# ZeroDivisionError: division by zero
```

**Proposed Fix:**
```python
# Option 1: Default to 0 when max_authors is 0
norm_authors = min(unique_authors / max(max_authors, 1), 1.0)

# Option 2: Validate input and raise meaningful error
if max_authors <= 0:
    raise ValueError(f"max_authors must be positive, got {max_authors}")
norm_authors = min(unique_authors / max_authors, 1.0)
```

**Upstream Source:**
In `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/services/pulse_compute.py:165`:
```python
max_authors = len({p.author for p in posts})  # Can be 0 if posts is empty
```

If `posts = []`, then `max_authors = 0`, propagating the error.

---

### 1.2 Negative Values Produce Invalid Pulse Scores

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:48-68`

**Severity:** CRITICAL

**Description:**
The `compute_pulse_score` function does not validate inputs, allowing negative centrality values to produce mathematically invalid (negative) pulse scores that violate the documented [0, 1] range.

**Mathematical Context:**
Pulse score formula (line 63-68):
```
score = 0.25 * norm_velocity
      + 0.25 * norm_eigen
      + 0.20 * norm_between
      + 0.15 * norm_pagerank
      + 0.15 * norm_authors
```

Expected: `score ∈ [0, 1]`
Actual with negative inputs: `score < 0`

**Reproduction:**
```python
score = compute_pulse_score(
    velocity=-1.0,
    eigenvector_centrality=-0.5,
    betweenness_centrality=-0.3,
    unique_authors=0,
    max_authors=1,
    pagerank=-1.0
)
# Result: score = -0.4183 (INVALID!)
```

**Calculation Breakdown:**
```
norm_velocity  = min(-1.0 / 3.0, 1.0) = -0.3333
norm_eigen     = min(-0.5, 1.0) = -0.5
norm_between   = min(-0.3, 1.0) = -0.3
norm_pagerank  = min(-1.0, 1.0) = -1.0
norm_authors   = min(0 / 1, 1.0) = 0.0

score = 0.25*(-0.3333) + 0.25*(-0.5) + 0.20*(-0.3) + 0.15*(-1.0) + 0.15*(0.0)
      = -0.0833 - 0.125 - 0.06 - 0.15 + 0
      = -0.4183
```

**Root Cause:**
The `min()` function only caps the upper bound at 1.0 but does not enforce a lower bound of 0.0.

**Proposed Fix:**
```python
def compute_pulse_score(
    velocity: float,
    eigenvector_centrality: float,
    betweenness_centrality: float,
    unique_authors: int,
    max_authors: int = 100,
    pagerank: float = 0.0,
) -> float:
    """Compute combined pulse score using all centrality measures.

    All inputs must be non-negative.

    Raises:
        ValueError: If any input is negative or max_authors <= 0
    """
    # Input validation
    if velocity < 0:
        raise ValueError(f"velocity must be non-negative, got {velocity}")
    if eigenvector_centrality < 0:
        raise ValueError(f"eigenvector_centrality must be non-negative, got {eigenvector_centrality}")
    if betweenness_centrality < 0:
        raise ValueError(f"betweenness_centrality must be non-negative, got {betweenness_centrality}")
    if pagerank < 0:
        raise ValueError(f"pagerank must be non-negative, got {pagerank}")
    if unique_authors < 0:
        raise ValueError(f"unique_authors must be non-negative, got {unique_authors}")
    if max_authors <= 0:
        raise ValueError(f"max_authors must be positive, got {max_authors}")

    # Normalize velocity (cap at 3x baseline)
    norm_velocity = min(velocity / 3.0, 1.0)

    # Centrality measures - already 0-1 from rustworkx but cap for safety
    norm_eigen = min(eigenvector_centrality, 1.0)
    norm_between = min(betweenness_centrality, 1.0)
    norm_pagerank = min(pagerank, 1.0)

    # Normalize author count
    norm_authors = min(unique_authors / max_authors, 1.0)

    score = (
        0.25 * norm_velocity
        + 0.25 * norm_eigen
        + 0.20 * norm_between
        + 0.15 * norm_pagerank
        + 0.15 * norm_authors
    )

    # Defensive: ensure score is in [0, 1] even if inputs are unexpected
    return round(max(0.0, min(score, 1.0)), 4)
```

---

### 1.3 Missing Input Validation in Velocity Computation

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:15-25`

**Severity:** CRITICAL

**Description:**
The `compute_velocity` function accepts negative baseline values and handles them as if they were zero, which masks data quality issues.

**Mathematical Context:**
Velocity definition (line 17-18):
```
velocity = current_mentions / baseline_mentions
```

Domain constraints:
- `current_mentions ≥ 0` (count of mentions)
- `baseline_mentions ≥ 0` (historical average)

**Actual Behavior:**
```python
data = VelocityData("test", 10, -5.0, 5)  # Negative baseline!
velocity = compute_velocity(data)
# Result: 2.0 (treated as emerging topic)
```

Line 20-21:
```python
if data.baseline_mentions <= 0:  # Treats negative same as zero
    return 2.0 if data.current_mentions > 0 else 1.0
```

**Issue:** Negative baselines indicate data corruption or calculation errors upstream, but the code silently masks this issue instead of failing fast.

**Proposed Fix:**
```python
def compute_velocity(data: VelocityData) -> float:
    """Compute velocity ratio for a topic.

    Velocity = current_rate / baseline_rate
    A velocity > 1.0 means the topic is trending up.

    Args:
        data: VelocityData with non-negative mention counts

    Raises:
        ValueError: If baseline_mentions is negative
    """
    if data.baseline_mentions < 0:
        raise ValueError(
            f"baseline_mentions must be non-negative, got {data.baseline_mentions} "
            f"for topic {data.topic_id}"
        )

    if data.baseline_mentions == 0:
        # No baseline: if we have current mentions, it's emerging
        return 2.0 if data.current_mentions > 0 else 1.0

    return data.current_mentions / data.baseline_mentions
```

---

## 2. High-Severity Issues

### 2.1 Eigenvector Centrality Not Normalized to [0,1]

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:164` and `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:54`

**Severity:** HIGH

**Description:**
The `rustworkx.eigenvector_centrality()` function returns values that are NOT normalized to the [0, 1] range. The values are normalized such that the L2 norm equals 1, which means individual values can exceed 1.0 in certain graph topologies.

**Mathematical Context:**
Eigenvector centrality from rustworkx uses L2 normalization:
```
||v||₂ = sqrt(Σ vᵢ²) = 1
```

This does NOT guarantee `vᵢ ∈ [0, 1]`.

Example: In a 2-node graph with equal eigenvector centrality:
```
v₁² + v₂² = 1
v₁ = v₂ = 1/√2 ≈ 0.707
```

Both values are 0.707, which is > 0.5 and < 1.0, but the assumption that eigenvector centrality is in [0, 1] is false.

**Reproduction:**
```python
data = [
    TopicGraphData("a", "b", shared_posts=10, shared_authors=5),
]
undirected, indices = build_topic_graph(data)
directed = build_directed_graph(data, indices)
centrality = compute_all_centrality(undirected, directed)

# Both nodes have eigenvector = 0.707 (sqrt(2)/2)
print(centrality[0]["eigenvector"])  # 0.7071...
```

**Impact:**
In `compute_pulse_score`, line 54:
```python
norm_eigen = min(eigenvector_centrality, 1.0)
```

The `min()` function attempts to cap at 1.0, which works for values > 1, but the code comment claims "already 0-1 from rustworkx", which is **incorrect**.

**Actual Range:**
For most graphs, eigenvector values fall in [0, 1], but this is not guaranteed. The current capping approach is defensive but based on a false assumption.

**Proposed Fix:**
1. **Document the actual behavior** in code comments:
```python
# Eigenvector centrality - L2 normalized (not necessarily in [0,1])
# Cap at 1.0 for pulse score combination
norm_eigen = min(eigenvector_centrality, 1.0)
```

2. **Consider max-normalization** if you want true [0, 1] range:
```python
def compute_all_centrality(undirected, directed):
    # ... existing code ...

    # Max-normalize eigenvector to [0, 1]
    if eigenvector:
        max_eigen = max(eigenvector.values())
        if max_eigen > 0:
            eigenvector = {k: v / max_eigen for k, v in eigenvector.items()}

    # ... rest of function ...
```

---

### 2.2 PageRank Can Exceed 1.0 in Edge Cases

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:148`

**Severity:** HIGH

**Description:**
While PageRank values should sum to 1.0 (forming a probability distribution), individual values can theoretically exceed 1.0 in graphs with very few nodes.

**Mathematical Context:**
PageRank formula:
```
PR(u) = (1-α)/N + α * Σ(PR(v)/L(v))
```

Where:
- α = damping factor (0.85)
- N = number of nodes
- L(v) = out-degree of node v

For a single-node graph:
```
PR(u) = (1-0.85)/1 + 0.85 * PR(u)
0.15 * PR(u) = 0.15
PR(u) = 1.0
```

For a 2-node graph with bidirectional edges, one node can have PR > 0.5 if it has more incoming edges.

**Tested Behavior:**
```python
# Star topology test
hub: pagerank=0.4757
spoke1: pagerank=0.1311
spoke2: pagerank=0.1311
spoke3: pagerank=0.1311
spoke4: pagerank=0.1311
```

Sum = 1.0 (correct)
Max = 0.4757 (< 1.0, but could be higher in extreme cases)

**Current Handling:**
Line 56 in `velocity.py`:
```python
norm_pagerank = min(pagerank, 1.0)
```

This caps PageRank at 1.0, which is correct defensive programming.

**Issue:**
The code comment on line 52 states "centrality measures - already 0-1 from rustworkx", but PageRank values are NOT guaranteed to be < 1.0 in all cases.

**Proposed Fix:**
Update the comment to reflect reality:
```python
# Centrality measures - cap at 1.0 for normalization
# - Eigenvector: L2-normalized, typically < 1 but not guaranteed
# - Betweenness: Normalized by rustworkx to [0, 1]
# - PageRank: Probability distribution (sum=1), individual values usually < 1
norm_eigen = min(eigenvector_centrality, 1.0)
norm_between = min(betweenness_centrality, 1.0)
norm_pagerank = min(pagerank, 1.0)
```

---

## 3. Medium-Severity Issues

### 3.1 Betweenness Normalization Assumption

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:158`

**Severity:** MEDIUM

**Description:**
The code correctly relies on `rustworkx.betweenness_centrality()` to return normalized values in [0, 1], but this is an implicit assumption not verified by tests.

**Mathematical Context:**
Rustworkx normalizes betweenness by dividing by:
```
(n-1)(n-2)/2  for undirected graphs
```

This ensures values are in [0, 1], with 1.0 representing a perfect bottleneck node.

**Verification:**
```python
# Star topology: hub has betweenness = 1.0
hub: betweenness=1.0000

# Chain topology (n=20): middle node has betweenness ≈ 0.5263
middle: betweenness=0.5263
```

**Risk:**
If rustworkx changes its normalization behavior in future versions, the pulse scores would become invalid.

**Proposed Fix:**
Add defensive capping and explicit testing:
```python
# Betweenness centrality - normalized by rustworkx to [0,1]
# Defensive cap in case of future API changes
norm_between = min(max(betweenness_centrality, 0.0), 1.0)
```

And add a regression test:
```python
def test_betweenness_normalization():
    """Verify rustworkx betweenness is normalized to [0, 1]."""
    # Create various topologies
    graphs = [create_star_graph(), create_chain_graph(), create_ring_graph()]
    for graph in graphs:
        centrality = rx.betweenness_centrality(graph)
        values = list(centrality.values())
        assert all(0 <= v <= 1 for v in values), \
            f"Betweenness values outside [0,1]: {values}"
```

---

### 3.2 Velocity Normalization Cap May Be Too Low

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:51`

**Severity:** MEDIUM

**Description:**
The velocity is normalized by capping at 3x baseline:
```python
norm_velocity = min(velocity / 3.0, 1.0)
```

This means a topic with 10x growth has the same normalized velocity (1.0) as a topic with 3x growth.

**Mathematical Implication:**
This creates a ceiling effect where very high-growth topics are indistinguishable from moderately high-growth topics.

**Example:**
```
velocity = 3.0  → norm_velocity = 1.0
velocity = 5.0  → norm_velocity = 1.0
velocity = 10.0 → norm_velocity = 1.0
velocity = 100.0 → norm_velocity = 1.0
```

All receive the same maximum contribution to pulse score: `0.25 * 1.0 = 0.25`

**Recommendation:**
Consider using a logarithmic or sigmoid normalization instead:

```python
# Option 1: Logarithmic normalization
import math
norm_velocity = min(math.log10(velocity + 1) / math.log10(4), 1.0)

# Option 2: Sigmoid normalization
norm_velocity = 1 / (1 + math.exp(-0.5 * (velocity - 3)))
```

Or increase the cap to 5x or 10x based on domain knowledge of typical growth patterns.

---

### 3.3 Empty Author Set in pulse_compute.py

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/services/pulse_compute.py:165`

**Severity:** MEDIUM

**Description:**
If the input `posts` list is empty, `max_authors = 0`, which triggers the division-by-zero bug in `compute_pulse_score`.

**Code Path:**
```python
# Line 165
max_authors = len({p.author for p in posts})  # 0 if posts is empty

# Later, line 175
pulse = compute_pulse_score(
    ...
    max_authors=max(max_authors, 1),  # FIXED: uses max(..., 1)
    ...
)
```

**Current Mitigation:**
Line 175 uses `max(max_authors, 1)`, which prevents the division by zero!

**Issue:**
This fix is **not applied in the direct call** to `compute_pulse_score` in velocity.py tests or other potential call sites.

**Verification:**
Looking at line 175:
```python
max_authors=max(max_authors, 1),  # This is safe
```

But the function signature (line 34-39 in velocity.py) has:
```python
def compute_pulse_score(
    ...
    max_authors: int = 100,
):
```

If a caller passes `max_authors=0` directly, it will fail.

**Recommendation:**
Move the validation into `compute_pulse_score` itself (see Critical Issue 1.1).

---

### 3.4 Floating-Point Precision in Weight Sum

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:63-68`

**Severity:** MEDIUM

**Description:**
The weights sum to exactly 1.0 when using decimal literals, but floating-point arithmetic may introduce small rounding errors.

**Mathematical Context:**
```python
weights = [0.25, 0.25, 0.20, 0.15, 0.15]
sum(weights) = 1.0  # Exact in this case
```

However, after multiplication and addition:
```python
score = 0.25 * v1 + 0.25 * v2 + 0.20 * v3 + 0.15 * v4 + 0.15 * v5
```

Floating-point errors can accumulate, potentially causing `score` to be slightly > 1.0 or < 0.0.

**Current Mitigation:**
```python
return round(score, 4)  # Rounds to 4 decimal places
```

This helps but doesn't guarantee `score ∈ [0, 1]`.

**Recommendation:**
Add explicit clamping:
```python
return round(max(0.0, min(score, 1.0)), 4)
```

This ensures the final score is always in [0, 1], even if floating-point errors push it outside.

---

## 4. Low-Severity Observations

### 4.1 Degree Centrality Fallback Not Used

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:122-131`

**Severity:** LOW

**Description:**
The `compute_centrality` function computes degree centrality as a fallback for PageRank, but this is never actually used because `compute_all_centrality` calls `compute_pagerank` directly.

**Code:**
```python
# Lines 122-131 in graph.py
degree_centrality: dict[int, float] = {}
if graph.num_nodes() > 0:
    degrees = {node: graph.degree(node) for node in graph.node_indices()}
    max_degree = max(degrees.values()) if degrees else 1
    degree_centrality = {
        node: degree / max_degree if max_degree > 0 else 0.0
        for node, degree in degrees.items()
    }
```

This is computed but then stored as `"pagerank"` in the result (line 137), which is confusing.

**Impact:**
The function `compute_centrality` is only called in tests, not in production code. Production uses `compute_all_centrality`, which correctly calls `compute_pagerank`.

**Recommendation:**
Either remove `compute_centrality` or update it to match `compute_all_centrality`.

---

### 4.2 No Test for Eigenvector Convergence Failure

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:164`

**Severity:** LOW

**Description:**
The code handles `rx.FailedToConverge` exceptions for eigenvector centrality by defaulting to 0.0 for all nodes. This is good defensive programming, but there are no tests verifying this behavior.

**Code:**
```python
try:
    eigenvector_raw = rx.eigenvector_centrality(undirected, max_iter=100)
    eigenvector = dict(eigenvector_raw) if eigenvector_raw else {}
except rx.FailedToConverge:
    eigenvector = dict.fromkeys(undirected.node_indices(), 0.0)
```

**Recommendation:**
Add a test that forces convergence failure:
```python
def test_eigenvector_convergence_failure():
    """Test handling of eigenvector centrality convergence failure."""
    # Create a graph that might not converge
    # (Note: rustworkx eigenvector usually converges, so we may need to mock)
    ...
```

---

### 4.3 PageRank Damping Factor Not Configurable

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py:148`

**Severity:** LOW

**Description:**
The PageRank damping factor is hardcoded to 0.85:
```python
def compute_pagerank(digraph: rx.PyDiGraph, alpha: float = 0.85) -> dict[int, float]:
```

While 0.85 is the standard value, different domains may benefit from different values.

**Recommendation:**
Make it configurable via environment variable or config file:
```python
DEFAULT_PAGERANK_ALPHA = float(os.getenv("PAGERANK_ALPHA", "0.85"))

def compute_pagerank(digraph: rx.PyDiGraph, alpha: float = DEFAULT_PAGERANK_ALPHA):
    ...
```

---

### 4.4 Emerging Topic Velocity of 2.0 Is Arbitrary

**Location:** `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py:21`

**Severity:** LOW

**Description:**
When a topic has no baseline data, the velocity is set to 2.0:
```python
return 2.0 if data.current_mentions > 0 else 1.0
```

**Mathematical Justification:**
The value 2.0 represents a "2x growth" signal, indicating the topic is emerging and should be ranked higher than topics with neutral velocity (1.0).

**Issue:**
This is an arbitrary choice with no documented rationale. Why 2.0 and not 1.5 or 3.0?

**Recommendation:**
Add a comment explaining the choice:
```python
# Emerging topic: assign 2.0 velocity (equivalent to 2x growth)
# This ensures new topics are surfaced without overwhelming established ones
return 2.0 if data.current_mentions > 0 else 1.0
```

Or make it configurable:
```python
EMERGING_TOPIC_VELOCITY = 2.0  # Configurable constant
```

---

## 5. Correctness Verification

### 5.1 Weight Sum Verification

**Formula:**
```
score = 0.25*velocity + 0.25*eigen + 0.20*between + 0.15*pagerank + 0.15*authors
```

**Weights:**
```
0.25 + 0.25 + 0.20 + 0.15 + 0.15 = 1.00 ✓
```

**Status:** CORRECT

---

### 5.2 Normalization Ranges

| Metric | Expected Range | Actual Range | Normalization Method | Status |
|--------|---------------|--------------|---------------------|--------|
| Velocity | [0, 1] | [0, 1] | `min(v/3.0, 1.0)` | CORRECT |
| Eigenvector | [0, 1] | [0, ~1] | `min(e, 1.0)` | CORRECT (with capping) |
| Betweenness | [0, 1] | [0, 1] | rustworkx built-in | CORRECT |
| PageRank | [0, 1] | [0, ~1] | `min(p, 1.0)` | CORRECT (with capping) |
| Authors | [0, 1] | [0, 1] | `min(u/max, 1.0)` | CORRECT (if max > 0) |

**Status:** Mostly correct, with issues noted above.

---

### 5.3 Pulse Score Bounds

**Expected:** `score ∈ [0, 1]`

**Actual:**
- With valid inputs: `score ∈ [0, 1]` ✓
- With negative inputs: `score < 0` ✗ (Critical Issue 1.2)
- With extreme inputs: `score ≤ 1` ✓ (capped correctly)

**Status:** FAILS with negative inputs

---

## 6. Numerical Stability Analysis

### 6.1 Division Operations

| Location | Operation | Risk | Mitigation |
|----------|-----------|------|------------|
| velocity.py:24 | `current / baseline` | Div by zero if baseline=0 | Checked on line 20 ✓ |
| velocity.py:62 | `unique / max_authors` | Div by zero if max=0 | NOT CHECKED ✗ |
| pulse_compute.py:165 | `len({authors})` | Can be 0 | Fixed with `max(..., 1)` on line 175 ✓ |

**Status:** 1 unmitigated division-by-zero risk

---

### 6.2 Floating-Point Precision

**Operations Analyzed:**
1. Weighted sum in pulse score: Low risk (only 5 multiplications)
2. Rounding to 4 decimals: Adequate precision for display
3. Min/max operations: Exact (no precision loss)

**Potential Issues:**
- Cumulative rounding errors: Negligible (< 10^-10)
- Loss of significance: Not observed in tested ranges

**Status:** STABLE

---

### 6.3 Overflow/Underflow

**Velocity Calculation:**
- Max velocity observed: 100x (velocity=100.0)
- Normalized: 100/3 = 33.33, capped to 1.0
- No overflow risk for float64

**Centrality Metrics:**
- All values naturally bounded by algorithms
- No overflow risk

**Status:** STABLE

---

## 7. Recommendations Summary

### Immediate Actions (Critical)
1. Add input validation to `compute_pulse_score` to reject negative values
2. Fix division-by-zero when `max_authors=0`
3. Add validation to `compute_velocity` to reject negative baselines

### Short-Term Actions (High)
4. Update code comments to reflect actual normalization behavior
5. Add defensive clamping: `max(0.0, min(score, 1.0))`
6. Add regression tests for edge cases

### Long-Term Actions (Medium)
7. Consider max-normalization for eigenvector centrality
8. Review velocity normalization cap (3x vs 5x vs logarithmic)
9. Add comprehensive edge case test suite

### Optional Improvements (Low)
10. Remove unused `compute_centrality` function or update it
11. Add test for eigenvector convergence failure
12. Make PageRank damping factor configurable
13. Document emerging topic velocity rationale

---

## 8. Test Coverage Recommendations

### Critical Edge Cases to Test
```python
# Test 1: Division by zero
test_pulse_score_with_zero_max_authors()

# Test 2: Negative inputs
test_pulse_score_rejects_negative_velocity()
test_pulse_score_rejects_negative_centrality()

# Test 3: Boundary values
test_pulse_score_all_zeros()
test_pulse_score_all_ones()
test_pulse_score_mixed_extremes()

# Test 4: Empty data
test_compute_velocity_empty_dataset()
test_graph_centrality_empty_graph()
```

### Numerical Stability Tests
```python
# Test 5: Floating-point precision
test_pulse_score_weight_sum_precision()
test_pulse_score_always_in_bounds()

# Test 6: Large graphs
test_graph_centrality_large_graph(n=1000)
test_pagerank_normalization_large_graph(n=1000)
```

---

## 9. Conclusion

The Community Pulse codebase demonstrates solid mathematical foundations with correct implementations of graph centrality algorithms and weighted combinations. However, **critical edge cases around division by zero and input validation must be addressed** before production deployment.

The main risks are:
1. **Runtime crashes** from division by zero (max_authors=0)
2. **Invalid scores** from negative input values
3. **Silent failures** from masked data quality issues

With the recommended fixes, the mathematical operations will be robust and production-ready.

---

## Appendix: Mathematical Formulas Reference

### Velocity
```
velocity = current_mentions / baseline_mentions  (if baseline > 0)
velocity = 2.0                                   (if baseline = 0 and current > 0)
velocity = 1.0                                   (if baseline = 0 and current = 0)
```

### Normalization
```
norm_velocity  = min(velocity / 3.0, 1.0)
norm_eigen     = min(eigenvector_centrality, 1.0)
norm_between   = min(betweenness_centrality, 1.0)
norm_pagerank  = min(pagerank, 1.0)
norm_authors   = min(unique_authors / max_authors, 1.0)
```

### Pulse Score
```
score = 0.25 * norm_velocity
      + 0.25 * norm_eigen
      + 0.20 * norm_between
      + 0.15 * norm_pagerank
      + 0.15 * norm_authors

Final: round(score, 4)
```

### Centrality Metrics
```
Betweenness: Σ(σ_st(v) / σ_st) / [(n-1)(n-2)/2]  (normalized)
Eigenvector: Av = λv (L2 normalized: ||v||₂ = 1)
PageRank: PR(u) = (1-α)/N + α * Σ(PR(v)/L(v))     (sums to 1)
```

---

**Files Reviewed:**
- `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/velocity.py`
- `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/analysis/graph.py`
- `/home/alext/community-pulse/.worktrees/poc-implementation/src/community_pulse/services/pulse_compute.py`

**Test Files Examined:**
- `/home/alext/community-pulse/.worktrees/poc-implementation/tests/analysis/test_graph.py`
- `/home/alext/community-pulse/.worktrees/poc-implementation/tests/test_integration.py`
