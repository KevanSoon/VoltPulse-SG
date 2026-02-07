"""Web search tool for appliance recommendations using OpenAI's web_search."""

import json
from pprint import pprint
from typing import Dict, Any, Optional, List
from openai import OpenAI
from langchain_core.tools import tool


# Simple in-memory cache to avoid duplicate searches within a session
_search_cache: Dict[str, str] = {}
# Cache for full response objects (with annotations)
_response_cache: Dict[str, Any] = {}


def get_openai_client():
    """Get OpenAI client instance."""
    return OpenAI()


def clear_search_cache():
    """Clear the search cache. Call this at the start of a new conversation."""
    global _search_cache, _response_cache
    _search_cache.clear()
    _response_cache.clear()


def _extract_citations(response) -> List[Dict[str, str]]:
    """Extract URL citations from an OpenAI web search response.

    Parses the response output items to find message content with
    url_citation annotations.

    Args:
        response: The OpenAI responses API response object

    Returns:
        List of citation dicts with 'url' and 'title' keys
    """
    citations = []
    seen_urls = set()

    for item in response.output:
        if getattr(item, "type", None) != "message":
            continue
        for content_block in getattr(item, "content", []):
            for annotation in getattr(content_block, "annotations", []):
                if getattr(annotation, "type", None) == "url_citation":
                    url = getattr(annotation, "url", "")
                    title = getattr(annotation, "title", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        citations.append({"url": url, "title": title})

    return citations


def openai_web_search_with_citations(query: str, use_cache: bool = True) -> Dict[str, Any]:
    """Perform web search using OpenAI and return text + citations.

    Args:
        query: The search query
        use_cache: Whether to use cached results

    Returns:
        Dict with 'text' (str) and 'citations' (list of url/title dicts)
    """
    cache_key = query.lower().strip()
    if use_cache and cache_key in _response_cache:
        print("\n" + "=" * 50)
        print("RETURNING CACHED SEARCH RESULT (with citations)")
        print("=" * 50 + "\n")
        return _response_cache[cache_key]

    print("\n" + "=" * 50)
    print("OPENAI WEB SEARCH (with citations)")
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

        text = response.output_text
        citations = _extract_citations(response)

        print(f"Results received: {len(text)} chars, {len(citations)} citations")

        result = {"text": text, "citations": citations}

        # Cache both text and full result
        _search_cache[cache_key] = text
        _response_cache[cache_key] = result

        return result

    except Exception as e:
        print(f"SEARCH FAILED: {str(e)}")
        return {"text": f"Search failed: {str(e)}", "citations": []}


@tool
def search_appliance_recommendations(
    appliance_type: str,
    context: Optional[str] = None,
) -> str:
    """Search the web for energy-efficient appliance recommendations in Singapore.

    Use this tool AFTER finding Climate Voucher retailers via RAG to enrich the
    response with specific product recommendations, reviews, and buying guides.

    This tool searches the web using OpenAI and returns product recommendations
    along with source URL citations that should be included in the final response.

    Args:
        appliance_type: The type of appliance to search for.
                       Examples: "refrigerator", "air conditioner", "washing machine",
                                "LED light", "water heater", "ceiling fan"
        context: Optional extra context to refine the search.
                Examples: "energy efficient 3-tick", "budget friendly",
                         "best for 4-room HDB", "inverter technology"

    Returns:
        JSON with 'recommendations' (text with product suggestions) and
        'sources' (list of URLs with titles for citation).
    """
    print(f"\n[WebSearch] search_appliance_recommendations - appliance: '{appliance_type}', context: '{context}'")

    # Build a targeted search query for Singapore market
    query_parts = [
        f"best energy efficient {appliance_type}",
        "Singapore 2025 2026",
        "recommendation review",
    ]
    if context:
        query_parts.insert(1, context)

    query = " ".join(query_parts)

    try:
        result = openai_web_search_with_citations(query)

        output = {
            "recommendations": result["text"],
            "sources": result["citations"],
            "appliance_searched": appliance_type,
            "search_query": query,
        }

        return json.dumps(output, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "error": f"Appliance search failed: {str(e)}",
            "appliance_searched": appliance_type,
        }, indent=2)


# All appliance/web search tools for the agentic RAG agent
APPLIANCE_SEARCH_TOOLS = [search_appliance_recommendations]
