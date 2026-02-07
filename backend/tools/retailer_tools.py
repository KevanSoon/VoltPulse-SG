"""Climate Voucher Retailer RAG Tools.

Provides agentic tools for:
1. Searching Climate Voucher participating retailers
2. Finding retailers by product category
3. Getting energy rating information
4. Calculating appliance upgrade ROI
"""

import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

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


def _format_retailer_results(results: List[Any]) -> str:
    """Format retailer search results for agent consumption."""
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
        formatted.append(entry)

    return json.dumps(formatted, indent=2, ensure_ascii=False)


@tool
async def search_climate_voucher_retailers(
    query: str,
    product_category: Optional[str] = None,
    planning_area: Optional[str] = None,
    limit: int = 10
) -> str:
    """Search for Climate Voucher participating retailers.

    Use this to find retailers where users can spend their Singapore Climate Vouchers
    on energy-efficient appliances. Searches by natural language query and filters.

    Singapore's Climate Vouchers are $300 vouchers for households to purchase
    energy-efficient and water-efficient products from participating retailers.

    Args:
        query: Natural language search query.
               Examples: "refrigerator shops near Bedok",
                        "where to buy LED lights in Ang Mo Kio",
                        "air conditioner retailers accepting climate vouchers"
        product_category: Optional product filter. Valid values:
                         - refrigerators, air_conditioners, dc_fans, led_lights
                         - washing_machines, water_closets
                         - sink_bib_taps_mixers, basin_taps_mixers, shower_taps_mixers
                         - heat_pump_water_heaters
        planning_area: Optional Singapore planning area filter.
                      Examples: "Bedok", "Ang Mo Kio", "Jurong East"
        limit: Maximum results (default: 10)

    Returns:
        JSON list of matching retailers with:
        - retailer_name, address, postal_code, planning_area
        - website URL
        - eligible_products list
        - remarks (e.g., "By Appointment", "Accepts vouchers upon delivery")
    """
    print(f"[Retailer RAG] search_climate_voucher_retailers - query: '{query}', "
          f"product: {product_category}, area: {planning_area}")

    if _encoder is None or _vector_store is None:
        return "Error: Retailer tools not initialized."

    try:
        # Normalize product category if provided
        normalized_product = None
        if product_category:
            normalized_product = _normalize_product_category(product_category)

        # Enhance query with product context
        enhanced_query = query
        if normalized_product:
            enhanced_query = f"{query} {PRODUCT_DISPLAY_NAMES.get(normalized_product, product_category)}"
        if planning_area:
            enhanced_query = f"{enhanced_query} {planning_area} Singapore"

        # Encode query
        embedding = await _encoder.encode(enhanced_query)

        # Search retailer form type
        results = await _vector_store.find_similar(
            query_embedding=embedding,
            form_type="retailer",
            limit=min(limit * 2, 30),  # Get extra to filter
        )

        # Post-filter by product and area
        filtered_results = []
        for result in results:
            form_data = result.form_data or {}

            # Product filter
            if normalized_product:
                products = form_data.get("eligible_products", [])
                if normalized_product not in products:
                    continue

            # Planning area filter
            if planning_area:
                retailer_area = form_data.get("planning_area", "").lower()
                if planning_area.lower() not in retailer_area:
                    continue

            filtered_results.append(result)

            if len(filtered_results) >= limit:
                break

        return _format_retailer_results(filtered_results)

    except Exception as e:
        return f"Search error: {str(e)}"


@tool
async def find_retailers_by_product(
    product: str,
    limit: int = 15
) -> str:
    """Find all retailers selling a specific Climate Voucher eligible product.

    Use this when users want to know where they can buy a specific type of
    energy-efficient appliance using their Climate Vouchers.

    Args:
        product: The product type to search for.
                Examples: "refrigerator", "aircon", "LED light", "washing machine",
                         "water heater", "fan", "toilet", "tap"
        limit: Maximum number of retailers to return (default: 15)

    Returns:
        JSON list of retailers selling the specified product, with full details
    """
    print(f"[Retailer RAG] find_retailers_by_product - product: '{product}'")

    if _vector_store is None:
        return "Error: Retailer tools not initialized."

    try:
        # Normalize product category
        normalized = _normalize_product_category(product)
        if not normalized:
            return f"Unknown product category: '{product}'. Valid categories: " + \
                   ", ".join(PRODUCT_DISPLAY_NAMES.keys())

        product_display = PRODUCT_DISPLAY_NAMES.get(normalized, product)

        # Query all retailers
        results = await _vector_store.find_by_form_type("retailer", limit=500)

        # Filter by product
        matching = []
        for result in results:
            form_data = result.form_data or {}
            products = form_data.get("eligible_products", [])
            if normalized in products:
                matching.append(result)

        # Sort by planning area for organization
        matching.sort(key=lambda r: r.form_data.get("planning_area", "ZZZ"))

        # Return top results
        formatted = _format_retailer_results(matching[:limit])

        # Add summary
        summary = {
            "product": product_display,
            "total_retailers_found": len(matching),
            "showing": min(limit, len(matching)),
            "retailers": json.loads(formatted)
        }

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


# Export all retailer tools
RETAILER_TOOLS = [
    search_climate_voucher_retailers,
    find_retailers_by_product,
    get_energy_rating_info,
    calculate_appliance_roi,
]