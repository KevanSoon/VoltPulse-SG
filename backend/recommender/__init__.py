"""Recommender system components."""
from .vector_store import VectorStore, SimilarityResult
from .gis_recommender import (
    GISRecommender,
    ClientProfile,
    ScoredClient,
    HousingType,
    PLANNING_AREAS,
    HOUSING_INCOME_PROXY,
    generate_mock_clients,
    generate_seed_profile,
    EmbeddingReducer,
    HybridSemanticSpatialEncoder,
)

__all__ = [
    "VectorStore",
    "SimilarityResult",
    "GISRecommender",
    "ClientProfile",
    "ScoredClient",
    "HousingType",
    "PLANNING_AREAS",
    "HOUSING_INCOME_PROXY",
    "generate_mock_clients",
    "generate_seed_profile",
    "EmbeddingReducer",
    "HybridSemanticSpatialEncoder",
]
