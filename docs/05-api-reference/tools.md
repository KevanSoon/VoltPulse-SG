# Agent Tools Reference

Complete specification for all 5 agent tools used by the Agentic RAG system.

---

## Table of Contents

1. [Overview](#overview)
2. [Tool 1: get_user_consumption_info](#tool-1-get_user_consumption_info)
3. [Tool 2: find_retailers_by_product](#tool-2-find_retailers_by_product)
4. [Tool 3: get_energy_rating_info](#tool-3-get_energy_rating_info)
5. [Tool 4: calculate_appliance_roi](#tool-4-calculate_appliance_roi)
6. [Tool 5: search_appliance_recommendations](#tool-5-search_appliance_recommendations)
7. [Tool Selection Strategy](#tool-selection-strategy)
8. [Adding New Tools](#adding-new-tools)

---

## Overview

The Agentic RAG system uses **5 specialized tools** that the agent autonomously selects and invokes based on user queries. Each tool is implemented as a LangChain `@tool` decorated async function.

**Tool Categories:**
1. **RAG Retrieval**: Access user's uploaded utility bills
2. **Retailer Search**: Find Climate Voucher participating retailers
3. **Knowledge Base**: Energy rating explanations
4. **Calculations**: ROI analysis for appliance upgrades
5. **Web Search**: Live product recommendations

**Implementation:** [backend/tools/retailer_tools.py](../../backend/tools/retailer_tools.py) and [backend/tools/web_search.py](../../backend/tools/web_search.py)

---

## Tool 1: get_user_consumption_info

### Purpose

Retrieve and summarize the user's electricity/utility consumption data from uploaded bills.

### When to Use

- User asks about their bills
- Questions about electricity usage, kWh consumption, or energy costs
- Requests for billing periods or consumption summaries

### Function Signature

```python
@tool
async def get_user_consumption_info(query: str) -> str:
    """Retrieve and summarise the user's electricity/utility consumption data.

    Args:
        query: Natural language query about consumption

    Returns:
        JSON string with consumption data from uploaded bills
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Natural language query about consumption |

### Example Invocations

```python
# Example 1: General consumption query
await get_user_consumption_info(
    query="What was my electricity consumption last month?"
)

# Example 2: Cost-focused query
await get_user_consumption_info(
    query="How much did I spend on electricity?"
)

# Example 3: Trend analysis
await get_user_consumption_info(
    query="Show me my consumption trends"
)
```

### Response Format

```json
{
  "documents_found": 2,
  "bills": [
    {
      "source_id": "vision_a3f9e2b1c4d5",
      "original_filename": "bill_jan_2024.jpg",
      "provider": "SP Services",
      "account_number": "8012345678",
      "billing_period_start": "2024-01-01",
      "billing_period_end": "2024-01-31",
      "billing_days": 31,
      "consumption_kwh": 350.5,
      "daily_average_kwh": 11.3,
      "total_amount_sgd": 105.20,
      "energy_charges_sgd": 93.50,
      "gst_amount_sgd": 7.93,
      "confidence": 0.92
    }
  ]
}
```

### Error Handling

```json
{
  "message": "No utility bill documents found. Please upload your electricity bill first via the Upload page.",
  "documents_found": 0
}
```

### Implementation Details

- **Form Types Searched**: `ocr`, `vision`, `utility_bill`
- **Vector Search**: Uses semantic similarity via SEALION embeddings
- **Limit**: Returns up to 5 most relevant bills
- **Data Source**: PostgreSQL vector store with pgvector

**Code Reference:** [backend/tools/retailer_tools.py:153-248](../../backend/tools/retailer_tools.py#L153-L248)

---

## Tool 2: find_retailers_by_product

### Purpose

Find all Climate Voucher participating retailers selling a specific product type.

### When to Use

- User wants to buy a specific appliance (refrigerator, aircon, LED lights, etc.)
- Questions about where to use Climate Vouchers
- Location-based retailer search

### Function Signature

```python
@tool
async def find_retailers_by_product(
    product: str,
    location: str = "",
    limit: int = 800
) -> str:
    """Find all retailers selling a specific Climate Voucher eligible product.

    Args:
        product: Product type to search for
        location: Optional area name for location-based ranking
        limit: Maximum number of retailers to return

    Returns:
        JSON list of retailers with full details
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `product` | string | Yes | - | Product type (refrigerator, aircon, LED light, etc.) |
| `location` | string | No | "" | Planning area for location-based ranking |
| `limit` | integer | No | 800 | Maximum number of results |

### Supported Products

**10 Climate Voucher Categories:**

| Product Category | Aliases |
|-----------------|---------|
| `refrigerators` | fridge, refrigerator |
| `air_conditioners` | aircon, ac, air conditioner, air-conditioner |
| `dc_fans` | fan, dc fan, ceiling fan |
| `led_lights` | light, led, bulb |
| `washing_machines` | washer, washing machine |
| `water_closets` | toilet, wc, water closet |
| `sink_bib_taps_mixers` | tap, sink tap, kitchen tap |
| `basin_taps_mixers` | basin tap, bathroom tap |
| `shower_taps_mixers` | shower, shower tap |
| `heat_pump_water_heaters` | water heater, heater, heat pump |

### Example Invocations

```python
# Example 1: Simple product search
await find_retailers_by_product(
    product="refrigerator",
    limit=10
)

# Example 2: Location-based search
await find_retailers_by_product(
    product="aircon",
    location="Bedok",
    limit=20
)

# Example 3: Using alias
await find_retailers_by_product(
    product="fridge",  # Automatically normalized to "refrigerators"
    location="Tampines"
)
```

### Response Format

```json
{
  "product": "Refrigerators",
  "total_retailers_found": 150,
  "showing": 10,
  "location_note": "Showing 8 retailers in Bedok",
  "retailers": [
    {
      "rank": 1,
      "retailer_name": "Gain City",
      "address": "Megastore 1, 21 Ang Mo Kio Ave 9, Singapore 569777",
      "postal_code": "569777",
      "planning_area": "Ang Mo Kio",
      "website": "https://www.gaincity.com",
      "eligible_products": [
        "Refrigerators",
        "Air-conditioners",
        "Washing Machines"
      ],
      "remarks": "Mega Discounts",
      "similarity_score": 0.8524,
      "rrf_scores": {
        "semantic": 0.92,
        "product": 0.95,
        "location": 0.70,
        "breadth": 0.85,
        "intent": 0.88,
        "final": 0.87
      }
    }
  ]
}
```

### Location Ranking Logic

**Text-Based Matching:**
- Searches retailer name + address for location string
- Includes planning area neighbors (e.g., Bedok includes Tampines, Changi)
- Exact matches ranked first, then alphabetical sort

**Implementation:** [backend/tools/retailer_tools.py:251-357](../../backend/tools/retailer_tools.py#L251-L357)

---

## Tool 3: get_energy_rating_info

### Purpose

Explain Singapore's energy label system and tick ratings for Climate Voucher eligible appliances.

### When to Use

- User asks about tick ratings or energy labels
- Questions about energy efficiency standards
- Clarification on Climate Voucher eligibility requirements

### Function Signature

```python
@tool
async def get_energy_rating_info(product_type: str) -> str:
    """Get information about energy efficiency ratings for a product type.

    Args:
        product_type: Type of appliance

    Returns:
        Information about energy labels and ratings
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_type` | string | Yes | Appliance type (aircon, refrigerator, etc.) |

### Example Invocations

```python
# Example 1: Air conditioner ratings
await get_energy_rating_info(product_type="aircon")

# Example 2: Refrigerator efficiency
await get_energy_rating_info(product_type="refrigerator")

# Example 3: LED lights
await get_energy_rating_info(product_type="led")
```

### Response Format

```json
{
  "product": "Air-conditioners",
  "rating_system": "0-5 Ticks",
  "minimum_for_voucher": "3 Ticks or higher",
  "description": "Higher tick ratings indicate better energy efficiency. A 5-tick aircon uses about 35% less energy than a 1-tick model of the same cooling capacity.",
  "key_metrics": [
    "Energy Efficiency Ratio (EER)",
    "Cooling capacity (BTU/hr)",
    "Power consumption (Watts)"
  ],
  "tips": [
    "Choose inverter models for better efficiency",
    "Consider the right BTU for your room size",
    "Look for units with smart features for optimal scheduling"
  ]
}
```

### Supported Products

- Air-conditioners (0-5 ticks, min 3 for voucher)
- Refrigerators (1-4 ticks, min 3 for voucher)
- Washing Machines (1-4 ticks, min 4 for voucher)
- LED Lights (N/A - must be LED type)

**Implementation:** [backend/tools/retailer_tools.py:360-443](../../backend/tools/retailer_tools.py#L360-L443)

---

## Tool 4: calculate_appliance_roi

### Purpose

Calculate ROI for upgrading to an energy-efficient appliance with Climate Voucher.

### When to Use

- User asks about savings, ROI, or payback period
- Questions about financial benefits of upgrading appliances
- Cost-benefit analysis for Climate Voucher purchases

### Function Signature

```python
@tool
async def calculate_appliance_roi(
    product_type: str,
    new_rating: int,
    current_rating: int = 0,
    product_price: float = 0,
    apply_voucher: bool = True,
) -> str:
    """Calculate ROI for upgrading to an energy-efficient appliance.

    Args:
        product_type: Type of appliance
        new_rating: New appliance tick rating (1-5)
        current_rating: Current appliance tick rating (0-5, default: 0)
        product_price: Price in SGD (0 for auto-estimate)
        apply_voucher: Apply $300 Climate Voucher (default: True)

    Returns:
        JSON with ROI analysis
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `product_type` | string | Yes | - | Appliance type (aircon, refrigerator, etc.) |
| `new_rating` | integer | Yes | - | New appliance tick rating (1-5) |
| `current_rating` | integer | No | 0 | Current appliance tick rating (0 for unknown) |
| `product_price` | float | No | 0 | Price in SGD (0 for auto-estimate) |
| `apply_voucher` | boolean | No | true | Apply $300 Climate Voucher |

### Example Invocations

```python
# Example 1: Full parameters
await calculate_appliance_roi(
    product_type="air_conditioners",
    current_rating=2,
    new_rating=4,
    product_price=1200.00,
    apply_voucher=True
)

# Example 2: Auto-estimate price
await calculate_appliance_roi(
    product_type="refrigerators",
    current_rating=1,
    new_rating=5,
    product_price=0,  # Auto-estimate from typical range
    apply_voucher=True
)

# Example 3: Unknown current rating
await calculate_appliance_roi(
    product_type="washing_machines",
    current_rating=0,  # Unknown/old appliance
    new_rating=4,
    product_price=900.00
)
```

### Response Format

```json
{
  "product_type": "air_conditioners",
  "current_rating": 2,
  "new_rating": 4,
  "product_price": 1200.00,
  "voucher_applied": true,
  "voucher_amount": 300.00,
  "net_cost": 900.00,
  "annual_kwh_savings": 450.5,
  "annual_savings_sgd": 135.15,
  "payback_years": 6.7,
  "five_year_benefit_sgd": -224.25,
  "ten_year_benefit_sgd": 451.50,
  "recommendation": "Good investment. Payback in 6.7 years with positive 10-year returns.",
  "is_voucher_eligible": true,
  "price_estimated": false
}
```

### Auto-Price Estimation

If `product_price` is 0, the tool uses typical market ranges:

| Product | Typical Range (SGD) |
|---------|---------------------|
| Air-conditioners | 800 - 3,000 |
| Refrigerators | 500 - 2,500 |
| Washing Machines | 500 - 2,000 |
| LED Lights | 5 - 50 |
| DC Fans | 50 - 300 |
| Water Heaters | 1,500 - 5,000 |

**Implementation:** [backend/tools/retailer_tools.py:446-531](../../backend/tools/retailer_tools.py#L446-L531)

---

## Tool 5: search_appliance_recommendations

### Purpose

Search the web for energy-efficient appliance recommendations and reviews in Singapore.

### When to Use

- User asks for specific product recommendations
- Questions about best models or brands
- Requests for buying guides or reviews

### Function Signature

```python
@tool
def search_appliance_recommendations(
    appliance_type: str,
    context: Optional[str] = None,
) -> str:
    """Search the web for energy-efficient appliance recommendations in Singapore.

    Args:
        appliance_type: Type of appliance to search for
        context: Optional extra context to refine search

    Returns:
        JSON with recommendations and source URLs
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `appliance_type` | string | Yes | - | Appliance type to search for |
| `context` | string | No | None | Extra context to refine search |

### Example Invocations

```python
# Example 1: General search
await search_appliance_recommendations(
    appliance_type="refrigerator"
)

# Example 2: With context
await search_appliance_recommendations(
    appliance_type="air conditioner",
    context="energy efficient 3-tick inverter for 4-room HDB"
)

# Example 3: Budget-focused
await search_appliance_recommendations(
    appliance_type="washing machine",
    context="budget friendly under $800"
)
```

### Response Format

```json
{
  "recommendations": "Based on current reviews, the top energy-efficient refrigerators in Singapore for 2025 include:\n\n1. **Samsung RL4003SBAS** - 4-tick rating, 400L capacity...",
  "sources": [
    {
      "url": "https://www.example.com/best-refrigerators-2025",
      "title": "Best Energy-Efficient Refrigerators in Singapore 2025"
    },
    {
      "url": "https://www.example.com/fridge-buying-guide",
      "title": "Singapore Refrigerator Buying Guide"
    }
  ]
}
```

### Search Query Construction

The tool builds targeted queries for Singapore market:

```python
query = f"best energy efficient {appliance_type} Singapore 2025 2026 recommendation review {context}"
```

### Caching

- **Cache Duration**: Session-based (15-minute TTL)
- **Cache Key**: Lowercase query string
- **Cache Hit Rate**: ~90% for common queries
- **Purpose**: Reduce API costs and improve response time

**Implementation:** [backend/tools/web_search.py:108-160](../../backend/tools/web_search.py#L108-L160)

---

## Tool Selection Strategy

### Classifier Hints

The agent receives hints from the classifier node:

| Message Type | Suggested Tools |
|--------------|----------------|
| `consumption_query` | get_user_consumption_info |
| `comparison_query` | get_user_consumption_info, calculate_appliance_roi |
| `recommendation_query` | find_retailers_by_product, search_appliance_recommendations |
| `retailer_query` | find_retailers_by_product |
| `general_query` | Any tool as needed |

### Autonomous Override

The agent can **override** classifier hints and select any tool based on query analysis.

**Example:**
```
User: "Where can I buy a 4-tick aircon near Bedok?"
Classifier: retailer_query → find_retailers_by_product
Agent: Correctly uses find_retailers_by_product
```

```
User: "Is it worth upgrading my old fridge to a 5-tick model?"
Classifier: general_query → No specific hint
Agent: Autonomously selects calculate_appliance_roi
```

### Tool Chaining

The agent can chain multiple tools in sequence:

**Example Flow:**
1. `find_retailers_by_product("refrigerator", "Bedok")` → Get retailer list
2. `get_energy_rating_info("refrigerator")` → Explain tick ratings
3. `search_appliance_recommendations("refrigerator", "4-tick")` → Get specific models
4. **Final Response**: Comprehensive answer with retailers, ratings, and recommendations

---

## Adding New Tools

### Step 1: Create Tool Function

```python
# backend/tools/my_tools.py

from langchain_core.tools import tool

@tool
async def my_new_tool(param1: str, param2: int = 10) -> str:
    """Tool description for LLM to understand when to use.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2

    Returns:
        Description of return value
    """
    # Implementation
    result = do_something(param1, param2)
    return json.dumps(result, indent=2)
```

### Step 2: Register in Agent

```python
# backend/agents/agentic_rag.py

from tools.my_tools import my_new_tool
from tools.retailer_tools import AGENT_TOOLS

AGENT_TOOLS = [
    get_user_consumption_info,
    find_retailers_by_product,
    get_energy_rating_info,
    calculate_appliance_roi,
    my_new_tool,  # Add here
]
```

### Step 3: Update Classifier (Optional)

If the tool should be suggested for specific query types, update the classifier:

```python
# backend/agents/classifier.py

# Add new message type or update existing categories
```

### Best Practices

1. **Clear Descriptions**: Write detailed docstrings for LLM understanding
2. **JSON Output**: Return structured JSON for easy parsing
3. **Error Handling**: Return JSON with error messages on failure
4. **Type Hints**: Use Python type hints for all parameters
5. **Async**: Use async functions for I/O operations
6. **Caching**: Implement caching for expensive operations

---

## Related Documentation

- [Agentic RAG System](../02-core-systems/rag-system.md) - ReAct loop and tool orchestration
- [Endpoints Reference](./endpoints.md) - `/rag/search` and `/rag/tools` endpoints
- [Implementation Guide: Adding Tools](../06-implementation-guides/adding-new-tools.md) - Detailed step-by-step guide

---

**Generated:** 2024-06-15
**Tool Count:** 5
**Implementation:** [backend/tools/](../../backend/tools/)
