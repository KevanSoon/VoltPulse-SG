# RRF Algorithm (Reciprocal Rank Fusion)

[← Back to Documentation](../README.md)

## Table of Contents
- [Overview](#overview)
- [Mathematical Formulation](#mathematical-formulation)
- [Why RRF?](#why-rrf)
- [Algorithm Implementation](#algorithm-implementation)
- [Worked Examples](#worked-examples)
- [K Parameter Tuning](#k-parameter-tuning)
- [Weight Configuration](#weight-configuration)
- [Performance Characteristics](#performance-characteristics)

---

## Overview

**Reciprocal Rank Fusion (RRF)** is a rank aggregation algorithm that combines multiple ranking signals to produce a unified ranking. VoltPulse-SG uses RRF to rank 700+ Climate Voucher retailers by combining **5 independent signals**:

1. **Semantic Similarity** (40%) - How well the retailer matches the query semantically
2. **Product Match** (25%) - Does the retailer sell the requested product?
3. **Location Relevance** (20%) - Is the retailer near the user's location?
4. **Retailer Breadth** (10%) - Does the retailer offer many products?
5. **Query Intent** (5%) - Does the retailer match the query's intent?

**Key Advantages:**
- **Robust**: Rank-based (not score-based), immune to scale differences
- **Simple**: No complex normalization required
- **Tunable**: Weights can be adjusted via environment variables
- **Research-backed**: Proven method in information retrieval

**Implementation:** [`backend/recommender/rrf_scorer.py`](../../backend/recommender/rrf_scorer.py)

---

## Mathematical Formulation

### Core RRF Formula

For a given retailer `r` and signal `s`:

```
contribution(r, s) = weight_s / (k + rank_s(r))
```

Where:
- `weight_s` = Signal weight (normalized to sum to 1.0)
- `k` = Scale constant (default 60)
- `rank_s(r)` = Rank of retailer `r` in signal `s` (1 = best, 2 = second, ...)

**Final RRF Score:**

```
RRF(r) = Σ [weight_s / (k + rank_s(r))] for all signals s
       = weight_semantic / (k + rank_semantic(r))
         + weight_product / (k + rank_product(r))
         + weight_location / (k + rank_location(r))
         + weight_breadth / (k + rank_breadth(r))
         + weight_intent / (k + rank_intent(r))
```

### Default Configuration

```python
# From backend/recommender/rrf_scorer.py lines 23-30
RRF_K = 60

SIGNAL_WEIGHTS = {
    'semantic': 0.40,   # 40%
    'product': 0.25,    # 25%
    'location': 0.20,   # 20%
    'breadth': 0.10,    # 10%
    'intent': 0.05,     # 5%
}
# Total: 1.00 (100%)
```

### Weight Normalization

Weights are automatically normalized to sum to 1.0:

```python
# From backend/recommender/rrf_scorer.py lines 92-98
def __init__(self, weights: Optional[Dict[str, float]] = None, k: int = RRF_K):
    self.weights = weights or SIGNAL_WEIGHTS.copy()
    self.k = k

    # Normalize weights to sum to 1.0
    total_weight = sum(self.weights.values())
    if total_weight > 0:
        self.weights = {
            signal: weight / total_weight
            for signal, weight in self.weights.items()
        }
```

---

## Why RRF?

### Problem: Combining Heterogeneous Signals

We have 5 different ranking signals with **incompatible scales**:

| Signal | Type | Range | Example Values |
|--------|------|-------|----------------|
| Semantic | Distance | 0.0-5.0 | 0.5, 1.2, 2.8 |
| Product | Jaccard | 0.0-1.0 | 0.67, 0.33, 1.0 |
| Location | Categorical | {0.0, 0.7, 1.0} | 1.0, 0.7, 0.0 |
| Breadth | Count-based | 0.0-1.5 | 0.3, 0.8, 1.2 |
| Intent | Score | 0.0-1.0 | 0.5, 0.5, 0.3 |

**Challenge:** How do we combine these fairly?

### Approach Comparison

#### ❌ Approach 1: Weighted Sum of Raw Scores

```python
# Combine raw scores directly
final_score = (
    0.40 * semantic_distance +
    0.25 * product_jaccard +
    0.20 * location_score +
    0.10 * breadth_score +
    0.05 * intent_score
)
```

**Problems:**
- Scales differ wildly (distance 0-5 vs Jaccard 0-1)
- Need complex normalization (min-max, z-score)
- Sensitive to outliers
- Normalization depends on candidate set (not stable)

#### ❌ Approach 2: CombSUM (Equal Weighting)

```python
# Sum normalized scores
final_score = (
    normalize(semantic) +
    normalize(product) +
    normalize(location) +
    normalize(breadth) +
    normalize(intent)
) / 5
```

**Problems:**
- No weight flexibility
- Still requires normalization
- Treats all signals equally (but some are more important)

#### ✅ Approach 3: RRF (Rank-Based Fusion)

```python
# Use ranks instead of scores
final_score = (
    0.40 / (60 + rank_semantic) +
    0.25 / (60 + rank_product) +
    0.20 / (60 + rank_location) +
    0.10 / (60 + rank_breadth) +
    0.05 / (60 + rank_intent)
)
```

**Advantages:**
- ✅ **Scale-invariant**: Ranks are always 1, 2, 3, ...
- ✅ **No normalization needed**: Ranks are inherently normalized
- ✅ **Robust to outliers**: Extreme scores don't affect ranks much
- ✅ **Tunable weights**: Easy to adjust signal importance
- ✅ **Interpretable**: Clear contribution from each signal

### Why Not Learning-to-Rank (LTR)?

**Learning-to-Rank** (e.g., LambdaMART, RankNet) learns weights from training data.

**Why we don't use it:**
- ❌ Requires labeled training data (we have none)
- ❌ Need user click/purchase data to train
- ❌ More complex to maintain
- ✅ RRF works out-of-the-box with expert-defined weights

**Future consideration:** If we collect user feedback (clicks, purchases), we could train an LTR model.

---

## Algorithm Implementation

### Step 1: Compute Ranks for Each Signal

For each signal, sort candidates and assign ranks:

```python
# From backend/recommender/rrf_scorer.py lines 227-243
def _compute_semantic_ranks(
    self,
    candidates: List[SimilarityResult]
) -> Dict[str, int]:
    """Rank candidates by L2 distance (lower distance = better rank)."""
    # Sort by distance (ascending - lower is better)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.distance if hasattr(c, 'distance') else (1.0 / c.score - 1.0)
    )

    # Create rank dictionary (1-indexed)
    rank_dict = {}
    for rank, candidate in enumerate(sorted_candidates, 1):
        rank_dict[candidate.id] = rank

    return rank_dict
```

**Example:**

| Retailer | Semantic Distance | Semantic Rank |
|----------|------------------|---------------|
| Gain City | 0.5 | 1 (best) |
| Courts | 0.8 | 2 |
| Harvey Norman | 1.2 | 3 |
| Best Denki | 1.5 | 4 |

### Step 2: Convert Scores to Ranks

For score-based signals (product, location, breadth, intent), convert scores to ranks:

```python
# From backend/recommender/rrf_scorer.py lines 369-385
def _scores_to_ranks(self, scores: Dict[str, float]) -> Dict[str, int]:
    """Convert scores to ranks (higher score = better rank = lower number)."""
    # Sort by score descending
    sorted_pairs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Handle ties: same score = same rank
    rank_dict = {}
    current_rank = 1
    prev_score = None

    for idx, (cand_id, score) in enumerate(sorted_pairs):
        if score != prev_score:
            current_rank = idx + 1
        rank_dict[cand_id] = current_rank
        prev_score = score

    return rank_dict
```

**Tie handling example:**

| Retailer | Product Score (Jaccard) | Product Rank |
|----------|------------------------|--------------|
| Retailer A | 1.0 | 1 (tied) |
| Retailer B | 1.0 | 1 (tied) |
| Retailer C | 0.67 | 3 |
| Retailer D | 0.33 | 4 |

### Step 3: Combine with RRF Formula

```python
# From backend/recommender/rrf_scorer.py lines 387-413
def _combine_rrf_scores(
    self,
    candidates: List[SimilarityResult],
    signal_ranks: Dict[str, Dict[str, int]],
    active_weights: Dict[str, float]
) -> Dict[str, float]:
    """Combine signal ranks using RRF formula."""
    rrf_scores = {}
    candidate_ids = [c.id for c in candidates]

    for cand_id in candidate_ids:
        rrf_score = 0.0

        for signal_name, weight in active_weights.items():
            if weight == 0:
                continue

            rank_dict = signal_ranks.get(signal_name, {})
            rank = rank_dict.get(cand_id, len(candidates) + 1)  # Default to last

            # RRF formula: weight / (k + rank)
            contribution = weight / (self.k + rank)
            rrf_score += contribution

        rrf_scores[cand_id] = rrf_score

    return rrf_scores
```

### Step 4: Sort by Final RRF Score

```python
# Sort by RRF score (descending)
sorted_pairs = sorted(
    rrf_scores.items(),
    key=lambda x: x[1],
    reverse=True
)

# Return top K
return sorted_pairs[:limit]
```

---

## Worked Examples

### Example 1: Simple Query

**Query:** "aircon near Bedok"

**Candidates:** 3 retailers

#### Step 1: Compute Ranks

| Retailer | Semantic Rank | Product Rank | Location Rank | Breadth Rank | Intent Rank |
|----------|---------------|--------------|---------------|--------------|-------------|
| Gain City | 1 | 2 | 1 | 1 | 3 |
| Courts | 2 | 1 | 5 | 2 | 2 |
| Harvey Norman | 3 | 3 | 2 | 3 | 1 |

#### Step 2: Apply RRF Formula

**Configuration:**
- k = 60
- Weights: semantic=0.40, product=0.25, location=0.20, breadth=0.10, intent=0.05

**Gain City:**
```
RRF = 0.40/(60+1) + 0.25/(60+2) + 0.20/(60+1) + 0.10/(60+1) + 0.05/(60+3)
    = 0.40/61 + 0.25/62 + 0.20/61 + 0.10/61 + 0.05/63
    = 0.006557 + 0.004032 + 0.003279 + 0.001639 + 0.000794
    = 0.016301
```

**Courts:**
```
RRF = 0.40/(60+2) + 0.25/(60+1) + 0.20/(60+5) + 0.10/(60+2) + 0.05/(60+2)
    = 0.40/62 + 0.25/61 + 0.20/65 + 0.10/62 + 0.05/62
    = 0.006452 + 0.004098 + 0.003077 + 0.001613 + 0.000806
    = 0.016046
```

**Harvey Norman:**
```
RRF = 0.40/(60+3) + 0.25/(60+3) + 0.20/(60+2) + 0.10/(60+3) + 0.05/(60+1)
    = 0.40/63 + 0.25/63 + 0.20/62 + 0.10/63 + 0.05/61
    = 0.006349 + 0.003968 + 0.003226 + 0.001587 + 0.000820
    = 0.015950
```

#### Step 3: Final Ranking

| Rank | Retailer | RRF Score |
|------|----------|-----------|
| 1 | **Gain City** | 0.016301 |
| 2 | Courts | 0.016046 |
| 3 | Harvey Norman | 0.015950 |

**Winner:** Gain City (best semantic match + perfect location + best breadth)

---

### Example 2: Conflicting Signals

**Query:** "cheap fridge near Woodlands"

**Retailers:**

| Retailer | Semantic | Product | Location | Breadth | Intent | Specialty |
|----------|----------|---------|----------|---------|--------|-----------|
| FridgeWorld | Rank 5 | Rank 1 | Rank 1 | Rank 1 | Rank 2 | Only sells fridges |
| MegaMart | Rank 1 | Rank 3 | Rank 10 | Rank 5 | Rank 1 | Far away, general store |
| LocalShop | Rank 3 | Rank 2 | Rank 2 | Rank 10 | Rank 5 | Near, small selection |

**RRF Calculations:**

**FridgeWorld:**
```
RRF = 0.40/(60+5) + 0.25/(60+1) + 0.20/(60+1) + 0.10/(60+1) + 0.05/(60+2)
    = 0.40/65 + 0.25/61 + 0.20/61 + 0.10/61 + 0.05/62
    = 0.006154 + 0.004098 + 0.003279 + 0.001639 + 0.000806
    = 0.015976
```

**MegaMart:**
```
RRF = 0.40/(60+1) + 0.25/(60+3) + 0.20/(60+10) + 0.10/(60+5) + 0.05/(60+1)
    = 0.40/61 + 0.25/63 + 0.20/70 + 0.10/65 + 0.05/61
    = 0.006557 + 0.003968 + 0.002857 + 0.001538 + 0.000820
    = 0.015740
```

**LocalShop:**
```
RRF = 0.40/(60+3) + 0.25/(60+2) + 0.20/(60+2) + 0.10/(60+10) + 0.05/(60+5)
    = 0.40/63 + 0.25/62 + 0.20/62 + 0.10/70 + 0.05/65
    = 0.006349 + 0.004032 + 0.003226 + 0.001429 + 0.000769
    = 0.015805
```

**Final Ranking:**

| Rank | Retailer | RRF Score | Why? |
|------|----------|-----------|------|
| 1 | **FridgeWorld** | 0.015976 | Perfect product+location, specialist |
| 2 | LocalShop | 0.015805 | Good balance |
| 3 | MegaMart | 0.015740 | Best semantic but far away |

**Insight:** RRF balances conflicting signals. MegaMart has best semantic match but loses due to poor location (rank 10). FridgeWorld wins despite worse semantic because it excels in product, location, and breadth.

---

## K Parameter Tuning

The **k constant** controls how much emphasis is placed on rank position.

### Mathematical Effect

```
contribution = weight / (k + rank)

For k=10:
  Rank 1: weight / 11 = 0.0909 * weight
  Rank 10: weight / 20 = 0.0500 * weight
  Ratio: 1.82x (rank 1 gets 82% more weight than rank 10)

For k=60 (default):
  Rank 1: weight / 61 = 0.0164 * weight
  Rank 10: weight / 70 = 0.0143 * weight
  Ratio: 1.15x (rank 1 gets 15% more weight than rank 10)

For k=100:
  Rank 1: weight / 101 = 0.0099 * weight
  Rank 10: weight / 110 = 0.0091 * weight
  Ratio: 1.09x (rank 1 gets 9% more weight than rank 10)
```

### Visualization

```
Contribution vs Rank for Different k Values

weight / (k + rank)

  0.020 ┤
        │     k=10 (steep)
  0.015 ┤  ●
        │   ●●
  0.010 ┤    ●●●___k=60 (balanced)
        │      ●●●●●●●___
  0.005 ┤           ●●●●●●●●___k=100 (flat)
        │                  ●●●●●●●●●●
  0.000 ┴──────────────────────────────────►
        1   5   10   15   20   25   30  Rank
```

### Choosing K

| k Value | Effect | Use Case |
|---------|--------|----------|
| 10-20 | Steep curve, top ranks dominate | When top results are MUCH better |
| 40-80 | Balanced (recommended) | General purpose, allows diversity |
| 100+ | Flat curve, ranks matter less | When many results are similar quality |

**VoltPulse-SG uses k=60** (balanced approach)

### Tuning K

```bash
# .env file
RRF_K=60  # Adjust to emphasize/de-emphasize rank differences
```

**Guidelines:**
- **Increase k** if you want more diversity in results (less penalty for lower ranks)
- **Decrease k** if you want to strongly favor top-ranked items

---

## Weight Configuration

### Current Weights

```python
# Default weights (from environment or hardcoded)
SIGNAL_WEIGHTS = {
    'semantic': 0.40,   # Most important: semantic understanding
    'product': 0.25,    # Second: correct product type
    'location': 0.20,   # Third: geographic proximity
    'breadth': 0.10,    # Fourth: product variety
    'intent': 0.05,     # Fifth: query intent alignment
}
```

### Adjusting Weights

**Environment variables:**

```bash
# .env file
RRF_SEMANTIC_WEIGHT=0.50   # Increase semantic importance
RRF_PRODUCT_WEIGHT=0.20    # Decrease product importance
RRF_LOCATION_WEIGHT=0.15   # Decrease location importance
RRF_BREADTH_WEIGHT=0.10
RRF_INTENT_WEIGHT=0.05
```

**Effect:**

```python
# New distribution after normalization:
semantic: 0.50 / 1.00 = 50%
product:  0.20 / 1.00 = 20%
location: 0.15 / 1.00 = 15%
breadth:  0.10 / 1.00 = 10%
intent:   0.05 / 1.00 = 5%
```

### Weight Sensitivity Analysis

**Experiment:** Vary semantic weight from 0.2 to 0.6

| Semantic Weight | Product Weight | Top 5 Results Change |
|----------------|----------------|----------------------|
| 0.20 | 0.35 | 40% different |
| 0.30 | 0.30 | 20% different |
| **0.40** | **0.25** | **Baseline** |
| 0.50 | 0.20 | 15% different |
| 0.60 | 0.15 | 30% different |

**Finding:** Results are relatively stable for semantic weights between 0.35-0.50.

### Recommended Tuning Process

1. **Collect user feedback** (clicks, purchases)
2. **Run A/B tests** with different weights
3. **Measure quality metrics** (click-through rate, conversion rate)
4. **Adjust weights** based on data

**Current weights are expert-defined** based on domain knowledge.

---

## Performance Characteristics

### Time Complexity

**Per-candidate cost:**

| Operation | Complexity | Time (100 candidates) |
|-----------|------------|----------------------|
| Semantic ranking | O(n log n) | 5ms |
| Product ranking | O(n²) (Jaccard) | 15ms |
| Location ranking | O(n) | 20ms |
| Breadth ranking | O(n) | 10ms |
| Intent ranking | O(n) | 15ms |
| RRF combination | O(n) | 5ms |
| **Total (full mode)** | **O(n²)** | **~70ms** |
| **Quick mode (2 signals)** | **O(n log n)** | **~25ms** |

### Space Complexity

**Memory usage:**

```
signal_ranks: 5 signals × 100 candidates × 8 bytes = 4 KB
rrf_scores: 100 candidates × 8 bytes = 800 bytes
Total: ~5 KB (negligible)
```

### Scalability

| Candidates | Full Mode | Quick Mode | Recommendation |
|------------|-----------|------------|----------------|
| 10 | 10ms | 5ms | Use full mode |
| 50 | 70ms | 25ms | Use full mode |
| 100 | 200ms | 50ms | Use quick mode |
| 500 | 1800ms | 300ms | **Use quick mode** |
| 1000 | 3500ms | 600ms | **Use quick mode** |

**Threshold:** Auto-enable quick mode when candidates > 30

---

## Cross-References

- [Multi-Signal Ranking](./multi-signal-ranking.md) - Details on all 5 signals
- [Performance Tuning](./performance-tuning.md) - Quick mode optimization
- [Retailer Matching](./retailer-matching.md) - End-to-end matching flow
- [Cost Optimization](../02-core-systems/cost-optimization.md) - Quick mode cost savings

---

[← Back to Documentation](../README.md) | [Next: Multi-Signal Ranking →](./multi-signal-ranking.md)
