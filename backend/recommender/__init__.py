"""Recommender system components."""
from .vector_store import DonorVectorStore, SimilarityResult
from .gis_recommender import (
    GISRecommender,
    ClientProfile,
    ScoredClient,
    HousingType,
    PLANNING_AREAS,
    HOUSING_INCOME_PROXY,
    generate_mock_clients,
    generate_seed_donor_profile,
    EmbeddingReducer,
    HybridSemanticSpatialEncoder,
)

__all__ = [
    "DonorVectorStore",
    "SimilarityResult",
    "GISRecommender",
    "ClientProfile",
    "ScoredClient",
    "HousingType",
    "PLANNING_AREAS",
    "HOUSING_INCOME_PROXY",
    "generate_mock_clients",
    "generate_seed_donor_profile",
    "EmbeddingReducer",
    "HybridSemanticSpatialEncoder",
]
