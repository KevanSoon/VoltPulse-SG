"""Agentic RAG tools for autonomous vector store exploration.

This module provides tools that allow an agent to autonomously:
1. Search semantically across the vector store
2. Filter by metadata fields
3. Retrieve specific documents
4. List available categories
5. Perform hybrid search with filters

The agent uses a ReAct loop to iteratively explore and refine its search.
"""

import json
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from functools import wraps

# Global references to be set at initialization
_encoder = None
_vector_store = None


def set_rag_dependencies(encoder, vector_store):
    """Set the encoder and vector store instances for RAG tools.
    
    Args:
        encoder: The SeaLion encoder instance
        vector_store: The DonorVectorStore instance
    """
    global _encoder, _vector_store
    _encoder = encoder
    _vector_store = vector_store


def _format_results(results: List[Any], include_details: bool = True) -> str:
    """Format search results for agent consumption.
    
    Args:
        results: List of SimilarityResult objects
        include_details: Whether to include full form data
        
    Returns:
        Formatted string representation of results
    """
    if not results:
        return "No results found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        entry = {
            "rank": i,
            "id": result.id,
            "form_type": result.form_type,
            "similarity_score": round(result.score, 4),
        }
        
        if include_details and result.form_data:
            # Extract key fields for readability
            form_data = result.form_data
            entry["name"] = form_data.get("name", "Unknown")
            entry["country"] = form_data.get("country", "Unknown")
            entry["causes"] = form_data.get("causes", [])
            
            # Include type-specific fields
            if result.form_type == "donor":
                entry["donor_type"] = form_data.get("donor_type", "Unknown")
                entry["donation_frequency"] = form_data.get("donation_frequency")
            elif result.form_type == "volunteer":
                entry["volunteer_type"] = form_data.get("volunteer_type", "Unknown")
                entry["skills"] = form_data.get("skills", [])
                entry["availability"] = form_data.get("availability")
        
        formatted.append(entry)
    
    return json.dumps(formatted, indent=2, default=str)


@tool
async def semantic_search(query: str, limit: int = 5, form_type: Optional[str] = None) -> str:
    """Search documents by semantic similarity.

    Use this to find donors/volunteers whose profiles match a natural language query.
    The search uses vector embeddings to find semantically similar entries.

    Args:
        query: Natural language description of what you're looking for.
               Examples: "corporate donors interested in education",
                        "volunteers with tech skills in Singapore"
        limit: Maximum number of results to return (default: 5, max: 20)
        form_type: Optional filter - "donor" or "volunteer"

    Returns:
        JSON formatted list of matching profiles with similarity scores
    """
    print(f"[Agentic RAG] semantic_search called - query: '{query}', limit: {limit}, form_type: {form_type}")
    if _encoder is None or _vector_store is None:
        return "Error: RAG tools not initialized. Call set_rag_dependencies first."
    
    try:
        # Encode the query
        embedding = await _encoder.encode(query)
        
        # Search the vector store
        results = await _vector_store.find_similar(
            query_embedding=embedding,
            form_type=form_type,
            limit=min(limit, 20)
        )
        
        return _format_results(results)
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
async def filter_by_metadata(
    field: str,
    value: str,
    limit: int = 10
) -> str:
    """Browse documents filtered by metadata field.

    Use this to find all entries matching a specific metadata value.
    Useful for exploring what's available before doing semantic search.

    Args:
        field: The metadata field to filter on.
               Valid fields: "form_type", "donor_type", "volunteer_type",
                           "country", "availability"
        value: The value to match.
               Examples: form_type="donor", country="SG", donor_type="corporate"
        limit: Maximum number of results (default: 10)

    Returns:
        JSON formatted list of matching entries
    """
    print(f"[Agentic RAG] filter_by_metadata called - field: '{field}', value: '{value}', limit: {limit}")
    if _vector_store is None:
        return "Error: RAG tools not initialized."
    
    try:
        # Map field to actual database query approach
        if field == "form_type":
            results = await _vector_store.find_by_form_type(value, limit=limit)
        else:
            # For other fields, we need to search through text_content
            # Use a raw query approach
            async with _vector_store.pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Build ILIKE pattern for JSON field search
                    pattern = f'%"{field}": "{value}"%'
                    
                    await cur.execute(
                        """
                        SELECT source_id, text_content, metadata
                        FROM my_embeddings
                        WHERE text_content ILIKE %s
                        LIMIT %s
                        """,
                        (pattern, limit)
                    )
                    rows = await cur.fetchall()
            
            # Convert to SimilarityResult-like format
            from recommender.vector_store import SimilarityResult, _parse_json_field
            results = []
            for row in rows:
                form_data = _parse_json_field(row[1])
                metadata = _parse_json_field(row[2])
                results.append(SimilarityResult(
                    id=row[0],
                    form_data=form_data,
                    form_type=metadata.get("form_type", "unknown"),
                    score=1.0,
                    distance=0.0
                ))
        
        return _format_results(results)
    except Exception as e:
        return f"Filter error: {str(e)}"


@tool
async def get_document_by_id(doc_id: str) -> str:
    """Retrieve a specific document by ID for deeper inspection.

    Use this when you've identified a promising result from search
    and want to see the complete profile details.

    Args:
        doc_id: The unique document/form ID (e.g., "donor_12345")

    Returns:
        Complete JSON representation of the document
    """
    print(f"[Agentic RAG] get_document_by_id called - doc_id: '{doc_id}'")
    if _vector_store is None:
        return "Error: RAG tools not initialized."
    
    try:
        result = await _vector_store.get_embedding(doc_id)
        
        if result is None:
            return f"Document with ID '{doc_id}' not found."
        
        # Return full document details
        document = {
            "id": result.id,
            "form_type": result.form_type,
            "data": result.form_data
        }
        
        return json.dumps(document, indent=2, default=str)
    except Exception as e:
        return f"Retrieval error: {str(e)}"


@tool
async def list_available_categories() -> str:
    """List all unique values for filterable fields.

    Use this first to understand what categories exist in the database
    before performing filtered searches. Returns available:
    - Form types (donor, volunteer)
    - Countries (ASEAN country codes)
    - Causes (education, health, etc.)
    - Donor types (individual, corporate, foundation)
    - Volunteer types (regular, event_based, skilled)

    Returns:
        JSON object with distinct values for each category
    """
    print("[Agentic RAG] list_available_categories called")
    if _vector_store is None:
        return "Error: RAG tools not initialized."
    
    try:
        async with _vector_store.pool.connection() as conn:
            async with conn.cursor() as cur:
                # Get form type counts
                await cur.execute("""
                    SELECT 
                        metadata->>'form_type' as form_type,
                        COUNT(*) as count
                    FROM my_embeddings
                    GROUP BY metadata->>'form_type'
                """)
                form_types = {row[0]: row[1] for row in await cur.fetchall()}
                
                # Get distinct countries
                await cur.execute("""
                    SELECT DISTINCT text_content::json->>'country' as country
                    FROM my_embeddings
                    WHERE text_content::json->>'country' IS NOT NULL
                """)
                countries = [row[0] for row in await cur.fetchall() if row[0]]
                
                # Get distinct donor types
                await cur.execute("""
                    SELECT DISTINCT text_content::json->>'donor_type' as dtype
                    FROM my_embeddings
                    WHERE text_content::json->>'donor_type' IS NOT NULL
                """)
                donor_types = [row[0] for row in await cur.fetchall() if row[0]]
                
                # Get distinct volunteer types
                await cur.execute("""
                    SELECT DISTINCT text_content::json->>'volunteer_type' as vtype
                    FROM my_embeddings
                    WHERE text_content::json->>'volunteer_type' IS NOT NULL
                """)
                volunteer_types = [row[0] for row in await cur.fetchall() if row[0]]
                
                # Get all causes (need to aggregate from arrays)
                await cur.execute("""
                    SELECT text_content
                    FROM my_embeddings
                    WHERE text_content LIKE '%causes%'
                    LIMIT 100
                """)
                rows = await cur.fetchall()
                
                all_causes = set()
                for row in rows:
                    try:
                        if isinstance(row[0], str):
                            data = json.loads(row[0])
                        else:
                            data = row[0]
                        causes = data.get("causes", [])
                        if isinstance(causes, list):
                            all_causes.update(causes)
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        categories = {
            "form_types": form_types,
            "countries": sorted(countries),
            "donor_types": sorted(donor_types),
            "volunteer_types": sorted(volunteer_types),
            "causes": sorted(all_causes),
            "total_records": sum(form_types.values()) if form_types else 0
        }
        
        return json.dumps(categories, indent=2)
    except Exception as e:
        return f"Error listing categories: {str(e)}"


@tool
async def hybrid_search(
    query: str,
    country: Optional[str] = None,
    form_type: Optional[str] = None,
    causes: Optional[List[str]] = None,
    limit: int = 10
) -> str:
    """Combine semantic search with metadata filters.

    Use this for targeted searches that combine meaning (semantic)
    with specific constraints (filters). More precise than pure
    semantic search when you know specific criteria.

    Args:
        query: Natural language query for semantic matching
        country: Optional country code filter (e.g., "SG", "MY", "TH")
        form_type: Optional form type filter ("donor" or "volunteer")
        causes: Optional list of cause categories to match
        limit: Maximum number of results (default: 10)

    Returns:
        JSON formatted list of results matching both semantic query and filters
    """
    print(f"[Agentic RAG] hybrid_search called - query: '{query}', country: {country}, form_type: {form_type}, causes: {causes}, limit: {limit}")
    if _encoder is None or _vector_store is None:
        return "Error: RAG tools not initialized."
    
    try:
        # Encode the query
        embedding = await _encoder.encode(query)
        
        # Use cause-based hybrid search if causes specified
        if causes and len(causes) > 0:
            results = await _vector_store.find_by_causes(
                target_causes=causes,
                query_embedding=embedding,
                limit=limit
            )
            
            # Apply additional filters if needed
            if form_type or country:
                filtered = []
                for r in results:
                    if form_type and r.form_type != form_type:
                        continue
                    if country and r.form_data.get("country") != country:
                        continue
                    filtered.append(r)
                results = filtered[:limit]
        else:
            # Standard similarity search with filters
            results = await _vector_store.find_similar(
                query_embedding=embedding,
                form_type=form_type,
                limit=limit,
                country_filter=country
            )
        
        return _format_results(results)
    except Exception as e:
        return f"Hybrid search error: {str(e)}"


@tool
async def get_statistics() -> str:
    """Get overall statistics about the vector store.

    Use this to understand the size and composition of the database
    before starting your search.

    Returns:
        JSON with counts by form type and other aggregate stats
    """
    print("[Agentic RAG] get_statistics called")
    if _vector_store is None:
        return "Error: RAG tools not initialized."
    
    try:
        counts = await _vector_store.count_by_type()
        return json.dumps({
            "database_statistics": counts,
            "description": "Number of entries by form type in the vector store"
        }, indent=2)
    except Exception as e:
        return f"Error getting statistics: {str(e)}"


# Export all RAG tools as a list for easy registration
RAG_TOOLS = [
    semantic_search,
    filter_by_metadata,
    get_document_by_id,
    list_available_categories,
    hybrid_search,
    get_statistics,
]
