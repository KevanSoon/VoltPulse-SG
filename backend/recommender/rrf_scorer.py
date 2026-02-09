"""Reciprocal Rank Fusion (RRF) scorer for multi-signal retailer ranking.

This module implements RRF to combine multiple ranking signals:
1. Semantic Similarity (40%) - L2 distance from vector search
2. Product Match (25%) - Jaccard similarity of products
3. Location Relevance (20%) - Planning area and postal proximity
4. Retailer Breadth (10%) - Number of products + website
5. Query Intent (5%) - Keyword-based intent detection

RRF Formula: Final Score = Σ (weight_i / (k + rank_i))
where k=60 (scale constant), rank_i is position in signal i
"""

import os
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
import numpy as np

# Import from existing modules
from recommender.vector_store import SimilarityResult


# Configuration from environment variables
RRF_K = int(os.getenv("RRF_K", "60"))
RRF_SEMANTIC_WEIGHT = float(os.getenv("RRF_SEMANTIC_WEIGHT", "0.40"))
RRF_PRODUCT_WEIGHT = float(os.getenv("RRF_PRODUCT_WEIGHT", "0.25"))
RRF_LOCATION_WEIGHT = float(os.getenv("RRF_LOCATION_WEIGHT", "0.20"))
RRF_BREADTH_WEIGHT = float(os.getenv("RRF_BREADTH_WEIGHT", "0.10"))
RRF_INTENT_WEIGHT = float(os.getenv("RRF_INTENT_WEIGHT", "0.05"))
RRF_QUICK_MODE_THRESHOLD = int(os.getenv("RRF_QUICK_MODE_THRESHOLD", "30"))

SIGNAL_WEIGHTS = {
    'semantic': RRF_SEMANTIC_WEIGHT,
    'product': RRF_PRODUCT_WEIGHT,
    'location': RRF_LOCATION_WEIGHT,
    'breadth': RRF_BREADTH_WEIGHT,
    'intent': RRF_INTENT_WEIGHT,
}

# Product keyword mappings for intent detection
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


@dataclass
class ScoredRetailer:
    """Retailer with RRF component scores and final rank."""

    retailer: SimilarityResult
    semantic_score: float      # 0-1 from L2 distance
    product_score: float       # 0-1 Jaccard similarity
    location_score: float      # 0-1 tiered match
    breadth_score: float       # 0-1 normalized
    intent_score: float        # 0-1 keyword match
    final_rrf_score: float     # Weighted RRF combination
    final_rank: int            # Position after RRF (1, 2, 3...)


class RRFScorer:
    """Reciprocal Rank Fusion scorer for multi-signal ranking."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        k: int = RRF_K
    ):
        """
        Initialize RRF scorer.

        Args:
            weights: Signal weights (semantic, product, location, breadth, intent)
            k: RRF scale constant (default 60)
        """
        self.weights = weights or SIGNAL_WEIGHTS.copy()
        self.k = k

        # Normalize weights to sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {
                signal: weight / total_weight
                for signal, weight in self.weights.items()
            }

    async def score_retailers(
        self,
        query_embedding: Optional[np.ndarray],
        query_text: str,
        candidates: List[SimilarityResult],
        query_product: Optional[str] = None,
        query_area: Optional[str] = None,
        limit: int = 10,
        quick_mode: Optional[bool] = None,
    ) -> List[ScoredRetailer]:
        """
        Apply RRF scoring to rank candidates.

        Args:
            query_embedding: Query vector for semantic matching (can be None)
            query_text: Raw query text for intent detection
            candidates: Vector search results
            query_product: User-specified product filter
            query_area: User-specified planning area filter
            limit: Top-K results to return
            quick_mode: Use fast path (semantic + product only), auto if >30 candidates

        Returns:
            List of ScoredRetailer sorted by RRF score
        """
        if not candidates:
            return []

        # Auto-enable quick mode for large candidate sets
        if quick_mode is None:
            quick_mode = len(candidates) > RRF_QUICK_MODE_THRESHOLD

        # Determine which signals to compute
        active_weights = self._get_active_weights(quick_mode, query_embedding)

        # Compute rank dictionaries for each active signal
        signal_ranks = {}

        if active_weights.get('semantic', 0) > 0 and query_embedding is not None:
            signal_ranks['semantic'] = self._compute_semantic_ranks(candidates)

        if active_weights.get('product', 0) > 0:
            query_products = {query_product} if query_product else set()
            signal_ranks['product'] = self._compute_product_ranks(candidates, query_products)

        if active_weights.get('location', 0) > 0:
            signal_ranks['location'] = self._compute_location_ranks(candidates, query_area)

        if active_weights.get('breadth', 0) > 0:
            signal_ranks['breadth'] = self._compute_breadth_ranks(candidates)

        if active_weights.get('intent', 0) > 0:
            signal_ranks['intent'] = self._compute_intent_ranks(candidates, query_text)

        # Compute RRF scores
        rrf_scores = self._combine_rrf_scores(
            candidates,
            signal_ranks,
            active_weights
        )

        # Sort by RRF score (descending)
        sorted_pairs = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Create ScoredRetailer objects
        scored_retailers = []
        for final_rank, (cand_id, rrf_score) in enumerate(sorted_pairs[:limit], 1):
            # Find original candidate
            original = next(c for c in candidates if c.id == cand_id)

            # Extract component scores
            semantic_score = 1.0 / (1.0 + original.distance) if hasattr(original, 'distance') else original.score
            product_score = self._get_score_from_rank(signal_ranks.get('product', {}), cand_id, len(candidates))
            location_score = self._get_score_from_rank(signal_ranks.get('location', {}), cand_id, len(candidates))
            breadth_score = self._get_score_from_rank(signal_ranks.get('breadth', {}), cand_id, len(candidates))
            intent_score = self._get_score_from_rank(signal_ranks.get('intent', {}), cand_id, len(candidates))

            scored_retailers.append(
                ScoredRetailer(
                    retailer=original,
                    semantic_score=semantic_score,
                    product_score=product_score,
                    location_score=location_score,
                    breadth_score=breadth_score,
                    intent_score=intent_score,
                    final_rrf_score=rrf_score,
                    final_rank=final_rank
                )
            )

        return scored_retailers

    def _get_active_weights(
        self,
        quick_mode: bool,
        query_embedding: Optional[np.ndarray]
    ) -> Dict[str, float]:
        """Determine which signals to use based on mode and availability."""
        if quick_mode:
            # Quick mode: semantic + product only
            total = self.weights['semantic'] + self.weights['product']
            return {
                'semantic': self.weights['semantic'] / total if query_embedding is not None else 0.0,
                'product': self.weights['product'] / total,
                'location': 0.0,
                'breadth': 0.0,
                'intent': 0.0,
            }

        # Full mode: all signals (if embedding available)
        if query_embedding is None:
            # No embedding: skip semantic, redistribute weight
            total = sum(w for s, w in self.weights.items() if s != 'semantic')
            return {
                'semantic': 0.0,
                'product': self.weights['product'] / total,
                'location': self.weights['location'] / total,
                'breadth': self.weights['breadth'] / total,
                'intent': self.weights['intent'] / total,
            }

        return self.weights.copy()

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
                # Tier 2: Postal district match (approximation)
                elif postal_prefix and query_area_lower.isdigit() and len(query_area_lower) >= 2:
                    # If query looks like postal code, match prefix
                    if postal_prefix == query_area_lower[:2]:
                        scores[candidate.id] = 0.7
                    else:
                        scores[candidate.id] = 0.0
                else:
                    scores[candidate.id] = 0.0

        return self._scores_to_ranks(scores)

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

    def _compute_intent_ranks(
        self,
        candidates: List[SimilarityResult],
        query_text: str
    ) -> Dict[str, int]:
        """Rank by query intent alignment (product vs location emphasis)."""
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
                # All equal (location handled by location signal)
                scores[candidate.id] = 0.5
            else:
                # Mixed: average
                scores[candidate.id] = 0.5

        return self._scores_to_ranks(scores)

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
                rank = rank_dict.get(cand_id, len(candidates) + 1)  # Default to last rank

                # RRF formula: weight / (k + rank)
                contribution = weight / (self.k + rank)
                rrf_score += contribution

            rrf_scores[cand_id] = rrf_score

        return rrf_scores

    def _get_score_from_rank(
        self,
        rank_dict: Dict[str, int],
        cand_id: str,
        total_candidates: int
    ) -> float:
        """Convert rank back to normalized score for display (1.0 = best)."""
        if not rank_dict or cand_id not in rank_dict:
            return 0.5  # Default middle score

        rank = rank_dict[cand_id]
        # Convert rank to 0-1 score (rank 1 = 1.0, last rank = 0.0)
        score = 1.0 - ((rank - 1) / total_candidates) if total_candidates > 0 else 0.5
        return max(0.0, min(1.0, score))
