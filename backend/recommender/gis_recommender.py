"""
GIS-based Donor/Client Recommender System for ASEAN targeting.

This module implements:
1. Lookalike Retrieval: Find top-K nearest neighbors using cosine similarity
2. Spatial Filtering: Geo-fence filtering by Singapore planning areas
3. Tiered Targeting: Ranking based on vector similarity, spatial proxy, and donation history
4. GeoJSON Export: Output for map-based dashboard visualization
5. Dimensionality Reduction: PCA for compact semantic representation

Privacy Note:
- PII (names, exact addresses) are stored as encrypted metadata, NOT in the vector
- Coordinates are stored with reduced precision (3 decimal places ~100m accuracy)
- Only behavioral/interest data is embedded in the vector space

Dimensionality Reduction Strategy:
- Store BOTH full 1024-dim embedding AND reduced representation
- Reduced dimensions (2D/3D) enable:
  1. Better matching with small datasets (less noise)
  2. Combination with geo-coordinates for hybrid semantic-spatial search
  3. Visualization in 2D/3D space
"""

import json
import hashlib
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np


# ============================================================================
# Dimensionality Reduction Utilities
# ============================================================================


class EmbeddingReducer:
    """
    Reduces high-dimensional embeddings to lower dimensions using PCA.

    For small datasets, this helps:
    1. Remove noise from sparse dimensions
    2. Enable combination with geo-coordinates
    3. Improve similarity matching with limited data
    """

    def __init__(self, n_components: int = 8):
        """
        Initialize reducer.

        Args:
            n_components: Target dimensionality (default 8 for semantic space)
        """
        self.n_components = n_components
        self._mean = None
        self._components = None
        self._is_fitted = False

    def fit(self, embeddings: np.ndarray) -> "EmbeddingReducer":
        """
        Fit PCA on a set of embeddings.

        Args:
            embeddings: (N, D) array of embeddings

        Returns:
            self for chaining
        """
        if embeddings.shape[0] < 2:
            # Not enough data to fit PCA, use identity-like projection
            self._mean = np.zeros(embeddings.shape[1])
            # Select top dimensions with highest variance as proxy
            self._components = np.eye(embeddings.shape[1])[: self.n_components]
            self._is_fitted = True
            return self

        # Center the data
        self._mean = np.mean(embeddings, axis=0)
        centered = embeddings - self._mean

        # Simple PCA via SVD (works for small datasets)
        try:
            U, S, Vt = np.linalg.svd(centered, full_matrices=False)
            self._components = Vt[: self.n_components]
        except np.linalg.LinAlgError:
            # SVD failed, use top-variance dimensions
            variances = np.var(centered, axis=0)
            top_dims = np.argsort(variances)[-self.n_components :]
            self._components = np.eye(embeddings.shape[1])[top_dims]

        self._is_fitted = True
        return self

    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Transform embeddings to reduced dimensionality.

        Args:
            embeddings: (N, D) or (D,) array of embeddings

        Returns:
            (N, n_components) or (n_components,) reduced embeddings
        """
        if not self._is_fitted:
            # Auto-fit on this data if not fitted
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)
            self.fit(embeddings)

        single = embeddings.ndim == 1
        if single:
            embeddings = embeddings.reshape(1, -1)

        centered = embeddings - self._mean
        reduced = centered @ self._components.T

        # Normalize to unit length for cosine similarity
        norms = np.linalg.norm(reduced, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1)
        reduced = reduced / norms

        return reduced[0] if single else reduced

    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """Fit and transform in one step."""
        return self.fit(embeddings).transform(embeddings)

    @staticmethod
    def compute_sparse_projection(
        embedding: np.ndarray, n_components: int = 8
    ) -> np.ndarray:
        """
        Fast projection for sparse embeddings without fitting.

        Selects the top-k dimensions with highest absolute values.
        Good for single queries when no training data available.
        """
        # Find non-zero dimensions
        nonzero_mask = np.abs(embedding) > 1e-6
        nonzero_indices = np.where(nonzero_mask)[0]

        if len(nonzero_indices) <= n_components:
            # Few enough non-zero dims, use them directly
            result = np.zeros(n_components)
            result[: len(nonzero_indices)] = embedding[nonzero_indices]
        else:
            # Take top-k by absolute value
            top_k_in_nonzero = np.argsort(np.abs(embedding[nonzero_indices]))[
                -n_components:
            ]
            top_k_indices = nonzero_indices[top_k_in_nonzero]
            result = embedding[top_k_indices]

        # Normalize
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm

        return result


class HybridSemanticSpatialEncoder:
    """
    Combines semantic embeddings with geographic coordinates.

    Creates a hybrid vector that captures both:
    1. Semantic similarity (interests, causes)
    2. Spatial proximity (location)

    This enables "find people with similar interests NEAR this location"
    without strict geo-fencing.
    """

    def __init__(
        self,
        semantic_dims: int = 8,
        spatial_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ):
        """
        Initialize hybrid encoder.

        Args:
            semantic_dims: Reduced semantic dimensions
            spatial_weight: Weight for spatial component (0-1)
            semantic_weight: Weight for semantic component (0-1)
        """
        self.semantic_dims = semantic_dims
        self.spatial_weight = spatial_weight
        self.semantic_weight = semantic_weight
        self.reducer = EmbeddingReducer(n_components=semantic_dims)

        # Singapore bounding box for normalization
        self.lat_min, self.lat_max = 1.15, 1.47  # ~35km range
        self.lng_min, self.lng_max = 103.6, 104.1  # ~55km range

    def normalize_coordinates(self, lat: float, lng: float) -> Tuple[float, float]:
        """Normalize coordinates to [0, 1] range within Singapore."""
        norm_lat = (lat - self.lat_min) / (self.lat_max - self.lat_min)
        norm_lng = (lng - self.lng_min) / (self.lng_max - self.lng_min)
        return (np.clip(norm_lat, 0, 1), np.clip(norm_lng, 0, 1))

    def encode(
        self, embedding: np.ndarray, coordinates: Tuple[float, float]
    ) -> np.ndarray:
        """
        Create hybrid semantic-spatial vector.

        Args:
            embedding: Full semantic embedding (1024-dim)
            coordinates: (lat, lng) tuple

        Returns:
            Hybrid vector of dimension (semantic_dims + 2)
        """
        # Reduce semantic embedding
        if embedding.ndim == 1 and len(embedding) > self.semantic_dims:
            semantic = EmbeddingReducer.compute_sparse_projection(
                embedding, self.semantic_dims
            )
        else:
            semantic = embedding[: self.semantic_dims]

        # Normalize spatial
        norm_lat, norm_lng = self.normalize_coordinates(coordinates[0], coordinates[1])
        spatial = np.array([norm_lat, norm_lng])

        # Combine with weights
        weighted_semantic = semantic * self.semantic_weight
        weighted_spatial = spatial * self.spatial_weight

        return np.concatenate([weighted_semantic, weighted_spatial])

    def compute_similarity(
        self, query_hybrid: np.ndarray, candidate_hybrid: np.ndarray
    ) -> float:
        """
        Compute similarity between hybrid vectors.

        Uses cosine similarity for semantic part and
        inverse distance for spatial part.
        """
        semantic_dims = self.semantic_dims

        # Semantic similarity (cosine)
        query_semantic = query_hybrid[:semantic_dims]
        cand_semantic = candidate_hybrid[:semantic_dims]

        dot = np.dot(query_semantic, cand_semantic)
        norm_q = np.linalg.norm(query_semantic)
        norm_c = np.linalg.norm(cand_semantic)

        if norm_q > 0 and norm_c > 0:
            semantic_sim = dot / (norm_q * norm_c)
        else:
            semantic_sim = 0.0

        # Spatial similarity (inverse euclidean distance)
        query_spatial = query_hybrid[semantic_dims:]
        cand_spatial = candidate_hybrid[semantic_dims:]

        spatial_dist = np.linalg.norm(query_spatial - cand_spatial)
        spatial_sim = 1.0 / (1.0 + spatial_dist * 10)  # Scale factor

        # Combine
        return self.semantic_weight * semantic_sim + self.spatial_weight * spatial_sim


# ============================================================================
# Singapore Planning Areas & Housing Data
# ============================================================================


class HousingType(str, Enum):
    """Singapore housing types with income proxy scores."""

    HDB_1_2_ROOM = "hdb_1_2_room"
    HDB_3_ROOM = "hdb_3_room"
    HDB_4_ROOM = "hdb_4_room"
    HDB_5_ROOM = "hdb_5_room"
    HDB_EXECUTIVE = "hdb_executive"
    CONDO = "condo"
    LANDED = "landed"
    GCB = "gcb"  # Good Class Bungalow


# Housing type to income proxy score (0-1)
HOUSING_INCOME_PROXY = {
    HousingType.HDB_1_2_ROOM: 0.1,
    HousingType.HDB_3_ROOM: 0.25,
    HousingType.HDB_4_ROOM: 0.4,
    HousingType.HDB_5_ROOM: 0.55,
    HousingType.HDB_EXECUTIVE: 0.65,
    HousingType.CONDO: 0.75,
    HousingType.LANDED: 0.85,
    HousingType.GCB: 1.0,
}

# Singapore Planning Areas with approximate centroids
PLANNING_AREAS = {
    "ang_mo_kio": {"name": "Ang Mo Kio", "lat": 1.3691, "lng": 103.8454},
    "bedok": {"name": "Bedok", "lat": 1.3236, "lng": 103.9273},
    "bishan": {"name": "Bishan", "lat": 1.3526, "lng": 103.8352},
    "bukit_batok": {"name": "Bukit Batok", "lat": 1.3590, "lng": 103.7637},
    "bukit_merah": {"name": "Bukit Merah", "lat": 1.2819, "lng": 103.8239},
    "bukit_panjang": {"name": "Bukit Panjang", "lat": 1.3774, "lng": 103.7719},
    "bukit_timah": {"name": "Bukit Timah", "lat": 1.3294, "lng": 103.8021},
    "central": {"name": "Central Area", "lat": 1.2789, "lng": 103.8536},
    "choa_chu_kang": {"name": "Choa Chu Kang", "lat": 1.3840, "lng": 103.7470},
    "clementi": {"name": "Clementi", "lat": 1.3162, "lng": 103.7649},
    "geylang": {"name": "Geylang", "lat": 1.3201, "lng": 103.8918},
    "hougang": {"name": "Hougang", "lat": 1.3612, "lng": 103.8863},
    "jurong_east": {"name": "Jurong East", "lat": 1.3329, "lng": 103.7436},
    "jurong_west": {"name": "Jurong West", "lat": 1.3404, "lng": 103.7090},
    "kallang": {"name": "Kallang", "lat": 1.3100, "lng": 103.8651},
    "marine_parade": {"name": "Marine Parade", "lat": 1.3020, "lng": 103.9072},
    "novena": {"name": "Novena", "lat": 1.3204, "lng": 103.8438},
    "orchard": {"name": "Orchard", "lat": 1.3048, "lng": 103.8318},
    "pasir_ris": {"name": "Pasir Ris", "lat": 1.3721, "lng": 103.9474},
    "punggol": {"name": "Punggol", "lat": 1.3984, "lng": 103.9072},
    "queenstown": {"name": "Queenstown", "lat": 1.2942, "lng": 103.7861},
    "sembawang": {"name": "Sembawang", "lat": 1.4491, "lng": 103.8185},
    "sengkang": {"name": "Sengkang", "lat": 1.3868, "lng": 103.8914},
    "serangoon": {"name": "Serangoon", "lat": 1.3554, "lng": 103.8679},
    "tampines": {"name": "Tampines", "lat": 1.3496, "lng": 103.9568},
    "toa_payoh": {"name": "Toa Payoh", "lat": 1.3343, "lng": 103.8563},
    "woodlands": {"name": "Woodlands", "lat": 1.4382, "lng": 103.7891},
    "yishun": {"name": "Yishun", "lat": 1.4304, "lng": 103.8354},
}


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ClientProfile:
    """Client/Donor profile with spatial and behavioral data.

    Privacy considerations:
    - user_id is a hashed identifier, not PII
    - coordinates are reduced precision (~100m accuracy)
    - name_encrypted would be encrypted in production

    Embedding Strategy:
    - embedding: Full 1024-dim vector for accuracy at scale
    - embedding_reduced: 8-dim compact vector for small dataset matching
    - hybrid_embedding: Semantic + spatial combined vector
    """

    user_id: str

    # Spatial data (reduced precision for privacy)
    coordinates: Tuple[float, float]  # (lat, lng) - 3 decimal precision
    planning_area: str
    housing_type: HousingType

    # Behavioral/Interest data (embedded in vector)
    interests: List[str]
    causes: List[str]
    preferred_language: str

    # Donation history
    is_donor: bool = False
    total_donated: float = 0.0
    last_donation_amount: float = 0.0
    last_org_donated: Optional[str] = None
    donation_count: int = 0

    # Metadata (not embedded)
    name_encrypted: Optional[str] = None  # Would be encrypted in production
    age_range: Optional[str] = None  # e.g., "25-34", "35-44"

    # Vector embeddings
    embedding: Optional[List[float]] = None  # Full 1024-dim
    embedding_reduced: Optional[List[float]] = None  # Reduced 8-dim
    hybrid_embedding: Optional[List[float]] = None  # Semantic + spatial (10-dim)

    def to_embedding_text(self) -> str:
        """Convert profile to text for embedding generation."""
        parts = [
            f"Planning area: {self.planning_area}",
            f"Housing: {self.housing_type.value}",
            f"Interests: {', '.join(self.interests)}",
            f"Causes: {', '.join(self.causes)}",
            f"Language: {self.preferred_language}",
        ]
        if self.is_donor:
            parts.append(f"Donor with {self.donation_count} donations")
        return "\n".join(parts)

    def compute_reduced_embeddings(self, semantic_dims: int = 8) -> None:
        """
        Compute reduced and hybrid embeddings from full embedding.

        Call this after setting the full embedding.
        """
        if self.embedding is None:
            return

        full_emb = np.array(self.embedding)

        # Compute reduced embedding using sparse projection
        reduced = EmbeddingReducer.compute_sparse_projection(full_emb, semantic_dims)
        self.embedding_reduced = reduced.tolist()

        # Compute hybrid embedding with spatial
        encoder = HybridSemanticSpatialEncoder(semantic_dims=semantic_dims)
        hybrid = encoder.encode(full_emb, self.coordinates)
        self.hybrid_embedding = hybrid.tolist()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "coordinates": list(self.coordinates),
            "planning_area": self.planning_area,
            "housing_type": self.housing_type.value,
            "interests": self.interests,
            "causes": self.causes,
            "preferred_language": self.preferred_language,
            "is_donor": self.is_donor,
            "total_donated": self.total_donated,
            "last_donation_amount": self.last_donation_amount,
            "last_org_donated": self.last_org_donated,
            "donation_count": self.donation_count,
            "age_range": self.age_range,
            "has_reduced_embedding": self.embedding_reduced is not None,
            "has_hybrid_embedding": self.hybrid_embedding is not None,
        }


@dataclass
class ScoredClient:
    """Client with computed targeting scores."""

    client: ClientProfile

    # Individual scores (0-1)
    vector_similarity_score: float = 0.0
    spatial_proxy_score: float = 0.0
    proximity_score: float = 0.0

    # Combined score
    final_score: float = 0.0

    # Distance from query (for debugging)
    vector_distance: float = 0.0
    geo_distance_km: float = 0.0


@dataclass
class GeoJSONFeature:
    """GeoJSON Feature for map visualization."""

    type: str = "Feature"
    geometry: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# GIS Recommender System
# ============================================================================


class GISRecommender:
    """
    GIS-enhanced recommender using vector similarity + spatial targeting.

    Features:
    1. Lookalike retrieval using SEA-LION embeddings
    2. Geo-fence filtering by planning area
    3. Tiered scoring combining multiple signals
    4. GeoJSON export for visualization
    5. Hybrid semantic-spatial matching for small datasets
    """

    def __init__(self, vector_store=None, encoder=None):
        """Initialize recommender with vector store and encoder."""
        self.vector_store = vector_store
        self.encoder = encoder

        # Hybrid encoder for small dataset matching
        self.hybrid_encoder = HybridSemanticSpatialEncoder(
            semantic_dims=8, spatial_weight=0.3, semantic_weight=0.7
        )

        # Scoring weights (can be tuned)
        self.weights = {
            "vector_similarity": 0.5,
            "spatial_proxy": 0.3,
            "proximity": 0.2,
        }

        # Threshold for using hybrid matching
        self.small_dataset_threshold = 100

    @staticmethod
    def haversine_distance(
        coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> float:
        """Calculate distance between two coordinates in kilometers."""
        from math import radians, sin, cos, sqrt, atan2

        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Earth's radius in km
        return 6371 * c

    @staticmethod
    def reduce_coordinate_precision(
        lat: float, lng: float, decimals: int = 3
    ) -> Tuple[float, float]:
        """Reduce coordinate precision for privacy (~100m at 3 decimals)."""
        return (round(lat, decimals), round(lng, decimals))

    def calculate_spatial_proxy_score(self, client: ClientProfile) -> float:
        """Calculate income proxy score based on housing type."""
        return HOUSING_INCOME_PROXY.get(client.housing_type, 0.5)

    def calculate_proximity_score(
        self, client: ClientProfile, event_locations: List[Tuple[float, float]] = None
    ) -> float:
        """
        Calculate proximity score based on distance to successful donation events.

        Lower distance = higher score.
        """
        if not event_locations:
            return 0.5  # Default score if no events

        # Find minimum distance to any event
        min_distance = float("inf")
        for event_coord in event_locations:
            dist = self.haversine_distance(client.coordinates, event_coord)
            min_distance = min(min_distance, dist)

        # Convert distance to score (0-1)
        # Max distance in Singapore ~40km, normalize accordingly
        max_distance = 40.0
        score = max(0, 1 - (min_distance / max_distance))
        return score

    def calculate_vector_similarity(self, distance: float) -> float:
        """Convert L2 distance to similarity score (0-1)."""
        return 1.0 / (1.0 + distance)

    def find_lookalikes_hybrid(
        self,
        seed_profile: ClientProfile,
        candidates: List[ClientProfile],
        k: int = 50,
        planning_area_filter: Optional[str] = None,
        housing_type_filter: Optional[List[HousingType]] = None,
    ) -> List[ScoredClient]:
        """
        Find lookalikes using hybrid semantic-spatial matching.

        This method is optimized for small datasets where pure vector
        similarity may not work well due to sparse embeddings.

        Args:
            seed_profile: The "ideal donor" profile to match against
            candidates: List of candidate client profiles
            k: Number of neighbors to retrieve
            planning_area_filter: Optional geo-fence filter
            housing_type_filter: Optional housing type filter

        Returns:
            List of ScoredClient objects ranked by hybrid similarity
        """
        if not seed_profile.embedding:
            # Generate a mock embedding based on profile text
            seed_profile.embedding = self._generate_fallback_embedding(seed_profile)

        # Compute hybrid embedding for seed
        seed_emb = np.array(seed_profile.embedding)
        seed_hybrid = self.hybrid_encoder.encode(seed_emb, seed_profile.coordinates)

        scored_clients = []

        for client in candidates:
            # Apply filters
            if planning_area_filter and client.planning_area != planning_area_filter:
                continue

            if housing_type_filter:
                if client.housing_type not in housing_type_filter:
                    continue

            # Ensure client has embedding
            if not client.embedding:
                client.embedding = self._generate_fallback_embedding(client)

            # Compute hybrid embedding for candidate
            cand_emb = np.array(client.embedding)
            cand_hybrid = self.hybrid_encoder.encode(cand_emb, client.coordinates)

            # Compute hybrid similarity
            hybrid_sim = self.hybrid_encoder.compute_similarity(
                seed_hybrid, cand_hybrid
            )

            # Calculate other scores
            spatial_score = self.calculate_spatial_proxy_score(client)
            geo_dist = self.haversine_distance(
                seed_profile.coordinates, client.coordinates
            )
            proximity_score = max(0, 1 - (geo_dist / 40.0))

            # Weighted final score
            final_score = (
                0.6 * hybrid_sim  # Higher weight on hybrid similarity
                + 0.2 * spatial_score
                + 0.2 * proximity_score
            )

            scored_clients.append(
                ScoredClient(
                    client=client,
                    vector_similarity_score=hybrid_sim,
                    spatial_proxy_score=spatial_score,
                    proximity_score=proximity_score,
                    final_score=final_score,
                    vector_distance=1 - hybrid_sim,
                    geo_distance_km=geo_dist,
                )
            )

        # Sort by final score
        scored_clients.sort(key=lambda x: x.final_score, reverse=True)
        return scored_clients[:k]

    def _generate_fallback_embedding(self, profile: ClientProfile) -> List[float]:
        """
        Generate a deterministic fallback embedding when encoder is unavailable.

        Uses a hash of profile features to create a pseudo-embedding.
        This ensures consistent matching even without the actual encoder.
        """
        # Create a feature string
        features = [
            profile.planning_area,
            profile.housing_type.value,
            ",".join(sorted(profile.interests)),
            ",".join(sorted(profile.causes)),
            profile.preferred_language,
            str(profile.is_donor),
        ]
        feature_str = "|".join(features)

        # Use hash to generate pseudo-random but deterministic values
        hash_bytes = hashlib.sha256(feature_str.encode()).digest()

        # Expand hash to 1024 dimensions using multiple rounds
        embedding = []
        for i in range(64):  # 64 rounds of 16 values each = 1024
            seed = int.from_bytes(hash_bytes, "big") + i
            np.random.seed(seed % (2**32))
            chunk = np.random.randn(16) * 0.1
            embedding.extend(chunk.tolist())

        # Normalize
        emb_array = np.array(embedding[:1024])
        norm = np.linalg.norm(emb_array)
        if norm > 0:
            emb_array = emb_array / norm

        return emb_array.tolist()

    def _form_data_to_client_profile(
        self, user_id: str, form_data: Dict[str, Any], form_type: str
    ) -> ClientProfile:
        """
        Convert form data from database to ClientProfile.

        Handles both donor forms (from /donors/register) and client forms
        (from /clients/register) which have different field structures.

        Donor forms have: name, donor_type, country, preferred_language, causes,
                         donation_frequency, amount_range, bio, motivation
        Client forms have: coordinates, planning_area, housing_type, interests,
                          causes, preferred_language, is_donor, etc.

        For donors without GIS data, we infer reasonable defaults based on
        available information.
        """
        import random

        # Check if this is a donor form (different structure)
        is_donor_form = form_type == "donor" or "donor_type" in form_data

        if is_donor_form:
            # Convert donor form data to client profile
            # Infer GIS data from available information

            # Get country and infer planning area
            country = form_data.get("country", "SG")

            # Assign a random planning area (in production, could use IP geolocation)
            if country == "SG":
                planning_areas = list(PLANNING_AREAS.keys())
                # Use hash of user_id for deterministic assignment
                area_idx = hash(user_id) % len(planning_areas)
                planning_area = planning_areas[area_idx]
                area_info = PLANNING_AREAS[planning_area]
                # Add small random offset for privacy
                random.seed(hash(user_id))
                lat = area_info["lat"] + random.uniform(-0.003, 0.003)
                lng = area_info["lng"] + random.uniform(-0.003, 0.003)
                coordinates = (round(lat, 4), round(lng, 4))
            else:
                # Non-SG donors - use central SG as placeholder
                planning_area = "central"
                coordinates = (1.2897, 103.8501)

            # Infer housing type from amount_range (income proxy)
            amount_range = form_data.get("amount_range", "")
            if "5000" in amount_range or "10000" in amount_range:
                housing_type = HousingType.LANDED
            elif "2000" in amount_range or "3000" in amount_range:
                housing_type = HousingType.CONDO
            elif "1000" in amount_range:
                housing_type = HousingType.HDB_EXECUTIVE
            elif "500" in amount_range:
                housing_type = HousingType.HDB_5_ROOM
            elif "100" in amount_range or "200" in amount_range:
                housing_type = HousingType.HDB_4_ROOM
            else:
                # Default based on donor_type
                donor_type = form_data.get("donor_type", "individual")
                if donor_type == "corporate":
                    housing_type = HousingType.CONDO  # Proxy for corporate
                elif donor_type == "foundation":
                    housing_type = HousingType.LANDED  # High value
                else:
                    housing_type = HousingType.HDB_4_ROOM

            # Get causes and infer interests from bio/motivation
            causes = form_data.get("causes", [])

            # Extract interests from bio and motivation text
            bio = form_data.get("bio", "")
            motivation = form_data.get("motivation", "")
            combined_text = f"{bio} {motivation}".lower()

            interest_keywords = {
                "technology": ["tech", "software", "digital", "innovation", "startup"],
                "sustainability": [
                    "green",
                    "sustainable",
                    "climate",
                    "environment",
                    "eco",
                ],
                "finance": ["finance", "banking", "investment", "money", "economic"],
                "healthcare": ["health", "medical", "hospital", "wellness", "care"],
                "education": ["education", "school", "learning", "teach", "university"],
                "community": [
                    "community",
                    "local",
                    "neighborhood",
                    "social",
                    "volunteer",
                ],
                "arts": ["art", "culture", "music", "creative", "design"],
            }

            interests = []
            for interest, keywords in interest_keywords.items():
                if any(kw in combined_text for kw in keywords):
                    interests.append(interest)

            # Add causes as interests too (overlap is fine)
            for cause in causes:
                if cause not in interests:
                    interests.append(cause)

            return ClientProfile(
                user_id=user_id,
                coordinates=coordinates,
                planning_area=planning_area,
                housing_type=housing_type,
                interests=interests[:5],  # Limit to 5
                causes=causes,
                preferred_language=form_data.get("preferred_language", "en"),
                is_donor=True,  # Came from donor registration
                total_donated=0,  # Unknown for new donors
                donation_count=0,
                age_range=None,
            )
        else:
            # Client form - has GIS data directly
            return ClientProfile(
                user_id=user_id,
                coordinates=tuple(form_data.get("coordinates", [1.3521, 103.8198])),
                planning_area=form_data.get("planning_area", "central"),
                housing_type=HousingType(form_data.get("housing_type", "hdb_4_room")),
                interests=form_data.get("interests", []),
                causes=form_data.get("causes", []),
                preferred_language=form_data.get("preferred_language", "en"),
                is_donor=form_data.get("is_donor", False),
                total_donated=form_data.get("total_donated", 0),
                donation_count=form_data.get("donation_count", 0),
                age_range=form_data.get("age_range"),
            )

    async def find_lookalikes(
        self,
        seed_profile: ClientProfile,
        k: int = 50,
        planning_area_filter: Optional[str] = None,
        housing_type_filter: Optional[List[HousingType]] = None,
        use_hybrid: bool = False,
        fallback_candidates: Optional[List[ClientProfile]] = None,
    ) -> List[ScoredClient]:
        """
        Find top-K lookalikes for a seed donor profile.

        Args:
            seed_profile: The "ideal donor" profile to match against
            k: Number of neighbors to retrieve
            planning_area_filter: Optional geo-fence filter
            housing_type_filter: Optional housing type filter
            use_hybrid: Force hybrid matching (good for small datasets)
            fallback_candidates: Candidates to use if vector store returns nothing

        Returns:
            List of ScoredClient objects ranked by similarity
        """
        # Check if we should use hybrid matching
        if use_hybrid and fallback_candidates:
            return self.find_lookalikes_hybrid(
                seed_profile=seed_profile,
                candidates=fallback_candidates,
                k=k,
                planning_area_filter=planning_area_filter,
                housing_type_filter=housing_type_filter,
            )

        if not self.encoder or not self.vector_store:
            # No encoder/store - use hybrid with fallback candidates
            if fallback_candidates:
                return self.find_lookalikes_hybrid(
                    seed_profile=seed_profile,
                    candidates=fallback_candidates,
                    k=k,
                    planning_area_filter=planning_area_filter,
                    housing_type_filter=housing_type_filter,
                )
            raise ValueError(
                "Encoder and vector store must be initialized, or provide fallback_candidates"
            )

        # Generate embedding for seed profile
        seed_text = seed_profile.to_embedding_text()
        seed_embedding = await self.encoder.encode(seed_text)

        # Query vector store - search for BOTH donors and clients
        # Donors registered via /donors/register have form_type="donor"
        # Clients registered via /clients/register have form_type="client"
        all_results = []

        # Search for donors first (main source of potential clients for donees)
        donor_results = await self.vector_store.find_similar(
            query_embedding=seed_embedding,
            form_type="donor",
            limit=k * 2,
            country_filter="SG",
        )
        all_results.extend(donor_results)

        # Also search for clients (if any registered via client endpoint)
        client_results = await self.vector_store.find_similar(
            query_embedding=seed_embedding,
            form_type="client",
            limit=k * 2,
            country_filter="SG",
        )
        all_results.extend(client_results)

        # Deduplicate by ID and sort by distance
        seen_ids = set()
        results = []
        for r in sorted(all_results, key=lambda x: x.distance):
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                results.append(r)

        scored_clients = []
        for result in results:
            # Reconstruct client profile from form_data
            form_data = result.form_data

            # Apply planning area filter
            if planning_area_filter:
                if form_data.get("planning_area") != planning_area_filter:
                    continue

            # Apply housing type filter
            if housing_type_filter:
                client_housing = form_data.get("housing_type")
                if client_housing not in [h.value for h in housing_type_filter]:
                    continue

            # Create client profile from form_data
            # Handle both donor forms (different fields) and client forms
            client = self._form_data_to_client_profile(
                result.id, form_data, result.form_type
            )

            # Calculate scores
            vector_score = self.calculate_vector_similarity(result.distance)
            spatial_score = self.calculate_spatial_proxy_score(client)
            proximity_score = 0.5  # Default, can be enhanced with event data

            # Calculate final weighted score
            final_score = (
                self.weights["vector_similarity"] * vector_score
                + self.weights["spatial_proxy"] * spatial_score
                + self.weights["proximity"] * proximity_score
            )

            scored_clients.append(
                ScoredClient(
                    client=client,
                    vector_similarity_score=vector_score,
                    spatial_proxy_score=spatial_score,
                    proximity_score=proximity_score,
                    final_score=final_score,
                    vector_distance=result.distance,
                )
            )

        # Sort by final score and return top K
        scored_clients.sort(key=lambda x: x.final_score, reverse=True)
        return scored_clients[:k]

    def apply_tiered_targeting(
        self, clients: List[ScoredClient], min_score: float = 0.0, tiers: int = 3
    ) -> Dict[str, List[ScoredClient]]:
        """
        Apply tiered targeting to segment clients.

        Returns clients grouped into tiers:
        - Tier 1: High priority (top third)
        - Tier 2: Medium priority (middle third)
        - Tier 3: Lower priority (bottom third)
        """
        # Filter by minimum score
        filtered = [c for c in clients if c.final_score >= min_score]

        if not filtered:
            return {"tier_1": [], "tier_2": [], "tier_3": []}

        # Calculate tier boundaries
        n = len(filtered)
        tier_size = n // tiers

        return {
            "tier_1": filtered[:tier_size],
            "tier_2": filtered[tier_size : tier_size * 2],
            "tier_3": filtered[tier_size * 2 :],
        }

    def to_geojson(self, scored_clients: List[ScoredClient]) -> Dict[str, Any]:
        """
        Convert scored clients to GeoJSON for map visualization.

        Note: Coordinates are reduced precision for privacy.
        """
        features = []

        for sc in scored_clients:
            # Reduce coordinate precision for privacy
            lat, lng = self.reduce_coordinate_precision(
                sc.client.coordinates[0], sc.client.coordinates[1]
            )

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat],  # GeoJSON is [lng, lat]
                },
                "properties": {
                    "user_id": sc.client.user_id,
                    "planning_area": sc.client.planning_area,
                    "housing_type": sc.client.housing_type.value,
                    "causes": sc.client.causes,
                    "is_donor": sc.client.is_donor,
                    "final_score": round(sc.final_score, 3),
                    "vector_similarity": round(sc.vector_similarity_score, 3),
                    "spatial_proxy": round(sc.spatial_proxy_score, 3),
                    "proximity": round(sc.proximity_score, 3),
                    # Exclude PII like name, exact address
                },
            }
            features.append(feature)

        return {"type": "FeatureCollection", "features": features}


# ============================================================================
# Mock Data Generator (for demonstration)
# ============================================================================

# Singapore-style names (multi-ethnic: Chinese, Malay, Indian, Eurasian)
_FIRST_NAMES_CHINESE = [
    "Wei Ling", "Jia Hui", "Xiu Mei", "Zhi Wei", "Mei Ling", "Jun Jie",
    "Xiao Ming", "Yu Yan", "Jing Yi", "Zhi Hao", "Hui Min", "Kai Wen",
    "Shi Min", "Yi Xuan", "Jia Ying", "Wen Hui", "Li Hua", "Xin Yi",
    "Jia Min", "Zhi Xuan", "Shu Ting", "Wei Jie", "Pei Shan", "Jun Wei",
]
_SURNAMES_CHINESE = [
    "Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh",
    "Teo", "Ang", "Yeo", "Tay", "Ho", "Low", "Sim", "Chong", "Leong", "Foo",
]

_FIRST_NAMES_MALAY = [
    "Ahmad", "Muhammad", "Fatimah", "Siti", "Nur", "Aisyah", "Hafiz",
    "Amirah", "Farah", "Haziq", "Iman", "Zulkifli", "Rashid", "Nurul",
    "Hakim", "Syahira", "Irfan", "Liyana", "Danial", "Ain",
]
_SURNAMES_MALAY = [
    "bin Abdullah", "binti Ismail", "bin Rahman", "binti Hassan",
    "bin Osman", "binti Ahmad", "bin Yusof", "binti Mohamed",
    "bin Ibrahim", "binti Ali", "bin Hamid", "binti Zainal",
]

_FIRST_NAMES_INDIAN = [
    "Priya", "Raj", "Ananya", "Arjun", "Kavitha", "Suresh", "Deepa",
    "Vijay", "Lakshmi", "Rahul", "Nirmala", "Sanjay", "Meena", "Arun",
    "Revathi", "Ganesh", "Shanti", "Kumar", "Devi", "Ravi",
]
_SURNAMES_INDIAN = [
    "Krishnan", "Pillai", "Nair", "Menon", "Rajan", "Sharma", "Patel",
    "Subramaniam", "Narayanan", "Chandran", "Gopal", "Muthu", "Samy",
]

_FIRST_NAMES_EURASIAN = [
    "Daniel", "Sarah", "Michael", "Rachel", "David", "Michelle", "James",
    "Vanessa", "Mark", "Stephanie", "Paul", "Amanda", "Brian", "Nicole",
]
_SURNAMES_EURASIAN = [
    "De Souza", "Pereira", "Rodrigues", "Fernandes", "Da Costa",
    "Oliveira", "Sequeira", "D'Cruz", "Shepherdson", "Westerhout",
]


def generate_singapore_name() -> str:
    """Generate a random Singapore-style name reflecting local demographics."""
    import random

    ethnicity = random.choices(
        ["chinese", "malay", "indian", "eurasian"],
        weights=[0.74, 0.13, 0.09, 0.04]  # Approximate Singapore demographics
    )[0]

    if ethnicity == "chinese":
        return f"{random.choice(_SURNAMES_CHINESE)} {random.choice(_FIRST_NAMES_CHINESE)}"
    elif ethnicity == "malay":
        first = random.choice(_FIRST_NAMES_MALAY)
        surname = random.choice(_SURNAMES_MALAY)
        return f"{first} {surname}"
    elif ethnicity == "indian":
        return f"{random.choice(_FIRST_NAMES_INDIAN)} {random.choice(_SURNAMES_INDIAN)}"
    else:
        return f"{random.choice(_FIRST_NAMES_EURASIAN)} {random.choice(_SURNAMES_EURASIAN)}"


def generate_mock_clients(n: int = 100) -> List[ClientProfile]:
    """Generate mock client profiles for testing."""
    import random

    used_names: set[str] = set()

    def get_unique_name() -> str:
        """Generate a unique Singapore name, adding suffix if needed."""
        base_name = generate_singapore_name()
        name = base_name
        suffix = 1
        while name in used_names:
            suffix += 1
            name = f"{base_name} ({suffix})"
        used_names.add(name)
        return name

    interests_pool = [
        "technology",
        "sustainability",
        "finance",
        "healthcare",
        "education",
        "arts",
        "sports",
        "community",
        "environment",
        "innovation",
        "social_impact",
        "volunteering",
        "entrepreneurship",
        "wellness",
    ]

    causes_pool = [
        "education",
        "health",
        "environment",
        "poverty",
        "children",
        "elderly",
        "disability",
        "animals",
        "arts",
        "disaster_relief",
        "human_rights",
        "technology",
        "housing",
    ]

    languages = ["en", "zh", "ms", "ta", "th", "vi"]
    age_ranges = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    housing_types = list(HousingType)
    planning_areas = list(PLANNING_AREAS.keys())

    clients = []

    for i in range(n):
        # Select random planning area and add some noise to coordinates
        area_key = random.choice(planning_areas)
        area = PLANNING_AREAS[area_key]

        # Add small random offset (within ~500m)
        lat = area["lat"] + random.uniform(-0.005, 0.005)
        lng = area["lng"] + random.uniform(-0.005, 0.005)

        # Weighted housing type selection (more HDB in Singapore)
        housing_weights = [0.05, 0.15, 0.25, 0.2, 0.1, 0.15, 0.08, 0.02]
        housing = random.choices(housing_types, weights=housing_weights)[0]

        # Random interests and causes
        interests = random.sample(interests_pool, random.randint(2, 5))
        causes = random.sample(causes_pool, random.randint(1, 4))

        # Donor status (30% are donors)
        is_donor = random.random() < 0.3

        client = ClientProfile(
            user_id=generate_singapore_name(),
            coordinates=(round(lat, 4), round(lng, 4)),
            planning_area=area_key,
            housing_type=housing,
            interests=interests,
            causes=causes,
            preferred_language=random.choice(languages),
            is_donor=is_donor,
            total_donated=random.uniform(50, 5000) if is_donor else 0,
            donation_count=random.randint(1, 20) if is_donor else 0,
            age_range=random.choice(age_ranges),
        )

        # Generate fallback embedding and compute reduced versions
        recommender = GISRecommender()
        client.embedding = recommender._generate_fallback_embedding(client)
        client.compute_reduced_embeddings()

        clients.append(client)

    return clients


def generate_seed_donor_profile(cause: str = "education") -> ClientProfile:
    """Generate an ideal donor profile for lookalike search."""
    profile = ClientProfile(
        user_id="seed_donor",
        coordinates=(1.3048, 103.8318),  # Orchard area
        planning_area="orchard",
        housing_type=HousingType.CONDO,
        interests=["sustainability", "social_impact", "community"],
        causes=[cause, "children"],
        preferred_language="en",
        is_donor=True,
        total_donated=2500.0,
        donation_count=12,
        age_range="35-44",
    )

    # Generate fallback embedding and compute reduced versions
    recommender = GISRecommender()
    profile.embedding = recommender._generate_fallback_embedding(profile)
    profile.compute_reduced_embeddings()

    return profile
