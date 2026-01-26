"""Agentic RAG tools for autonomous vector store exploration.

This module provides tools that allow an agent to autonomously:
1. Search semantically across the vector store
2. Filter by metadata fields
3. Retrieve specific documents
4. List available categories
5. Perform hybrid search with filters
6. Extract consumption data from utility bills (on-demand)
7. Search and compare utility bills

The agent uses a ReAct loop to iteratively explore and refine its search.
"""

import json
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from functools import wraps

# Global references to be set at initialization
_encoder = None
_vector_store = None
_llm = None
_consumption_extractor = None


def set_rag_dependencies(encoder, vector_store, llm=None):
    """Set the encoder and vector store instances for RAG tools.

    Args:
        encoder: The SeaLion encoder instance
        vector_store: The VectorStore instance
        llm: Optional LLM instance for consumption extraction
    """
    global _encoder, _vector_store, _llm, _consumption_extractor
    _encoder = encoder
    _vector_store = vector_store
    _llm = llm

    # Initialize consumption extractor if LLM is provided
    if llm:
        from services.consumption_extractor import ConsumptionExtractor
        _consumption_extractor = ConsumptionExtractor(llm)


def _format_results(results: List[Any], include_details: bool = True) -> str:
    """Format search results for agent consumption.
    
    Args:
        results: List of SimilarityResult objects
        include_details: Whether to include full data
        
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
            
            # Include type-specific fields for consumption data
            if result.form_type == "ocr":
                entry["original_filename"] = form_data.get("original_filename", "Unknown")
                entry["text_count"] = form_data.get("text_count", 0)
            elif result.form_type == "consumption":
                entry["consumption_kwh"] = form_data.get("consumption_kwh")
                entry["total_amount"] = form_data.get("total_amount")
        
        formatted.append(entry)
    
    return json.dumps(formatted, indent=2, default=str)


@tool
async def semantic_search(query: str, limit: int = 5, form_type: Optional[str] = None) -> str:
    """Search documents by semantic similarity.

    Use this to find documents whose content matches a natural language query.
    The search uses vector embeddings to find semantically similar entries.

    Args:
        query: Natural language description of what you're looking for.
               Examples: "electricity bills from January",
                        "high consumption months"
        limit: Maximum number of results to return (default: 5, max: 20)
        form_type: Optional filter - "ocr", "consumption", or "client"

    Returns:
        JSON formatted list of matching documents with similarity scores
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
               Valid fields: "form_type", "country", "provider_name"
        value: The value to match.
               Examples: form_type="ocr", country="SG"
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
        doc_id: The unique document ID (e.g., "ocr_12345")

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
    - Form types (ocr, consumption, client)
    - Countries (ASEAN country codes)
    - Providers (electricity retailers)

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
                
                # Get distinct provider names (for electricity bills)
                await cur.execute("""
                    SELECT DISTINCT text_content::json->>'provider_name' as provider
                    FROM my_embeddings
                    WHERE text_content::json->>'provider_name' IS NOT NULL
                """)
                providers = [row[0] for row in await cur.fetchall() if row[0]]
                
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
            "providers": sorted(providers),
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
        form_type: Optional form type filter ("ocr", "consumption", or "client")
        causes: Optional list of categories to match
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


# =============================================================================
# CONSUMPTION DATA TOOLS - For Singapore electricity bill extraction
# =============================================================================

@tool
async def extract_consumption_data(source_id: str) -> str:
    """Extract structured consumption data from a utility bill stored in the vector store.

    Use this to get detailed electricity usage information from a bill that was
    previously uploaded via OCR. Extracts kWh consumption, costs, billing period,
    tariff breakdown, and provider information.

    This tool is specifically designed for Singapore electricity bills from
    providers like SP Services, Geneco, Keppel, Senoko, Tuas Power, etc.

    Args:
        source_id: The unique ID of the OCR document (e.g., "ocr_abc123")

    Returns:
        JSON with structured consumption data including:
        - consumption_kwh: Total electricity consumed
        - total_amount: Bill amount in SGD
        - billing_period_start/end: Billing dates
        - provider_name: Electricity retailer
        - tariff_tiers: Breakdown by usage tier
        - extraction_confidence: Quality score (0-1)
    """
    print(f"[Consumption] extract_consumption_data called - source_id: '{source_id}'")

    if _vector_store is None:
        return "Error: Vector store not initialized."
    if _consumption_extractor is None:
        return "Error: Consumption extractor not initialized. LLM required."

    try:
        # Retrieve the OCR document
        result = await _vector_store.get_embedding(source_id)

        if result is None:
            return f"Document with ID '{source_id}' not found."

        # Check if it's an OCR document
        form_data = result.form_data
        if form_data.get("source_type") != "ocr":
            return f"Document '{source_id}' is not an OCR result (type: {result.form_type})"

        # Get the combined OCR text
        ocr_text = form_data.get("combined_text", "")
        if not ocr_text:
            return f"No OCR text found in document '{source_id}'"

        # Extract consumption data using LLM
        extraction = await _consumption_extractor.extract_with_retry(ocr_text)

        # Format result
        extraction_dict = extraction.model_dump(exclude={"raw_ocr_text"})
        extraction_dict["source_id"] = source_id
        extraction_dict["original_filename"] = form_data.get("original_filename", "unknown")

        return json.dumps(extraction_dict, indent=2, default=str)

    except Exception as e:
        return f"Extraction error: {str(e)}"


@tool
async def search_utility_bills(query: str, limit: int = 10) -> str:
    """Search stored utility bills by semantic query.

    Use this to find electricity bills matching a natural language description.
    For example: "latest bill", "highest consumption", "bills from January".

    This searches OCR documents in the vector store and returns matching bills
    with basic metadata. Use extract_consumption_data to get full details.

    Args:
        query: Natural language search query
               Examples: "recent electricity bills", "high consumption months",
                        "bills from SP Services"
        limit: Maximum number of results (default: 10)

    Returns:
        JSON list of matching utility bills with:
        - source_id: Document ID for use with extract_consumption_data
        - original_filename: Uploaded file name
        - text_preview: First 200 chars of OCR text
        - similarity_score: Relevance to query
    """
    print(f"[Consumption] search_utility_bills called - query: '{query}', limit: {limit}")

    if _encoder is None or _vector_store is None:
        return "Error: RAG tools not initialized."

    try:
        # Encode the query
        embedding = await _encoder.encode(query)

        # Search for OCR documents specifically
        results = await _vector_store.find_similar(
            query_embedding=embedding,
            form_type="ocr",
            limit=min(limit, 20)
        )

        if not results:
            return "No utility bills found matching the query."

        # Format results with OCR-specific fields
        formatted = []
        for i, result in enumerate(results, 1):
            form_data = result.form_data or {}
            combined_text = form_data.get("combined_text", "")

            entry = {
                "rank": i,
                "source_id": result.id,
                "original_filename": form_data.get("original_filename", "unknown"),
                "text_preview": combined_text[:200] + "..." if len(combined_text) > 200 else combined_text,
                "text_count": form_data.get("text_count", 0),
                "similarity_score": round(result.score, 4),
            }
            formatted.append(entry)

        return json.dumps(formatted, indent=2, default=str)

    except Exception as e:
        return f"Search error: {str(e)}"


@tool
async def compare_consumption(source_ids: List[str]) -> str:
    """Compare electricity consumption across multiple bills.

    Use this to analyze consumption trends, compare costs between periods,
    or identify usage patterns across multiple bills.

    Extracts data from each bill and provides a comparison summary including:
    - Total kWh and cost per bill
    - Month-over-month changes
    - Average daily consumption
    - Cost per kWh

    Args:
        source_ids: List of OCR document IDs to compare
                   Example: ["ocr_abc123", "ocr_def456"]

    Returns:
        JSON comparison with:
        - bills: Array of extracted data per bill
        - comparison: Aggregated statistics and trends
    """
    print(f"[Consumption] compare_consumption called - source_ids: {source_ids}")

    if _vector_store is None:
        return "Error: Vector store not initialized."
    if _consumption_extractor is None:
        return "Error: Consumption extractor not initialized. LLM required."

    if not source_ids or len(source_ids) < 2:
        return "Error: Please provide at least 2 source IDs to compare."

    try:
        bills = []
        extraction_errors = []

        for source_id in source_ids:
            # Retrieve and extract each bill
            result = await _vector_store.get_embedding(source_id)

            if result is None:
                extraction_errors.append(f"Document '{source_id}' not found")
                continue

            form_data = result.form_data or {}
            ocr_text = form_data.get("combined_text", "")

            if not ocr_text:
                extraction_errors.append(f"No OCR text in '{source_id}'")
                continue

            # Extract consumption data
            extraction = await _consumption_extractor.extract_with_retry(ocr_text)

            bills.append({
                "source_id": source_id,
                "original_filename": form_data.get("original_filename", "unknown"),
                "billing_period_start": str(extraction.billing_period_start) if extraction.billing_period_start else None,
                "billing_period_end": str(extraction.billing_period_end) if extraction.billing_period_end else None,
                "consumption_kwh": extraction.consumption_kwh,
                "total_amount": extraction.total_amount,
                "daily_average_kwh": extraction.daily_average_kwh,
                "provider_name": extraction.provider_name,
                "extraction_confidence": extraction.extraction_confidence,
            })

        if len(bills) < 2:
            return json.dumps({
                "error": "Could not extract data from enough bills for comparison",
                "extraction_errors": extraction_errors,
                "bills_extracted": len(bills)
            }, indent=2)

        # Calculate comparison statistics
        total_kwh = sum(b["consumption_kwh"] or 0 for b in bills)
        total_cost = sum(b["total_amount"] or 0 for b in bills)
        avg_kwh = total_kwh / len(bills) if bills else 0
        avg_cost = total_cost / len(bills) if bills else 0

        # Calculate cost per kWh for each bill
        for bill in bills:
            if bill["consumption_kwh"] and bill["total_amount"]:
                bill["cost_per_kwh"] = round(bill["total_amount"] / bill["consumption_kwh"], 4)
            else:
                bill["cost_per_kwh"] = None

        # Sort by billing period if available
        bills_with_dates = [b for b in bills if b["billing_period_end"]]
        bills_with_dates.sort(key=lambda x: x["billing_period_end"])

        comparison = {
            "bills": bills_with_dates if bills_with_dates else bills,
            "summary": {
                "total_bills_compared": len(bills),
                "total_consumption_kwh": round(total_kwh, 2),
                "total_cost_sgd": round(total_cost, 2),
                "average_consumption_kwh": round(avg_kwh, 2),
                "average_cost_sgd": round(avg_cost, 2),
            },
            "extraction_errors": extraction_errors if extraction_errors else None,
        }

        # Add trend if we have dates
        if len(bills_with_dates) >= 2:
            first = bills_with_dates[0]
            last = bills_with_dates[-1]
            if first["consumption_kwh"] and last["consumption_kwh"]:
                kwh_change = last["consumption_kwh"] - first["consumption_kwh"]
                kwh_pct = (kwh_change / first["consumption_kwh"]) * 100 if first["consumption_kwh"] else 0
                comparison["summary"]["consumption_trend"] = {
                    "change_kwh": round(kwh_change, 2),
                    "change_percent": round(kwh_pct, 1),
                    "direction": "increased" if kwh_change > 0 else "decreased" if kwh_change < 0 else "unchanged"
                }

        return json.dumps(comparison, indent=2, default=str)

    except Exception as e:
        return f"Comparison error: {str(e)}"


# Export all RAG tools as a list for easy registration
RAG_TOOLS = [
    # Existing tools
    semantic_search,
    filter_by_metadata,
    get_document_by_id,
    list_available_categories,
    hybrid_search,
    get_statistics,
    # Consumption tools
    extract_consumption_data,
    search_utility_bills,
    compare_consumption,
]
