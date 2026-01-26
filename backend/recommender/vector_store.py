"""Vector storage and retrieval for donor/volunteer embeddings.

Uses the existing my_embeddings table in Supabase with pgvector extension.
"""

import json
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
import numpy as np


def _parse_json_field(value: Union[str, dict, None]) -> dict:
    """Safely parse a JSON field that might already be a dict (psycopg3 auto-parses)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


@dataclass
class SimilarityResult:
    """Result from similarity search.

    Attributes:
        id: The source_id of the matched form.
        form_data: The original form data as a dictionary.
        score: Similarity score (higher is more similar).
        form_type: Type of form ("donor" or "volunteer").
        distance: Raw L2 distance from query.
    """
    id: str
    form_data: Dict[str, Any]
    score: float
    form_type: str
    distance: float = 0.0


class DonorVectorStore:
    """Vector storage and retrieval for donor/volunteer embeddings.

    Uses the existing my_embeddings table schema:
    - source_id: form ID
    - chunk_index: always 0 (single embedding per form)
    - text_content: JSON serialized form data
    - metadata: {"form_type": "donor"|"volunteer", ...}
    - embedding: VECTOR(1024)

    Attributes:
        pool: AsyncConnectionPool for database connections.
    """

    def __init__(self, pool):
        """Initialize vector store.

        Args:
            pool: AsyncConnectionPool from psycopg_pool
        """
        self.pool = pool

    async def store_embedding(
        self,
        form_id: str,
        form_type: str,
        embedding: np.ndarray,
        form_data: Dict[str, Any]
    ) -> int:
        """Store form embedding in my_embeddings table.

        Args:
            form_id: Unique identifier for the form.
            form_type: Type of form ("donor" or "volunteer").
            embedding: The 1024-dimensional embedding vector.
            form_data: Original form data to store.

        Returns:
            The database ID of the inserted record.
        """
        embedding_list = embedding.tolist()
        form_json = json.dumps(form_data, default=str)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO my_embeddings
                    (source_id, chunk_index, text_content, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    RETURNING id
                    """,
                    (
                        form_id,
                        0,  # Single embedding per form
                        form_json,
                        json.dumps({"form_type": form_type}),
                        embedding_list
                    )
                )
                result = await cur.fetchone()
                return result[0]

    async def update_embedding(
        self,
        form_id: str,
        embedding: np.ndarray,
        form_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing embedding.

        Args:
            form_id: The form ID to update.
            embedding: New embedding vector.
            form_data: Optional updated form data.

        Returns:
            True if update succeeded, False if record not found.
        """
        embedding_list = embedding.tolist()

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                if form_data:
                    form_json = json.dumps(form_data, default=str)
                    await cur.execute(
                        """
                        UPDATE my_embeddings
                        SET embedding = %s::vector, text_content = %s
                        WHERE source_id = %s
                        """,
                        (embedding_list, form_json, form_id)
                    )
                else:
                    await cur.execute(
                        """
                        UPDATE my_embeddings
                        SET embedding = %s::vector
                        WHERE source_id = %s
                        """,
                        (embedding_list, form_id)
                    )
                return cur.rowcount > 0

    async def delete_embedding(self, form_id: str) -> bool:
        """Delete an embedding by form ID.

        Args:
            form_id: The form ID to delete.

        Returns:
            True if deletion succeeded, False if record not found.
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM my_embeddings WHERE source_id = %s",
                    (form_id,)
                )
                return cur.rowcount > 0

    async def get_embedding(self, form_id: str) -> Optional[SimilarityResult]:
        """Get a specific embedding by form ID.

        Args:
            form_id: The form ID to retrieve.

        Returns:
            SimilarityResult if found, None otherwise.
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT source_id, text_content, metadata
                    FROM my_embeddings
                    WHERE source_id = %s
                    """,
                    (form_id,)
                )
                row = await cur.fetchone()

                if not row:
                    return None

                form_data = _parse_json_field(row[1])
                metadata = _parse_json_field(row[2])

                return SimilarityResult(
                    id=row[0],
                    form_data=form_data,
                    form_type=metadata.get("form_type", "unknown"),
                    score=1.0,
                    distance=0.0,
                )

    async def find_similar(
        self,
        query_embedding: np.ndarray,
        form_type: Optional[str] = None,
        limit: int = 10,
        country_filter: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None
    ) -> List[SimilarityResult]:
        """Find similar donors/volunteers using vector similarity.

        Uses L2 distance (Euclidean) with IVFFlat index for efficient search.

        Args:
            query_embedding: The query embedding vector.
            form_type: Optional filter for "donor" or "volunteer".
            limit: Maximum number of results to return.
            country_filter: Optional filter for country code.
            exclude_ids: Optional list of form IDs to exclude.

        Returns:
            List of SimilarityResult ordered by similarity (highest first).
        """
        embedding_list = query_embedding.tolist()

        # Build query with optional filters
        query = """
            SELECT
                source_id,
                text_content,
                metadata,
                embedding <-> %s::vector AS distance
            FROM my_embeddings
            WHERE 1=1
        """
        params: List[Any] = [embedding_list]

        if form_type:
            query += " AND metadata->>'form_type' = %s"
            params.append(form_type)

        if country_filter:
            query += " AND text_content ILIKE %s"
            params.append(f'%"country": "{country_filter}"%')

        if exclude_ids:
            placeholders = ", ".join(["%s"] * len(exclude_ids))
            query += f" AND source_id NOT IN ({placeholders})"
            params.extend(exclude_ids)

        query += " ORDER BY distance ASC LIMIT %s"
        params.append(limit)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()

        results = []
        for row in rows:
            form_data = _parse_json_field(row[1])
            metadata = _parse_json_field(row[2])
            distance = float(row[3])

            results.append(SimilarityResult(
                id=row[0],
                form_data=form_data,
                form_type=metadata.get("form_type", "unknown"),
                score=1.0 / (1.0 + distance),  # Convert distance to similarity
                distance=distance
            ))

        return results

    async def find_by_causes(
        self,
        target_causes: List[str],
        query_embedding: np.ndarray,
        limit: int = 20
    ) -> List[SimilarityResult]:
        """Hybrid search: filter by causes, rank by embedding similarity.

        Combines keyword filtering with vector similarity for better
        recommendations when specific causes are targeted.

        Args:
            target_causes: List of cause categories to match.
            query_embedding: The query embedding for ranking.
            limit: Maximum number of results to return.

        Returns:
            List of SimilarityResult matching causes, ranked by similarity.
        """
        embedding_list = query_embedding.tolist()

        # Build ILIKE clauses for cause filtering
        cause_conditions = " OR ".join([
            "text_content ILIKE %s" for _ in target_causes
        ])
        cause_params = [f"%{cause}%" for cause in target_causes]

        query = f"""
            SELECT
                source_id,
                text_content,
                metadata,
                embedding <-> %s::vector AS distance
            FROM my_embeddings
            WHERE ({cause_conditions})
            ORDER BY distance ASC
            LIMIT %s
        """

        params = [embedding_list] + cause_params + [limit]

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()

        results = []
        for row in rows:
            form_data = _parse_json_field(row[1])
            metadata = _parse_json_field(row[2])
            distance = float(row[3])

            results.append(SimilarityResult(
                id=row[0],
                form_data=form_data,
                form_type=metadata.get("form_type", "unknown"),
                score=1.0 / (1.0 + distance),
                distance=distance
            ))

        return results

    async def count_by_type(self) -> Dict[str, int]:
        """Get count of embeddings by form type.

        Returns:
            Dictionary with counts: {"donor": N, "volunteer": M, "total": N+M}
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT
                        metadata->>'form_type' as form_type,
                        COUNT(*) as count
                    FROM my_embeddings
                    GROUP BY metadata->>'form_type'
                """)
                rows = await cur.fetchall()

        counts = {"donor": 0, "volunteer": 0, "total": 0}
        for row in rows:
            form_type = row[0] or "unknown"
            count = row[1]
            if form_type in counts:
                counts[form_type] = count
            counts["total"] += count

        return counts

    async def find_by_form_type(
        self, form_type: str, limit: int = 500
    ) -> List[SimilarityResult]:
        """Get all entries of a specific form type.

        Args:
            form_type: Type of form ("donor", "volunteer", or "client").
            limit: Maximum number of results to return.

        Returns:
            List of SimilarityResult for the specified form type.
        """
        query = """
            SELECT
                source_id,
                text_content,
                metadata
            FROM my_embeddings
            WHERE metadata->>'form_type' = %s
            LIMIT %s
        """

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (form_type, limit))
                rows = await cur.fetchall()

        results = []
        for row in rows:
            form_data = _parse_json_field(row[1])
            metadata = _parse_json_field(row[2])

            results.append(
                SimilarityResult(
                    id=row[0],
                    form_data=form_data,
                    form_type=metadata.get("form_type", form_type),
                    score=1.0,
                    distance=0.0,
                )
            )

        return results
