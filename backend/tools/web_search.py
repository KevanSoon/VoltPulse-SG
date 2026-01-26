"""Web search tool for searching charity organization information using OpenAI."""

import os
from pprint import pprint
from typing import Dict, Any, Optional
from openai import OpenAI
from langchain_core.tools import tool


# Simple in-memory cache to avoid duplicate searches within a session
_search_cache: Dict[str, str] = {}


def get_openai_client():
    """Get OpenAI client instance."""
    return OpenAI()


def clear_search_cache():
    """Clear the search cache. Call this at the start of a new conversation."""
    global _search_cache
    _search_cache.clear()
    print("🗑️ Search cache cleared")


def openai_web_search(query: str, use_cache: bool = True) -> str:
    """Perform web search using OpenAI's web_search tool.

    Args:
        query: The search query
        use_cache: Whether to use cached results if available

    Returns:
        Search results as text
    """
    # Check cache first
    cache_key = query.lower().strip()
    if use_cache and cache_key in _search_cache:
        print("\n" + "=" * 50)
        print("📦 RETURNING CACHED SEARCH RESULT")
        print("=" * 50)
        pprint({"query": query, "cached": True})
        print("=" * 50 + "\n")
        return _search_cache[cache_key]

    print("\n" + "=" * 50)
    print("🔍 OPENAI WEB SEARCH CALLED")
    print("=" * 50)
    pprint({"query": query})
    print("=" * 50 + "\n")

    client = get_openai_client()

    try:
        response = client.responses.create(
            model="gpt-5",
            tools=[{"type": "web_search"}],
            input=query
        )
        print("\n" + "-" * 50)
        print("✅ SEARCH RESULTS RECEIVED")
        print("-" * 50)
        pprint({"output_length": len(response.output_text)})
        print("-" * 50 + "\n")

        # Cache the result
        _search_cache[cache_key] = response.output_text

        return response.output_text
    except Exception as e:
        print(f"\n❌ SEARCH FAILED: {str(e)}\n")
        return f"Search failed: {str(e)}"


@tool
def search_charity_comprehensive(charity_name: str) -> str:
    """Search the web for comprehensive information about a charity organization.

    This tool performs a SINGLE optimized search to find ALL relevant information
    about a charity including:
    - Mission and programs
    - Charity ratings (Charity Navigator, GuideStar, BBB)
    - Financial transparency and accountability
    - Recent news and impact reports
    - Contact information and ways to donate

    Use this as your PRIMARY tool - it combines general info and ratings in one search.

    Args:
        charity_name: The name of the charity organization to research.
                     Example: "Red Cross" or "Doctors Without Borders"

    Returns:
        Comprehensive search results about the charity including ratings and programs.
    """
    print("\n📋 TOOL CALLED: search_charity_comprehensive")
    pprint({"charity_name": charity_name})

    # Build a comprehensive query that covers all aspects in ONE search
    comprehensive_query = (
        f"{charity_name} charity nonprofit organization "
        f"mission programs impact "
        f"Charity Navigator rating GuideStar "
        f"financial transparency accountability review"
    )

    try:
        results = openai_web_search(comprehensive_query)
        return results
    except Exception as e:
        return f"Search failed: {str(e)}. Please try again with a different query."


@tool
def search_charity_info(query: str) -> str:
    """Search the web for information about a charity organization.

    NOTE: Prefer using search_charity_comprehensive for most queries as it
    combines general info and ratings in a single search.

    Use this tool only when you need to search for something very specific
    that isn't covered by comprehensive search.

    Args:
        query: The search query about the charity organization.
               Example: "Red Cross disaster relief programs 2024"

    Returns:
        Search results containing relevant information about the charity.
    """
    print("\n📋 TOOL CALLED: search_charity_info")
    pprint({"input_query": query})

    # Enhance query for charity-specific searches
    enhanced_query = f"{query} charity nonprofit organization"

    try:
        results = openai_web_search(enhanced_query)
        return results
    except Exception as e:
        return f"Search failed: {str(e)}. Please try again with a different query."


@tool
def search_charity_ratings(charity_name: str) -> str:
    """Search for charity ratings and reviews from watchdog organizations.

    NOTE: Prefer using search_charity_comprehensive as it already includes
    rating information. Use this only if you specifically need MORE detailed
    rating information after the comprehensive search.

    Args:
        charity_name: The name of the charity to look up ratings for.

    Returns:
        Information about the charity's ratings and accountability.
    """
    print("\n⭐ TOOL CALLED: search_charity_ratings")
    pprint({"charity_name": charity_name})

    query = f"{charity_name} charity rating Charity Navigator GuideStar review"

    try:
        results = openai_web_search(query)
        return results
    except Exception as e:
        return f"Rating search failed: {str(e)}. Please try again."


# List of all available tools for the charity search agent
# Put comprehensive search FIRST so the LLM prefers it
CHARITY_SEARCH_TOOLS = [search_charity_comprehensive, search_charity_info, search_charity_ratings]
