# Adding Custom RRF Signals

Guide for extending the RRF scorer with new ranking signals.

---

## Overview

The RRF (Reciprocal Rank Fusion) scorer currently uses **5 signals** to rank retailers:

1. **Semantic Similarity** (40%) - SEALION embedding distance
2. **Product Match** (25%) - Jaccard similarity
3. **Location Relevance** (20%) - Planning area matching
4. **Retailer Breadth** (10%) - Product diversity + website
5. **Query Intent** (5%) - Keyword-based intent detection

You can add **custom signals** to improve ranking for specific use cases.

---

## Step 1: Define Signal Method

Edit `backend/recommender/rrf_scorer.py`:

```python
class RRFScorer:
    def _score_review_quality(
        self,
        candidates: List[SimilarityResult],
        query_text: str
    ) -> List[float]:
        """Score retailers by review quality (new signal).

        Args:
            candidates: Retailer results
            query_text: User query

        Returns:
            List of scores (0.0-1.0) for each candidate
        """
        scores = []

        for candidate in candidates:
            form_data = candidate.form_data or {}

            # Extract review data
            avg_rating = form_data.get("average_rating", 0.0)  # 0-5
            review_count = form_data.get("review_count", 0)

            # Normalize rating (0-5 → 0-1)
            rating_score = avg_rating / 5.0 if avg_rating > 0 else 0.0

            # Normalize review count (log scale, 100+ reviews = 1.0)
            import math
            review_score = min(1.0, math.log(review_count + 1) / math.log(100))

            # Combine (70% rating, 30% count)
            final_score = (rating_score * 0.7) + (review_score * 0.3)
            scores.append(final_score)

        return scores
```

---

## Step 2: Add Signal to Score Method

Add your signal to the `score_retailers` method:

```python
async def score_retailers(
    self,
    candidates: List[SimilarityResult],
    query_text: str,
    quick_mode: bool = False
) -> List[ScoredRetailer]:
    """Score and rank retailers using RRF."""

    # Existing signals
    semantic_scores = self._score_semantic_similarity(candidates)
    product_scores = self._score_product_match(candidates, query_text)
    location_scores = self._score_location_relevance(candidates, query_text)
    breadth_scores = self._score_retailer_breadth(candidates)
    intent_scores = self._score_query_intent(candidates, query_text)

    # New signal
    review_scores = self._score_review_quality(candidates, query_text)

    # ... rest of RRF combination logic
```

---

## Step 3: Add Weight Configuration

Add environment variable for your signal weight:

```python
# In __init__ method
self.review_weight = float(os.getenv("RRF_REVIEW_WEIGHT", "0.05"))

# Update weight normalization
self.weights = {
    "semantic": self.semantic_weight,
    "product": self.product_weight,
    "location": self.location_weight,
    "breadth": self.breadth_weight,
    "intent": self.intent_weight,
    "review": self.review_weight,  # Add here
}

# Normalize weights to sum to 1.0
total_weight = sum(self.weights.values())
self.weights = {k: v / total_weight for k, v in self.weights.items()}
```

---

## Step 4: Include in RRF Combination

Add your signal to the RRF formula:

```python
# Create rankings for each signal
rankings = {
    "semantic": self._create_ranking(semantic_scores),
    "product": self._create_ranking(product_scores),
    "location": self._create_ranking(location_scores),
    "breadth": self._create_ranking(breadth_scores),
    "intent": self._create_ranking(intent_scores),
    "review": self._create_ranking(review_scores),  # Add here
}

# Calculate RRF scores
for idx, candidate in enumerate(candidates):
    rrf_contributions = {}

    for signal_name, ranking in rankings.items():
        rank = ranking[idx]
        weight = self.weights[signal_name]
        contribution = weight / (self.k + rank)
        rrf_contributions[signal_name] = contribution

    final_score = sum(rrf_contributions.values())
```

---

## Step 5: Update ScoredRetailer Schema

Add your signal score to the `ScoredRetailer` model:

```python
class ScoredRetailer(BaseModel):
    retailer: SimilarityResult

    # Component scores
    semantic_score: float
    product_score: float
    location_score: float
    breadth_score: float
    intent_score: float
    review_score: float  # Add here

    # Final score
    final_rrf_score: float
    rank: int
```

---

## Environment Variables

Add to `.env`:

```env
# RRF Signal Weights (must sum to ~1.0)
RRF_SEMANTIC_WEIGHT=0.35
RRF_PRODUCT_WEIGHT=0.25
RRF_LOCATION_WEIGHT=0.15
RRF_BREADTH_WEIGHT=0.10
RRF_INTENT_WEIGHT=0.10
RRF_REVIEW_WEIGHT=0.05
```

---

## Testing

```python
import pytest
from recommender.rrf_scorer import RRFScorer

@pytest.mark.asyncio
async def test_review_signal():
    """Test review quality signal."""
    scorer = RRFScorer()

    candidates = [
        create_mock_result(review_count=50, avg_rating=4.5),
        create_mock_result(review_count=5, avg_rating=3.0),
    ]

    scores = scorer._score_review_quality(candidates, "")
    assert scores[0] > scores[1]  # More reviews + higher rating
```

---

## Best Practices

1. **Normalize to 0-1**: All signals must output scores between 0.0 and 1.0
2. **Handle Missing Data**: Gracefully handle missing metadata fields
3. **Test Edge Cases**: Empty candidates, missing fields, zero values
4. **Document Clearly**: Explain signal purpose and formula in docstring
5. **Tune Weights**: Start with low weight (0.05), increase if effective

---

## Related Documentation

- [RRF Algorithm](../03-recommender-system/rrf-algorithm.md)
- [Multi-Signal Ranking](../03-recommender-system/multi-signal-ranking.md)

---

**Generated:** 2024-06-15
