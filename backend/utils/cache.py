"""Query caching utilities for retailer recommendation system.

Provides LRU cache with TTL for:
1. Query results (full retailer search results)
2. Embeddings (encoded query vectors)

This significantly reduces latency by avoiding re-encoding common queries
and re-searching the database for repeated searches.
"""

import time
import os
import hashlib
from typing import Any, Optional, Dict, Tuple, Callable
from collections import OrderedDict


# Configuration from environment
QUERY_CACHE_SIZE = int(os.getenv("QUERY_CACHE_SIZE", "1000"))
QUERY_CACHE_TTL = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "3600"))  # 1 hour
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "2000"))
EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "86400"))  # 24 hours


class LRUCache:
    """
    LRU (Least Recently Used) cache with TTL (Time To Live).

    Features:
    - Auto-eviction of oldest items when size limit reached
    - TTL-based expiration for stale entries
    - Thread-safe operations (for async usage)
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time to live for cached items in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            self.misses += 1
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            # Remove expired entry
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Store item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove if already exists (to update timestamp)
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = (value, time.time())

        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            # Remove oldest (first) item
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds
        }


class QueryCache:
    """
    Cache for retailer search query results.

    Caches the full JSON response for a given query combination.
    """

    def __init__(self, max_size: int = QUERY_CACHE_SIZE, ttl_seconds: int = QUERY_CACHE_TTL):
        """Initialize query cache."""
        self.cache = LRUCache(max_size=max_size, ttl_seconds=ttl_seconds)

    def key(
        self,
        query: str,
        product: Optional[str] = None,
        area: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Generate cache key for query parameters.

        Args:
            query: Search query text
            product: Product category filter
            area: Planning area filter
            limit: Result limit

        Returns:
            Cache key string
        """
        # Normalize for better cache hits
        query_norm = query.lower().strip()
        product_norm = product.lower() if product else ""
        area_norm = area.lower() if area else ""

        # Create composite key
        key_str = f"{query_norm}|{product_norm}|{area_norm}|{limit}"

        # Hash for consistent key length
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"query:{key_hash}"

    async def get_or_compute(
        self,
        query: str,
        product: Optional[str],
        area: Optional[str],
        limit: int,
        compute_fn: Callable
    ) -> Any:
        """
        Get cached result or compute and cache it.

        Args:
            query: Search query
            product: Product filter
            area: Area filter
            limit: Result limit
            compute_fn: Async function to compute result if not cached

        Returns:
            Cached or computed result
        """
        cache_key = self.key(query, product, area, limit)

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Compute result
        result = await compute_fn()

        # Cache result
        self.cache.set(cache_key, result)

        return result

    def invalidate(self) -> None:
        """Invalidate all cached queries."""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats()


class EmbeddingCache:
    """
    Cache for SeaLion embeddings.

    Since encoding is deterministic, we can cache embeddings for 24 hours
    to avoid expensive API calls for repeated queries.
    """

    def __init__(
        self,
        max_size: int = EMBEDDING_CACHE_SIZE,
        ttl_seconds: int = EMBEDDING_CACHE_TTL
    ):
        """Initialize embedding cache."""
        self.cache = LRUCache(max_size=max_size, ttl_seconds=ttl_seconds)

    def key(self, text: str) -> str:
        """
        Generate cache key for text.

        Args:
            text: Text to encode

        Returns:
            Cache key
        """
        # Normalize text
        text_norm = text.strip()

        # Hash for consistent key
        text_hash = hashlib.md5(text_norm.encode()).hexdigest()
        return f"emb:{text_hash}"

    async def get_or_encode(
        self,
        text: str,
        encode_fn: Callable
    ) -> Any:
        """
        Get cached embedding or encode and cache it.

        Args:
            text: Text to encode
            encode_fn: Async function to encode text

        Returns:
            Cached or computed embedding
        """
        cache_key = self.key(text)

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Encode
        embedding = await encode_fn(text)

        # Cache
        self.cache.set(cache_key, embedding)

        return embedding

    def invalidate(self) -> None:
        """Invalidate all cached embeddings."""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats()


# Global cache instances
_query_cache: Optional[QueryCache] = None
_embedding_cache: Optional[EmbeddingCache] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance (singleton)."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance (singleton)."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "query_cache": get_query_cache().stats(),
        "embedding_cache": get_embedding_cache().stats()
    }
