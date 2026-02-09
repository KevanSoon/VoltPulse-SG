"""Agentic RAG Tools for VoltPulse chatbot.

Provides 5 standalone tools:
1. get_user_consumption_info - RAG retrieval of user's consumption data
2. find_retailers_by_product - Find retailers by product category
3. get_energy_rating_info - Explain energy efficiency ratings
4. calculate_appliance_roi - Calculate ROI for appliance upgrades
5. search_appliance_recommendations - Web search (defined in web_search.py)
"""

import json
import os
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

# Import RRF scorer
from recommender.rrf_scorer import RRFScorer, ScoredRetailer
from recommender.planning_areas import PLANNING_AREA_NEIGHBORS

# Global references - set at initialization
_encoder = None
_vector_store = None


def set_retailer_dependencies(encoder, vector_store):
    """Initialize retailer tools with dependencies.

    Args:
        encoder: SeaLion encoder instance
        vector_store: VectorStore instance
    """
    global _encoder, _vector_store
    _encoder = encoder
    _vector_store = vector_store


# Product category mappings for user-friendly queries
PRODUCT_ALIASES = {
    "fridge": "refrigerators",
    "refrigerator": "refrigerators",
    "aircon": "air_conditioners",
    "air conditioner": "air_conditioners",
    "air-conditioner": "air_conditioners",
    "ac": "air_conditioners",
    "fan": "dc_fans",
    "dc fan": "dc_fans",
    "ceiling fan": "dc_fans",
    "light": "led_lights",
    "led": "led_lights",
    "bulb": "led_lights",
    "washing machine": "washing_machines",
    "washer": "washing_machines",
    "toilet": "water_closets",
    "wc": "water_closets",
    "water closet": "water_closets",
    "tap": "sink_bib_taps_mixers",
    "sink tap": "sink_bib_taps_mixers",
    "kitchen tap": "sink_bib_taps_mixers",
    "basin tap": "basin_taps_mixers",
    "bathroom tap": "basin_taps_mixers",
    "shower": "shower_taps_mixers",
    "shower tap": "shower_taps_mixers",
    "water heater": "heat_pump_water_heaters",
    "heater": "heat_pump_water_heaters",
    "heat pump": "heat_pump_water_heaters",
}

# Friendly product names for display
PRODUCT_DISPLAY_NAMES = {
    "refrigerators": "Refrigerators",
    "air_conditioners": "Air-conditioners",
    "dc_fans": "Direct Current (DC) Fans",
    "led_lights": "LED Lights",
    "washing_machines": "Washing Machines",
    "water_closets": "Water Closets (Toilets)",
    "sink_bib_taps_mixers": "Sink/Bib Taps & Mixers",
    "basin_taps_mixers": "Basin Taps & Mixers",
    "shower_taps_mixers": "Shower Taps & Mixers",
    "heat_pump_water_heaters": "Heat Pump Water Heaters",
}


def _normalize_product_category(query: str) -> Optional[str]:
    """Convert user query to standard product category."""
    query_lower = query.lower().strip()

    # Direct match
    if query_lower in PRODUCT_DISPLAY_NAMES:
        return query_lower

    # Alias match
    for alias, category in PRODUCT_ALIASES.items():
        if alias in query_lower:
            return category

    return None


def _format_retailer_results(
    results: List[Any],
    rrf_scores: Optional[List[ScoredRetailer]] = None
) -> str:
    """Format retailer search results for agent consumption.

    Args:
        results: List of SimilarityResult objects
        rrf_scores: Optional list of ScoredRetailer with RRF component scores

    Returns:
        JSON string with retailer details and scores
    """
    if not results:
        return "No retailers found matching your criteria."

    formatted = []
    for i, result in enumerate(results, 1):
        form_data = result.form_data or {}

        # Get eligible products display names
        products = form_data.get("eligible_products", [])
        products_display = [PRODUCT_DISPLAY_NAMES.get(p, p) for p in products]

        entry = {
            "rank": i,
            "retailer_name": form_data.get("retail_outlet", "Unknown"),
            "address": form_data.get("outlet_address", "Unknown"),
            "postal_code": form_data.get("postal_code", ""),
            "planning_area": form_data.get("planning_area", "Unknown"),
            "website": form_data.get("website"),
            "eligible_products": products_display,
            "remarks": form_data.get("remarks"),
            "similarity_score": round(result.score, 4),
        }

        # Add RRF component scores if available
        if rrf_scores:
            rrf_entry = next((r for r in rrf_scores if r.retailer.id == result.id), None)
            if rrf_entry:
                entry["rrf_scores"] = {
                    "semantic": round(rrf_entry.semantic_score, 4),
                    "product": round(rrf_entry.product_score, 4),
                    "location": round(rrf_entry.location_score, 4),
                    "breadth": round(rrf_entry.breadth_score, 4),
                    "intent": round(rrf_entry.intent_score, 4),
                    "final": round(rrf_entry.final_rrf_score, 4)
                }

        formatted.append(entry)

    return json.dumps(formatted, indent=2, ensure_ascii=False)


@tool
async def get_user_consumption_info(query: str) -> str:
    """Retrieve and summarise the user's electricity/utility consumption data.

    Use this tool when the user asks about their bills, electricity usage,
    kWh consumption, energy costs, billing periods, or wants a summary of
    their consumption.

    This performs RAG retrieval over the user's stored utility bill documents
    (uploaded via OCR / Vision) and returns the extracted consumption data.

    Args:
        query: Natural language query about consumption.
               Examples: "What was my electricity consumption last month?",
                        "Show me my utility bills",
                        "How much kWh did I use?"

    Returns:
        JSON string with consumption data from the user's uploaded bills,
        including provider, billing period, kWh, costs, and daily averages.
    """
    print(f"[Tool] get_user_consumption_info - query: '{query}'")

    if _encoder is None or _vector_store is None:
        return "Error: Tools not initialized. Vector store or encoder not available."

    try:
        # Encode the user query
        embedding = await _encoder.encode(query)

        # Search for consumption / OCR documents
        results = await _vector_store.find_similar(
            query_embedding=embedding,
            form_type="ocr",
            limit=5,
        )

        if not results:
            # Also try the "vision" form type
            results = await _vector_store.find_similar(
                query_embedding=embedding,
                form_type="vision",
                limit=5,
            )

        if not results:
            return json.dumps({
                "message": "No utility bill documents found. Please upload your electricity bill first via the Upload page.",
                "documents_found": 0
            }, indent=2)

        # Extract and format consumption data from results
        bills = []
        for result in results:
            form_data = result.form_data or {}

            # Check for vision-extracted data
            extraction_data = form_data.get("extraction_data", {})
            if extraction_data:
                bill_info = {
                    "source_id": result.id,
                    "original_filename": form_data.get("original_filename", "Unknown"),
                    "provider": extraction_data.get("provider_name"),
                    "account_number": extraction_data.get("account_number"),
                    "billing_period_start": extraction_data.get("billing_period_start"),
                    "billing_period_end": extraction_data.get("billing_period_end"),
                    "billing_days": extraction_data.get("billing_days"),
                    "consumption_kwh": extraction_data.get("consumption_kwh"),
                    "daily_average_kwh": extraction_data.get("daily_average_kwh"),
                    "total_amount_sgd": extraction_data.get("total_amount"),
                    "energy_charges_sgd": extraction_data.get("energy_charges"),
                    "gst_amount_sgd": extraction_data.get("gst_amount"),
                    "confidence": extraction_data.get("extraction_confidence"),
                }
            else:
                # Legacy OCR format
                bill_info = {
                    "source_id": result.id,
                    "original_filename": form_data.get("original_filename", "Unknown"),
                    "provider": form_data.get("provider_name"),
                    "consumption_kwh": form_data.get("consumption_kwh"),
                    "total_amount_sgd": form_data.get("total_amount"),
                    "raw_text_preview": (form_data.get("combined_text", "") or "")[:500],
                }

            bills.append(bill_info)

        output = {
            "documents_found": len(bills),
            "bills": bills,
        }

        return json.dumps(output, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Consumption retrieval failed: {str(e)}"}, indent=2)


@tool
async def find_retailers_by_product(
    product: str,
    location: str = "",
    limit: int = 800
) -> str:
    """Find all retailers selling a specific Climate Voucher eligible product.

    Use this when users want to know where they can buy a specific type of
    energy-efficient appliance using their Climate Vouchers.

    Args:
        product: The product type to search for.
                Examples: "refrigerator", "aircon", "LED light", "washing machine",
                         "water heater", "fan", "toilet", "tap"
        location: Optional location / area name the user mentioned.
                  Examples: "Bukit Panjang", "Bedok", "Tampines", "Jurong East"
                  When provided, retailers whose address or name contains
                  this area (or a neighbouring area) are ranked first.
        limit: Maximum number of retailers to return (default: 800)

    Returns:
        JSON list of retailers selling the specified product, with full details.
        When a location is given, results are sorted with nearby retailers first.
    """
    print(f"[Retailer RAG] find_retailers_by_product - product: '{product}', location: '{location}'")

    if _vector_store is None:
        return "Error: Retailer tools not initialized."

    try:
        # Normalize product category
        normalized = _normalize_product_category(product)
        if not normalized:
            return f"Unknown product category: '{product}'. Valid categories: " + \
                   ", ".join(PRODUCT_DISPLAY_NAMES.keys())

        product_display = PRODUCT_DISPLAY_NAMES.get(normalized, product)

        # Query all retailers (use 800 to cover 700+ retailers)
        results = await _vector_store.find_by_form_type("retailer", limit=800)

        # Filter by product
        matching = []
        for result in results:
            form_data = result.form_data or {}
            products = form_data.get("eligible_products", [])
            if normalized in products:
                matching.append(result)

        # ------------------------------------------------------------------
        # Location scoring – uses ONLY address and retailer_name text fields
        # Completely ignores the planning_area metadata field.
        # ------------------------------------------------------------------
        if location and location.strip():
            location_clean = location.strip()

            # Build search terms: the area itself + its neighbours
            search_areas = [location_clean]
            neighbours = PLANNING_AREA_NEIGHBORS.get(location_clean, [])
            search_areas_lower = [a.lower() for a in search_areas]
            neighbours_lower = [n.lower() for n in neighbours]

            def _matches_location(result) -> bool:
                """Check if area name appears in combined retailer_name + address."""
                form_data = result.form_data or {}
                text = (
                    (form_data.get("retail_outlet", "") or "") + " " +
                    (form_data.get("outlet_address", "") or "")
                ).lower()
                return any(term in text for term in search_areas_lower)

            # Only keep retailers whose name or address contains the area
            exact_hits = [r for r in matching if _matches_location(r)]

            if exact_hits:
                matching = exact_hits
                location_note = f"Showing {len(matching)} retailers in {location_clean}"
            else:
                # No text matches – return all, but note it
                matching.sort(key=lambda r: (r.form_data or {}).get("outlet_address", "ZZZ"))
                location_note = (
                    f"No retailers with '{location_clean}' in their address were found. "
                    f"Showing all {len(matching)} retailers for {product_display}."
                )
        else:
            # No location requested – alphabetical by address
            matching.sort(key=lambda r: (r.form_data or {}).get("outlet_address", "ZZZ"))
            location_note = None

        # Return top results
        formatted = _format_retailer_results(matching[:limit])

        # Add summary
        summary: Dict[str, Any] = {
            "product": product_display,
            "total_retailers_found": len(matching),
            "showing": min(limit, len(matching)),
            "retailers": json.loads(formatted),
        }
        if location_note:
            summary["location_note"] = location_note

        return json.dumps(summary, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Search error: {str(e)}"


@tool
async def get_energy_rating_info(product_type: str) -> str:
    """Get information about energy efficiency ratings for a product type.

    Use this to explain Singapore's energy label system and help users
    understand what tick ratings mean for their Climate Voucher purchases.

    Args:
        product_type: Type of appliance.
                     Examples: "aircon", "refrigerator", "washing machine"

    Returns:
        Information about energy labels and ratings for the product type
    """
    print(f"[Retailer RAG] get_energy_rating_info - product: '{product_type}'")

    # Normalize product
    normalized = _normalize_product_category(product_type)

    # Energy label information by product type
    energy_info = {
        "air_conditioners": {
            "product": "Air-conditioners",
            "rating_system": "0-5 Ticks",
            "minimum_for_voucher": "3 Ticks or higher",
            "description": "Higher tick ratings indicate better energy efficiency. A 5-tick aircon uses about 35% less energy than a 1-tick model of the same cooling capacity.",
            "key_metrics": ["Energy Efficiency Ratio (EER)", "Cooling capacity (BTU/hr)", "Power consumption (Watts)"],
            "tips": [
                "Choose inverter models for better efficiency",
                "Consider the right BTU for your room size",
                "Look for units with smart features for optimal scheduling"
            ]
        },
        "refrigerators": {
            "product": "Refrigerators",
            "rating_system": "1-4 Ticks",
            "minimum_for_voucher": "3 Ticks or higher",
            "description": "A 4-tick refrigerator can save about $100 in electricity bills annually compared to a 1-tick model.",
            "key_metrics": ["Annual Energy Consumption (kWh)", "Total Storage Volume (L)", "Energy Efficiency Index"],
            "tips": [
                "Choose the right size for your household",
                "Inverter compressors are more efficient",
                "Side-by-side models typically use more energy"
            ]
        },
        "washing_machines": {
            "product": "Washing Machines",
            "rating_system": "1-4 Ticks",
            "minimum_for_voucher": "4 Ticks",
            "description": "Energy-efficient washing machines use less water and electricity per wash cycle.",
            "key_metrics": ["Water Consumption (L/cycle)", "Energy Consumption (kWh/cycle)", "Wash capacity (kg)"],
            "tips": [
                "Front-load washers are generally more efficient",
                "Look for water efficiency labels too",
                "Consider models with eco-wash programs"
            ]
        },
        "led_lights": {
            "product": "LED Lights",
            "rating_system": "N/A - Must be LED",
            "minimum_for_voucher": "LED type required",
            "description": "LED lights use up to 80% less energy than incandescent bulbs and last much longer.",
            "key_metrics": ["Wattage", "Lumens (brightness)", "Color temperature (K)"],
            "tips": [
                "Check lumen output, not just wattage",
                "Choose appropriate color temperature for each room",
                "Dimmable LEDs offer more flexibility"
            ]
        }
    }

    # Get info or provide general information
    if normalized and normalized in energy_info:
        info = energy_info[normalized]
    else:
        info = {
            "product": product_type,
            "rating_system": "Varies by product",
            "description": "Singapore uses a tick rating system for appliances. Higher ticks mean better energy efficiency. Climate Vouchers can only be used for products meeting minimum efficiency standards.",
            "general_tip": "Visit https://www.nea.gov.sg/our-services/climate-change-energy-efficiency for official energy label information.",
            "eligible_products": list(PRODUCT_DISPLAY_NAMES.values())
        }

    return json.dumps(info, indent=2, ensure_ascii=False)


@tool
async def calculate_appliance_roi(
    product_type: str,
    current_rating: int,
    new_rating: int,
    product_price: float,
    apply_voucher: bool = True,
) -> str:
    """Calculate ROI for upgrading to an energy-efficient appliance.

    Use this tool to help users understand the financial benefits of
    upgrading their appliances using Climate Vouchers.

    Args:
        product_type: Type of appliance (e.g., "aircon", "refrigerator", "washing machine")
        current_rating: Current appliance tick rating (0-5, use 0 for old/unknown)
        new_rating: New appliance tick rating (1-5)
        product_price: Price of new appliance in SGD
        apply_voucher: Whether to apply $300 Climate Voucher (default: True)

    Returns:
        JSON with ROI analysis including annual savings, payback period,
        and long-term benefits
    """
    print(f"[Retailer RAG] calculate_appliance_roi - {product_type}: {current_rating}-tick → {new_rating}-tick @ ${product_price}")

    try:
        from services.roi_calculator import ROICalculator

        calculator = ROICalculator()
        result = calculator.calculate(
            product_type=product_type,
            current_rating=current_rating,
            new_rating=new_rating,
            product_price=product_price,
            apply_voucher=apply_voucher
        )

        # Format a user-friendly response
        output = {
            "product": result.product_display_name,
            "upgrade": f"{current_rating}-tick → {new_rating}-tick",
            "cost_breakdown": {
                "product_price": f"${result.product_price:.2f}",
                "climate_voucher": f"-${result.voucher_amount:.2f}" if result.voucher_amount > 0 else "Not eligible",
                "your_cost": f"${result.net_cost:.2f}"
            },
            "annual_savings": {
                "energy_kwh": f"{result.annual_energy_savings_kwh:.0f} kWh",
                "cost_sgd": f"${result.annual_savings_sgd:.2f}"
            },
            "roi_analysis": {
                "payback_period": f"{result.payback_period_months} months ({result.payback_period_years:.1f} years)",
                "5_year_benefit": f"${result.net_benefit_5_years:.2f}",
                "10_year_benefit": f"${result.net_benefit_10_years:.2f}",
                "annual_roi": f"{result.roi_percent_annual:.1f}%"
            },
            "voucher_eligible": result.is_voucher_eligible,
            "notes": result.notes
        }

        return json.dumps(output, indent=2, ensure_ascii=False)

    except ValueError as e:
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"ROI calculation failed: {str(e)}"}, indent=2)


# Export all tools (excluding web_search which is in web_search.py)
AGENT_TOOLS = [
    get_user_consumption_info,
    find_retailers_by_product,
    get_energy_rating_info,
    calculate_appliance_roi,
]