# Multi-Signal Ranking

[← Back to Documentation](../README.md)

## Table of Contents
- [Overview](#overview)
- [Signal 1: Semantic Similarity (40%)](#signal-1-semantic-similarity-40)
- [Signal 2: Product Match (25%)](#signal-2-product-match-25)
- [Signal 3: Location Relevance (20%)](#signal-3-location-relevance-20)
- [Signal 4: Retailer Breadth (10%)](#signal-4-retailer-breadth-10)
- [Signal 5: Query Intent (5%)](#signal-5-query-intent-5)
- [Signal Combination Strategy](#signal-combination-strategy)
- [Implementation Examples](#implementation-examples)

---

## Overview

VoltPulse-SG's recommender system uses **5 independent ranking signals** that are combined via RRF (Reciprocal Rank Fusion) to produce a unified retailer ranking. Each signal captures a different aspect of relevance.

**Signal Weights (default):**
- **Semantic Similarity** (40%) - Semantic understanding via SEALION embeddings
- **Product Match** (25%) - Exact product availability
- **Location Relevance** (20%) - Geographic proximity
- **Retailer Breadth** (10%) - Product variety and online presence
- **Query Intent** (5%) - Query type alignment

**Implementation:** [`backend/recommender/rrf_scorer.py`](../../backend/recommender/rrf_scorer.py)

---

## Signal 1: Semantic Similarity (40%)

### Purpose

Capture **semantic relevance** between user query and retailer description using vector embeddings.

### How It Works

**Step 1: Encode query with SEALION**
```python
query_text = "Find retailers selling air conditioners near Bedok"
query_embedding = await encoder.encode(query_text)  # 1024-dim vector
```

**Step 2: Retailers have pre-computed embeddings**
```python
# From backend/services/retailer_loader.py
retailer_text = """
Climate Voucher Retailer: Gain City (Bedok)
Address: 123 Bedok North Ave 1
Products Available: air_conditioners, refrigerators, washing_machines
Singapore Planning Area: Bedok
"""
retailer_embedding = await encoder.encode(retailer_text)  # Stored in DB
```

**Step 3: Compute L2 distance**
```sql
SELECT retailer_id, embedding <-> query_embedding AS distance
FROM my_embeddings
WHERE metadata->>'form_type' = 'retailer'
ORDER BY distance ASC
```

**Step 4: Rank by distance (lower = better)**

### Implementation

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

### Example

**Query:** "energy efficient cooling system"

| Retailer | Description | L2 Distance | Semantic Rank |
|----------|-------------|-------------|---------------|
| Gain City | "Air conditioners, energy-efficient models..." | 0.5 | 1 (best) |
| Courts | "Appliances including AC, fridges..." | 0.8 | 2 |
| Harvey Norman | "Electronics and home appliances..." | 1.2 | 3 |

**Why it works:**
- "energy efficient cooling system" is semantically similar to "air conditioners, energy-efficient"
- SEALION understands "cooling system" = "air conditioner"
- Captures fuzzy matching that keyword search misses

### Weight Justification (40%)

**Highest weight** because:
- Captures user intent holistically
- Handles synonyms and paraphrasing
- Most flexible signal (works for any query type)
- SEALION embeddings are high-quality (1024-dim, ASEAN-focused)

---

## Signal 2: Product Match (25%)

### Purpose

Measure **exact product availability** using set overlap (Jaccard similarity).

### Jaccard Similarity Formula

```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|

where:
  A = query products (set)
  B = retailer products (set)
  ∩ = intersection (common products)
  ∪ = union (all products)
```

### Implementation

```python
# From backend/recommender/rrf_scorer.py lines 245-267
def _compute_product_ranks(
    self,
    candidates: List[SimilarityResult],
    query_products: Set[str]
) -> Dict[str, int]:
    """Rank by product match using Jaccard similarity."""
    scores = {}

    for candidate in candidates:
        form_data = candidate.form_data or {}
        retailer_products = set(form_data.get("eligible_products", []))

        if not query_products:
            # No product filter: all tied with medium score
            scores[candidate.id] = 0.5
        else:
            # Jaccard similarity: intersection / union
            intersection = len(query_products & retailer_products)
            union = len(query_products | retailer_products)
            scores[candidate.id] = intersection / union if union > 0 else 0.0

    # Convert scores to ranks (higher score = better rank)
    return self._scores_to_ranks(scores)
```

### Example 1: Perfect Match

**Query products:** `{air_conditioners}`
**Retailer A products:** `{air_conditioners, refrigerators, washing_machines}`

```
Intersection: {air_conditioners} = 1
Union: {air_conditioners, refrigerators, washing_machines} = 3
Jaccard: 1/3 = 0.33
```

**Retailer B products:** `{air_conditioners}`

```
Intersection: {air_conditioners} = 1
Union: {air_conditioners} = 1
Jaccard: 1/1 = 1.0  (perfect match!)
```

**Ranking:** Retailer B (1.0) > Retailer A (0.33)

### Example 2: Multiple Products

**Query products:** `{air_conditioners, refrigerators}`
**Retailer A products:** `{air_conditioners, refrigerators, washing_machines}`

```
Intersection: {air_conditioners, refrigerators} = 2
Union: {air_conditioners, refrigerators, washing_machines} = 3
Jaccard: 2/3 = 0.67
```

**Retailer B products:** `{air_conditioners}`

```
Intersection: {air_conditioners} = 1
Union: {air_conditioners, refrigerators} = 2
Jaccard: 1/2 = 0.50
```

**Ranking:** Retailer A (0.67) > Retailer B (0.50)

### Example 3: No Match

**Query products:** `{air_conditioners}`
**Retailer C products:** `{led_lights, washing_machines}`

```
Intersection: {} = 0
Union: {air_conditioners, led_lights, washing_machines} = 3
Jaccard: 0/3 = 0.0  (no match)
```

**Result:** Rank = last (filtered out or heavily penalized)

### Weight Justification (25%)

**Second highest weight** because:
- Exact match is critical (user wants specific product)
- Avoids recommending retailers without the product
- Simple and interpretable (set overlap)
- Complements semantic signal (which can be fuzzy)

---

## Signal 3: Location Relevance (20%)

### Purpose

Assess **geographic proximity** using Singapore planning areas and postal codes.

### Tiered Scoring System

**Tier 1 (score = 1.0): Exact Planning Area Match**
```
Query: "Bedok"
Retailer planning_area: "Bedok"
Score: 1.0
```

**Tier 2 (score = 0.7): Postal District Match**
```
Query: "46" (postal code prefix)
Retailer postal_code: "460123"
Postal prefix: "46"
Score: 0.7
```

**Tier 3 (score = 0.0): No Match**
```
Query: "Bedok"
Retailer planning_area: "Jurong"
Score: 0.0
```

### Implementation

```python
# From backend/recommender/rrf_scorer.py lines 269-302
def _compute_location_ranks(
    self,
    candidates: List[SimilarityResult],
    query_area: Optional[str]
) -> Dict[str, int]:
    """Rank by location relevance with tiered scoring."""
    scores = {}

    for candidate in candidates:
        form_data = candidate.form_data or {}
        retailer_area = form_data.get("planning_area", "").lower()
        retailer_postal = form_data.get("postal_code", "")
        postal_prefix = retailer_postal[:2] if retailer_postal and len(retailer_postal) >= 2 else None

        if not query_area:
            # No location filter: all get medium score
            scores[candidate.id] = 0.5
        else:
            query_area_lower = query_area.lower()

            # Tier 1: Exact planning area match
            if retailer_area and query_area_lower in retailer_area:
                scores[candidate.id] = 1.0

            # Tier 2: Postal district match
            elif postal_prefix and query_area_lower.isdigit() and len(query_area_lower) >= 2:
                if postal_prefix == query_area_lower[:2]:
                    scores[candidate.id] = 0.7
                else:
                    scores[candidate.id] = 0.0
            else:
                scores[candidate.id] = 0.0

    return self._scores_to_ranks(scores)
```

### Singapore Planning Areas

**55 planning areas** covering all of Singapore:

```python
# From backend/recommender/planning_areas.py
PLANNING_AREAS = {
    "ang_mo_kio": "Ang Mo Kio",
    "bedok": "Bedok",
    "bishan": "Bishan",
    "bukit_batok": "Bukit Batok",
    "bukit_merah": "Bukit Merah",
    "bukit_panjang": "Bukit Panjang",
    "bukit_timah": "Bukit Timah",
    # ... 48 more areas
}
```

### Postal District Mapping

**Singapore has 28 postal districts** (first 2 digits):

| Postal District | Area |
|----------------|------|
| 01-08 | City & Central |
| 09-10 | Orchard & River Valley |
| 11-13 | Novena & Newton |
| 14-16 | East Coast & Marine Parade |
| 17-18, 43-46 | **Bedok** |
| 19-21, 47-48 | Tampines & Pasir Ris |
| ... | ... |

### Example Scenarios

**Scenario 1: Exact Match**
```
Query: "Where to buy aircon near Bedok?"
Extracted location: "Bedok"

Retailer A: planning_area = "Bedok"
→ Tier 1 match, score = 1.0, rank = 1

Retailer B: planning_area = "Tampines"
→ No match, score = 0.0, rank = 5
```

**Scenario 2: Postal Code Match**
```
Query: "Retailers near 460123"
Extracted postal: "46"

Retailer A: postal_code = "460456"
→ Tier 2 match (46 prefix), score = 0.7, rank = 1

Retailer B: postal_code = "520123"
→ No match (52 ≠ 46), score = 0.0, rank = 3
```

**Scenario 3: No Location Specified**
```
Query: "Where to buy aircon?"
Location: None

All retailers: score = 0.5 (neutral)
→ Location signal doesn't differentiate
```

### Weight Justification (20%)

**Third highest weight** because:
- Geographic convenience matters for in-store purchases
- Singapore is small (30km × 50km), but public transport varies
- Balances with semantic/product (20% prevents location dominating)
- Tiered system (1.0, 0.7, 0.0) provides nuance

---

## Signal 4: Retailer Breadth (10%)

### Purpose

Reward retailers with **diverse product offerings** and **online presence**.

### Formula

```
Breadth Score = (product_count / 10) + (has_website ? 0.5 : 0)

where:
  product_count = number of Climate Voucher eligible products (0-10)
  has_website = whether retailer has a website
```

**Normalization:** Scores are normalized to 0-1 range before ranking.

### Implementation

```python
# From backend/recommender/rrf_scorer.py lines 304-330
def _compute_breadth_ranks(
    self,
    candidates: List[SimilarityResult]
) -> Dict[str, int]:
    """Rank by retailer breadth (product count + website)."""
    scores = {}

    for candidate in candidates:
        form_data = candidate.form_data or {}

        # Product breadth (0-1)
        products = form_data.get("eligible_products", [])
        product_breadth = len(products) / 10.0  # Max 10 Climate Voucher products

        # Website presence (0.5 bonus)
        website = form_data.get("website")
        website_score = 0.5 if website and website != "Not available" else 0.0

        # Combined score (0-1.5)
        scores[candidate.id] = product_breadth + website_score

    # Normalize to 0-1
    max_score = max(scores.values()) if scores else 1.0
    if max_score > 0:
        scores = {cid: score / max_score for cid, score in scores.items()}

    return self._scores_to_ranks(scores)
```

### Climate Voucher Eligible Products (10 types)

```python
ELIGIBLE_PRODUCTS = [
    "refrigerators",
    "air_conditioners",
    "dc_fans",
    "led_lights",
    "washing_machines",
    "water_closets",
    "sink_bib_taps_mixers",
    "basin_taps_mixers",
    "shower_taps_mixers",
    "heat_pump_water_heaters"
]
```

### Example Calculations

**Retailer A (Specialist):**
```
Products: [air_conditioners]  (1 product)
Website: None

Breadth score = (1/10) + 0.0 = 0.1
Normalized (if max=1.5): 0.1 / 1.5 = 0.067
Rank: Lower (specialist with no online presence)
```

**Retailer B (Generalist with website):**
```
Products: [air_conditioners, refrigerators, washing_machines,
           led_lights, dc_fans]  (5 products)
Website: www.retailerb.com

Breadth score = (5/10) + 0.5 = 1.0
Normalized: 1.0 / 1.5 = 0.667
Rank: Higher (diverse + online)
```

**Retailer C (Full range with website):**
```
Products: All 10 products
Website: www.megastore.com

Breadth score = (10/10) + 0.5 = 1.5
Normalized: 1.5 / 1.5 = 1.0
Rank: Highest (maximum breadth)
```

### Rationale

**Product diversity bonus:**
- More products → more likely to find what user needs
- One-stop shopping convenience

**Website bonus:**
- Online research before visiting store
- Check inventory, prices, promotions
- Contact information easily accessible

### Weight Justification (10%)

**Fourth weight** because:
- Breadth is nice-to-have, not essential (user has specific product in mind)
- Lower weight ensures specialist stores aren't penalized too much
- Provides tiebreaker when other signals are equal
- Website bonus (50% of breadth score) encourages digital presence

---

## Signal 5: Query Intent (5%)

### Purpose

Align results with **query type** (product-focused vs location-focused).

### Intent Detection

**Method:** Keyword counting

```python
# From backend/recommender/rrf_scorer.py lines 41-57
PRODUCT_KEYWORDS = [
    'fridge', 'refrigerator', 'freezer',
    'aircon', 'air conditioner', 'ac', 'cooling',
    'fan', 'ceiling fan', 'dc fan',
    'light', 'led', 'bulb', 'lamp', 'lighting',
    'wash', 'washing machine', 'washer', 'laundry',
    'toilet', 'wc', 'water closet', 'bathroom',
    'tap', 'faucet', 'mixer', 'sink', 'basin', 'shower',
    'heater', 'water heater', 'heat pump',
]

LOCATION_KEYWORDS = [
    'bedok', 'ang mo kio', 'tampines', 'jurong', 'yishun',
    'bishan', 'toa payoh', 'queenstown', 'geylang', 'hougang',
    'near', 'location', 'area', 'postal', 'district',
    'nearby', 'close', 'around', 'vicinity',
]
```

**Intent Classification:**

```
product_count = count of product keywords in query
location_count = count of location keywords in query

if product_count > location_count:
    intent = 'product'  → Reward retailers with many products
elif location_count > product_count:
    intent = 'location'  → All retailers treated equally (location signal handles this)
else:
    intent = 'mixed'  → Neutral scoring
```

### Implementation

```python
# From backend/recommender/rrf_scorer.py lines 332-367
def _compute_intent_ranks(
    self,
    candidates: List[SimilarityResult],
    query_text: str
) -> Dict[str, int]:
    """Rank by query intent alignment."""
    query_lower = query_text.lower()

    # Count keyword mentions
    product_count = sum(1 for kw in PRODUCT_KEYWORDS if kw in query_lower)
    location_count = sum(1 for kw in LOCATION_KEYWORDS if kw in query_lower)

    # Determine intent
    if product_count > location_count:
        intent = 'product'
    elif location_count > product_count:
        intent = 'location'
    else:
        intent = 'mixed'

    scores = {}
    for candidate in candidates:
        form_data = candidate.form_data or {}

        if intent == 'product':
            # Reward product breadth
            products = form_data.get("eligible_products", [])
            scores[candidate.id] = len(products) / 10.0
        elif intent == 'location':
            # All equal (location signal already handles proximity)
            scores[candidate.id] = 0.5
        else:
            # Mixed: average
            scores[candidate.id] = 0.5

    return self._scores_to_ranks(scores)
```

### Example Scenarios

**Scenario 1: Product-Focused**
```
Query: "Best energy-efficient air conditioner with inverter technology"

product_count = 2  (air conditioner, inverter)
location_count = 0
Intent: 'product'

Scoring:
  Retailer with 8 products: 8/10 = 0.8
  Retailer with 3 products: 3/10 = 0.3
  Retailer with 1 product: 1/10 = 0.1

Result: Generalists ranked higher (more product variety)
```

**Scenario 2: Location-Focused**
```
Query: "Where to buy aircon near Bedok area?"

product_count = 1  (aircon)
location_count = 3  (near, bedok, area)
Intent: 'location'

Scoring:
  All retailers: 0.5 (neutral)

Result: Location signal (20% weight) dominates, intent doesn't differentiate
```

**Scenario 3: Mixed**
```
Query: "Aircon shops"

product_count = 1  (aircon)
location_count = 0
Intent: 'mixed'  (tie)

Scoring:
  All retailers: 0.5 (neutral)

Result: Intent signal doesn't influence ranking
```

### Weight Justification (5%)

**Lowest weight** because:
- Keyword-based detection is heuristic (not always accurate)
- Other signals already capture intent:
  - Semantic signal understands query meaning
  - Product signal ensures correct product
  - Location signal handles geographic queries
- Acts as **tiebreaker** when other signals are close
- Prevents over-reliance on simple keyword matching

---

## Signal Combination Strategy

### RRF Aggregation

All 5 signals are combined using **Reciprocal Rank Fusion (RRF)**:

```python
# For each retailer r:
RRF_score(r) = Σ [weight_i / (k + rank_i(r))] for i in {1,2,3,4,5}

where:
  k = 60 (scale constant)
  rank_i(r) = rank of retailer r in signal i
  weight_i = signal weight (normalized to sum to 1.0)
```

**Full formula:**

```
RRF(r) = 0.40/(60+rank_semantic) +
         0.25/(60+rank_product) +
         0.20/(60+rank_location) +
         0.10/(60+rank_breadth) +
         0.05/(60+rank_intent)
```

### Why RRF?

1. **Handles incompatible scales:** Ranks (1,2,3...) are universal
2. **Robust to outliers:** Extreme scores don't affect ranks much
3. **Tunable:** Easy to adjust weights
4. **No normalization needed:** Ranks are inherently normalized

### Signal Independence

**Signals are computed independently**, then combined:

```python
# Each signal produces its own ranking
semantic_ranks = _compute_semantic_ranks(candidates)
product_ranks = _compute_product_ranks(candidates, query_products)
location_ranks = _compute_location_ranks(candidates, query_area)
breadth_ranks = _compute_breadth_ranks(candidates)
intent_ranks = _compute_intent_ranks(candidates, query_text)

# Combine via RRF
rrf_scores = _combine_rrf_scores(
    candidates,
    signal_ranks={
        'semantic': semantic_ranks,
        'product': product_ranks,
        'location': location_ranks,
        'breadth': breadth_ranks,
        'intent': intent_ranks
    },
    active_weights=weights
)
```

**Independence is key:** A retailer can rank poorly in one signal but still rank high overall if it excels in others.

---

## Implementation Examples

### Example 1: Balanced Query

**Query:** "air conditioner near Bedok"

**Candidate Retailers:**

| Retailer | Semantic | Product | Location | Breadth | Intent | RRF Score |
|----------|----------|---------|----------|---------|--------|-----------|
| Gain City | Rank 1 | Rank 2 | Rank 1 | Rank 1 | Rank 3 | **0.0163** |
| Courts | Rank 2 | Rank 1 | Rank 5 | Rank 2 | Rank 2 | 0.0160 |
| Harvey Norman | Rank 3 | Rank 3 | Rank 2 | Rank 3 | Rank 1 | 0.0157 |

**Winner:** Gain City (strong semantic + perfect location + high breadth)

### Example 2: Product Specialist vs Generalist

**Query:** "5-tick inverter aircon"

**Retailers:**

| Retailer | Type | Products | Semantic | Product | Location | Breadth | RRF Score |
|----------|------|----------|----------|---------|----------|---------|-----------|
| AirconPro | Specialist | 1 (AC only) | Rank 1 | Rank 1 | Rank 3 | Rank 10 | **0.0165** |
| MegaMart | Generalist | 10 (all) | Rank 5 | Rank 3 | Rank 1 | Rank 1 | 0.0152 |

**Winner:** AirconPro (perfect semantic + product match outweighs low breadth)

**Insight:** Specialist beats generalist when query is specific.

### Example 3: Location Dominates

**Query:** "appliance store in Jurong West"

**Retailers:**

| Retailer | Semantic | Product | Location | Breadth | Intent | RRF Score |
|----------|----------|---------|----------|---------|--------|-----------|
| JurongMart | Rank 5 | Rank 5 | Rank 1 | Rank 2 | Rank 5 | **0.0142** |
| CityStore | Rank 1 | Rank 1 | Rank 10 | Rank 1 | Rank 1 | 0.0135 |

**Winner:** JurongMart (perfect location compensates for weaker other signals)

**Insight:** When location is specified, proximity matters significantly (20% weight).

---

## Cross-References

- [RRF Algorithm](./rrf-algorithm.md) - Mathematical formulation and RRF details
- [Retailer Matching](./retailer-matching.md) - End-to-end matching flow
- [Performance Tuning](./performance-tuning.md) - Quick mode (2 signals only)
- [SEALION Integration](../02-core-systems/sealion-integration.md) - Semantic signal embeddings

---

[← Back to Documentation](../README.md) | [Next: Retailer Matching →](./retailer-matching.md)
