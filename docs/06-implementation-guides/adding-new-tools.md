# Adding New Agent Tools

Step-by-step guide for extending the Agentic RAG system with custom tools.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Create Tool Function](#step-1-create-tool-function)
4. [Step 2: Register Tool](#step-2-register-tool)
5. [Step 3: Update Classifier (Optional)](#step-3-update-classifier-optional)
6. [Step 4: Test Tool](#step-4-test-tool)
7. [Examples](#examples)
8. [Best Practices](#best-practices)

---

## Overview

The Agentic RAG system currently has 5 tools. You can add custom tools to extend functionality for new use cases.

**Current Tools:**
1. `get_user_consumption_info` - RAG over utility bills
2. `find_retailers_by_product` - Retailer search
3. `get_energy_rating_info` - Energy rating explanations
4. `calculate_appliance_roi` - ROI calculations
5. `search_appliance_recommendations` - Web search

**New Tool Capabilities:**
- Database queries (weather data, tariff rates, etc.)
- External API integrations (SMS, email, payment)
- Calculations (carbon footprint, solar ROI, etc.)
- Data transformations (report generation, charts)

---

## Prerequisites

**Required Knowledge:**
- Python async/await patterns
- LangChain tool decorators
- JSON serialization
- Pydantic models (optional but recommended)

**Files to Modify:**
- `backend/tools/your_tool.py` (create new file)
- `backend/agents/agentic_rag.py` (register tool)
- `backend/agents/classifier.py` (optional, for hints)

---

## Step 1: Create Tool Function

### Basic Template

Create a new file: `backend/tools/tariff_tools.py`

```python
"""Tools for electricity tariff queries."""

import json
from typing import Optional
from langchain_core.tools import tool

@tool
async def get_current_tariff(
    provider: str = "sp_services",
    tariff_type: str = "residential"
) -> str:
    """Get current electricity tariff rates in Singapore.

    Use this tool when users ask about current electricity prices,
    tariff rates, or pricing plans.

    Args:
        provider: Electricity provider (default: "sp_services")
        tariff_type: Tariff type (residential, commercial, industrial)

    Returns:
        JSON string with tariff rates and pricing details
    """
    print(f"[Tool] get_current_tariff - provider: {provider}, type: {tariff_type}")

    # Implement your logic here
    tariffs = {
        "sp_services": {
            "residential": {
                "base_rate": 0.2998,  # SGD per kWh
                "grid_charge": 0.0442,
                "effective_rate": 0.3440,
                "gst": 0.09,
                "effective_date": "2024-01-01",
                "next_review": "2024-04-01"
            }
        }
    }

    provider_data = tariffs.get(provider, {})
    tariff_data = provider_data.get(tariff_type)

    if not tariff_data:
        return json.dumps({
            "error": f"Tariff data not available for {provider}/{tariff_type}",
            "available_providers": list(tariffs.keys())
        }, indent=2)

    result = {
        "provider": provider,
        "tariff_type": tariff_type,
        "rates": tariff_data,
        "note": "Rates subject to quarterly review by EMA"
    }

    return json.dumps(result, indent=2, ensure_ascii=False)
```

### Key Components

**1. Async Function**
```python
async def get_current_tariff(...) -> str:
```
- Must be `async` for non-blocking execution
- Return type must be `str` (JSON formatted)

**2. Decorator**
```python
@tool
```
- LangChain's `@tool` decorator makes function LLM-compatible
- Automatically generates JSON schema from docstring

**3. Docstring**
```python
"""Short description for LLM to understand when to use this tool.

Use this tool when users ask about... (clear trigger conditions)

Args:
    param1: Description with examples

Returns:
    Description of return format
"""
```
- First line: Brief description (shown in tool selection)
- Use this tool when: Explicit triggering conditions
- Args: Parameter descriptions with types and examples
- Returns: Output format description

**4. Logging**
```python
print(f"[Tool] tool_name - param1: {value1}, param2: {value2}")
```
- Log all tool invocations for debugging
- Include all parameter values

**5. JSON Return**
```python
return json.dumps(result, indent=2, ensure_ascii=False)
```
- Always return valid JSON string
- Use `indent=2` for readability
- Use `ensure_ascii=False` for Unicode support

---

### With Database Access

For tools that need database access:

```python
@tool
async def get_solar_potential(postal_code: str) -> str:
    """Get solar panel potential for a location.

    Args:
        postal_code: Singapore 6-digit postal code

    Returns:
        JSON with solar irradiance, roof area, and estimated generation
    """
    from recommender.vector_store import VectorStore
    from graph.builder import create_async_pool

    # Access database
    pool = create_async_pool()
    await pool.open()
    vector_store = VectorStore(pool)

    try:
        # Query solar data
        results = await vector_store.find_by_form_type("solar_data", limit=1)
        # Process results...

        return json.dumps(solar_data, indent=2)

    finally:
        await pool.close()
```

---

### With External API

For tools that call external APIs:

```python
import httpx

@tool
async def send_energy_alert(
    recipient: str,
    alert_type: str,
    message: str
) -> str:
    """Send energy consumption alert via SMS or email.

    Args:
        recipient: Phone number (+65...) or email
        alert_type: "sms" or "email"
        message: Alert message content

    Returns:
        JSON with delivery status
    """
    async with httpx.AsyncClient() as client:
        if alert_type == "sms":
            response = await client.post(
                "https://api.twilio.com/sms/send",
                json={"to": recipient, "body": message}
            )
        # Handle response...

    return json.dumps({"status": "sent", "recipient": recipient}, indent=2)
```

---

## Step 2: Register Tool

### Add to Agent Tools List

Edit `backend/agents/agentic_rag.py`:

```python
# Import your new tool
from tools.tariff_tools import get_current_tariff

# ... existing imports ...
from tools.retailer_tools import (
    get_user_consumption_info,
    find_retailers_by_product,
    get_energy_rating_info,
    calculate_appliance_roi
)
from tools.web_search import search_appliance_recommendations

# Add to AGENT_TOOLS list
AGENT_TOOLS = [
    get_user_consumption_info,
    find_retailers_by_product,
    get_energy_rating_info,
    calculate_appliance_roi,
    search_appliance_recommendations,
    get_current_tariff,  # Add your new tool here
]
```

### Initialize in AgenticRAGAgent

The agent automatically uses all tools in `AGENT_TOOLS`:

```python
class AgenticRAGAgent:
    def __init__(self, llm, encoder, vector_store):
        self.llm = llm
        self.encoder = encoder
        self.vector_store = vector_store
        self.tools = AGENT_TOOLS  # Automatically includes your new tool
```

---

## Step 3: Update Classifier (Optional)

If your tool should be suggested for specific query types, update the classifier.

### Add New Message Type

Edit `backend/agents/classifier.py`:

```python
class MessageType(TypedDict):
    message_type: Literal[
        "consumption_query",
        "comparison_query",
        "recommendation_query",
        "retailer_query",
        "tariff_query",  # Add new type
        "general_query"
    ]
```

### Update Classifier System Prompt

```python
classifier_system_prompt = """You are a query classifier...

Categories:
1. consumption_query: Questions about user's electricity bills...
2. comparison_query: Comparing consumption to averages...
3. recommendation_query: Product recommendations...
4. retailer_query: Where to buy appliances...
5. tariff_query: Current electricity rates, pricing plans, tariff reviews
6. general_query: Everything else

Examples for tariff_query:
- "What's the current electricity rate?"
- "How much does SP Services charge per kWh?"
- "When is the next tariff review?"
"""
```

### Update Router

Edit `backend/graph/router.py` to route the new category:

```python
def router(state: State) -> str:
    """Route based on message type."""
    message_type = state.get("message_type")

    # All routes go to agentic_rag
    # Agent autonomously selects correct tool
    return "agentic_rag"
```

**Note:** Currently, all queries route to the same `agentic_rag` node. The agent autonomously selects the correct tool based on the query, so updating the classifier is optional but can improve efficiency.

---

## Step 4: Test Tool

### Unit Test

Create `backend/tests/test_tariff_tools.py`:

```python
import pytest
import json
from tools.tariff_tools import get_current_tariff

@pytest.mark.asyncio
async def test_get_current_tariff():
    """Test tariff lookup."""
    result = await get_current_tariff.ainvoke({
        "provider": "sp_services",
        "tariff_type": "residential"
    })

    data = json.loads(result)
    assert "rates" in data
    assert data["rates"]["effective_rate"] > 0
    assert data["provider"] == "sp_services"

@pytest.mark.asyncio
async def test_invalid_provider():
    """Test error handling for invalid provider."""
    result = await get_current_tariff.ainvoke({
        "provider": "invalid_provider",
        "tariff_type": "residential"
    })

    data = json.loads(result)
    assert "error" in data
```

Run tests:
```bash
pytest backend/tests/test_tariff_tools.py -v
```

---

### Integration Test via API

Test via the `/rag/search` endpoint:

```bash
curl -X POST http://localhost:7860/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current electricity tariff rate?",
    "max_iterations": 10
  }'
```

Expected response:
```json
{
  "response": "The current residential electricity tariff rate from SP Services is SGD $0.3440 per kWh...",
  "tool_calls": [
    {
      "tool": "get_current_tariff",
      "args": {"provider": "sp_services", "tariff_type": "residential"},
      "result": "{\"provider\": \"sp_services\", ...}"
    }
  ],
  "message_count": 3
}
```

---

### Manual Testing via Chat

```bash
curl -X POST http://localhost:7860/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you tell me the current electricity rates?",
    "user_id": "test_user",
    "thread_id": "test_thread"
  }'
```

---

## Examples

### Example 1: Carbon Footprint Calculator

```python
@tool
async def calculate_carbon_footprint(consumption_kwh: float) -> str:
    """Calculate carbon footprint from electricity consumption.

    Args:
        consumption_kwh: Electricity consumption in kWh

    Returns:
        JSON with CO2 emissions and equivalencies
    """
    # Singapore grid emission factor: 0.4057 kg CO2/kWh (2023)
    emission_factor = 0.4057
    co2_kg = consumption_kwh * emission_factor

    # Equivalencies
    trees_needed = co2_kg / 21.77  # Trees to offset (avg 21.77 kg CO2/year)
    km_driven = co2_kg / 0.192     # Equivalent km driven (0.192 kg CO2/km)

    result = {
        "consumption_kwh": consumption_kwh,
        "co2_emissions_kg": round(co2_kg, 2),
        "equivalencies": {
            "trees_to_offset": round(trees_needed, 1),
            "km_driven_equivalent": round(km_driven, 1)
        },
        "emission_factor": emission_factor,
        "note": "Based on Singapore's grid emission factor (2023)"
    }

    return json.dumps(result, indent=2)
```

---

### Example 2: Weather Data Lookup

```python
import httpx

@tool
async def get_weather_impact(planning_area: str) -> str:
    """Get weather data and estimate impact on energy consumption.

    Args:
        planning_area: Singapore planning area

    Returns:
        JSON with temperature, humidity, and cooling load estimate
    """
    # Call weather API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.data.gov.sg/v1/environment/air-temperature",
            params={"date": "2024-06-15"}
        )
        data = response.json()

    # Extract temperature
    temperature = data["items"][0]["readings"][0]["value"]

    # Estimate cooling load impact
    baseline_temp = 24.0  # Comfortable temperature
    temp_diff = max(0, temperature - baseline_temp)
    cooling_load_increase = temp_diff * 0.08  # 8% per degree

    result = {
        "planning_area": planning_area,
        "current_temperature": temperature,
        "cooling_load_increase_percent": round(cooling_load_increase * 100, 1),
        "recommendation": "Consider using fans instead of aircon" if temp_diff < 3 else "Aircon may be necessary"
    }

    return json.dumps(result, indent=2)
```

---

## Best Practices

### 1. Clear Docstrings

**Good:**
```python
"""Get current electricity tariff rates in Singapore.

Use this tool when users ask about current electricity prices,
tariff rates, or pricing plans.

Args:
    provider: Electricity provider (sp_services, senoko, etc.)
"""
```

**Bad:**
```python
"""Gets tariff."""  # Too vague, agent won't know when to use it
```

---

### 2. Error Handling

Always return JSON even for errors:

```python
@tool
async def my_tool(param: str) -> str:
    try:
        # Main logic
        result = process(param)
        return json.dumps(result, indent=2)

    except ValueError as e:
        return json.dumps({
            "error": "Invalid parameter",
            "details": str(e)
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": "Tool execution failed",
            "details": str(e)
        }, indent=2)
```

---

### 3. Parameter Defaults

Provide sensible defaults to reduce user friction:

```python
@tool
async def get_tariff(
    provider: str = "sp_services",  # Default to most common
    tariff_type: str = "residential",
    include_gst: bool = True
) -> str:
```

---

### 4. Structured Output

Use consistent JSON structure:

```python
{
  "status": "success",  # or "error"
  "data": {...},         # Main result
  "metadata": {          # Optional metadata
    "timestamp": "2024-06-15T10:30:00Z",
    "source": "sp_services",
    "version": "1.0"
  },
  "message": "Optional human-readable message"
}
```

---

### 5. Performance Optimization

- **Cache expensive operations:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fetch_tariff_data(provider: str):
    # Expensive database query
    return data
```

- **Use connection pooling:**
```python
# Reuse database connections instead of creating new ones
```

- **Timeout long operations:**
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(url)
```

---

## Related Documentation

- [Tools Reference](../05-api-reference/tools.md) - Complete tool specifications
- [Agentic RAG System](../02-core-systems/rag-system.md) - Tool orchestration
- [Endpoints Reference](../05-api-reference/endpoints.md) - `/rag/search` endpoint

---

**Generated:** 2024-06-15
**Target Audience:** Backend developers
**Difficulty:** Intermediate
