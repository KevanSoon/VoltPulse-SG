# Agentic RAG System

[← Back to Documentation](../README.md)

## Table of Contents
- [Overview](#overview)
- [What Makes It "Agentic"](#what-makes-it-agentic)
- [ReAct Loop Mechanics](#react-loop-mechanics)
- [The 5 Tools](#the-5-tools)
- [Tool Selection Strategy](#tool-selection-strategy)
- [Memory Management](#memory-management)
- [Grounding Rules](#grounding-rules)
- [Implementation Details](#implementation-details)

---

## Overview

The VoltPulse-SG **Agentic RAG (Retrieval-Augmented Generation)** system is an autonomous AI agent that uses a **ReAct (Reasoning + Acting)** loop to handle user queries by selecting and invoking appropriate tools. Unlike traditional RAG systems that simply retrieve and generate, this agent **reasons** about which tools to use and **acts** autonomously to gather information.

**Key Characteristics:**
- **Autonomous**: Agent decides which tools to invoke based on user intent
- **Multi-tool**: 5 specialized tools for different query types
- **Memory-enabled**: Retrieves context from past conversations
- **Grounded**: Only uses tool results, preventing hallucinations
- **Streaming-capable**: Real-time response generation

**Implementation:** [`backend/agents/agentic_rag.py`](../../backend/agents/agentic_rag.py)

---

## What Makes It "Agentic"

Traditional RAG systems follow a fixed pattern:
```
Query → Retrieve documents → Generate response
```

**Agentic RAG** adds reasoning and tool selection:
```
Query → [Thought: What information do I need?]
      → [Action: Select and invoke tool(s)]
      → [Observation: Process tool results]
      → [Thought: Do I have enough information?]
      → [Action: Invoke more tools OR generate response]
```

### Comparison

| Feature | Traditional RAG | Agentic RAG (VoltPulse) |
|---------|----------------|-------------------------|
| Tool selection | Fixed (always retrieves) | Autonomous (agent decides) |
| Multi-step reasoning | No | Yes (ReAct loop) |
| Multiple tools | No | Yes (5 tools) |
| Query classification | External | Built-in (classifier node) |
| Tool orchestration | Manual | Automatic (LangGraph) |
| Memory | Limited | Full conversation history |

---

## ReAct Loop Mechanics

The agent uses LangGraph's `create_react_agent` to implement the ReAct pattern.

### ReAct Cycle

```python
# From backend/agents/agentic_rag.py lines 158-161
self.react_agent = create_react_agent(
    model=llm,
    tools=self.tools,
)
```

**ReAct Execution Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│  USER QUERY: "What was my electricity consumption?"         │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  [THOUGHT 1] The user wants their electricity consumption   │
│              data. I should use get_user_consumption_info.  │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  [ACTION 1] Invoke get_user_consumption_info(                │
│                user_id="user123",                            │
│                query="electricity consumption"               │
│             )                                                │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  [OBSERVATION 1] Tool returned:                             │
│  "Electricity: 420 kWh, Cost: $151.20,                      │
│   National avg: 400 kWh, You're 5% above average"           │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  [THOUGHT 2] I have the consumption data. I can now         │
│              summarize it for the user.                     │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  [RESPONSE] Your electricity consumption was 420 kWh,       │
│             costing $151.20. This is 5% above the national  │
│             average of 400 kWh for similar households.      │
└─────────────────────────────────────────────────────────────┘
```

### Multi-Step Example

For complex queries, the agent can invoke multiple tools:

```
USER: "Best aircon for my 4-room HDB near Bedok?"

[Thought 1] User wants appliance recommendations AND retailer locations.
[Action 1] Invoke search_appliance_recommendations("best aircon 4-room HDB")
[Observation 1] "Daikin Inverter 24000 BTU (5-tick), Mitsubishi Starmex..."

[Thought 2] I have product recommendations. Now find retailers near Bedok.
[Action 2] Invoke find_retailers_by_product("air_conditioners", "Bedok")
[Observation 2] "Gain City (Bedok), Courts (Tampines), Harvey Norman..."

[Thought 3] I have both products and locations. Can provide complete answer.
[Response] For a 4-room HDB, I recommend:
1. Daikin Inverter 24000 BTU (5-tick) - highly efficient...
2. Mitsubishi Starmex - reliable and quiet...

Retailers near Bedok:
• Gain City (Bedok) - 123 Bedok North, accepts Climate Voucher
• Courts (Tampines) - 10 min away...
```

---

## The 5 Tools

### Tool 1: `get_user_consumption_info`

**Purpose:** Retrieve user's uploaded electricity/utility bill data via RAG.

**When to use:**
- User asks about "my bill", "my consumption", "my kWh"
- Questions about billing periods, costs, usage patterns

**Implementation:** [`backend/tools/retailer_tools.py:40-98`](../../backend/tools/retailer_tools.py#L40-L98)

```python
@tool
async def get_user_consumption_info(query: str) -> str:
    """Retrieve and summarise the user's electricity/utility consumption data.

    This performs RAG retrieval over the user's stored utility bill documents
    (uploaded via OCR / Vision) and returns the extracted consumption data.
    """
    encoder = _get_encoder()
    vector_store = _get_vector_store()

    # 1. Encode query with SEALION
    query_embedding = await encoder.encode(query)

    # 2. Vector search with form_type filter
    results = await vector_store.find_similar(
        query_embedding,
        form_type="ocr",  # Only bill data
        limit=3
    )

    # 3. Format results for LLM
    if not results:
        return "No consumption data found for this user."

    # Extract and format bill data
    consumption_data = []
    for result in results:
        data = result.form_data or {}
        consumption_data.append({
            "electricity_kwh": data.get("consumption_kwh"),
            "cost_sgd": data.get("total_charges_sgd"),
            "billing_period": data.get("billing_period"),
            "national_average": data.get("national_average"),
        })

    return json.dumps(consumption_data, indent=2)
```

**Example Queries:**
- "What was my electricity consumption?"
- "Show me my last bill"
- "How much did I pay for electricity?"

**Performance:** ~200ms latency (embedding generation + vector search)

---

### Tool 2: `get_energy_rating_info`

**Purpose:** Explain Singapore's energy efficiency tick rating system.

**When to use:**
- User asks about "tick ratings", "energy labels", "what is 4-tick"
- Questions about minimum ratings for Climate Voucher eligibility

**Implementation:** [`backend/tools/retailer_tools.py:101-151`](../../backend/tools/retailer_tools.py#L101-L151)

```python
@tool
def get_energy_rating_info(product_type: str) -> str:
    """Explains Singapore's energy efficiency tick rating system.

    Args:
        product_type: Type of product (e.g., "air_conditioner", "refrigerator")

    Returns:
        Formatted explanation of tick ratings for the product type
    """
    rating_info = {
        "air_conditioners": {
            "min_ticks": 3,
            "max_ticks": 5,
            "description": "5-tick AC uses ~35% less energy than 1-tick",
            "climate_voucher_min": 3,
        },
        "refrigerators": {
            "min_ticks": 1,
            "max_ticks": 4,
            "description": "4-tick fridge uses ~30% less energy than 1-tick",
            "climate_voucher_min": 2,
        },
        # ... other products
    }

    info = rating_info.get(product_type, {})
    return f"""
Singapore Energy Label Information for {product_type}:

• Rating scale: {info['min_ticks']}-{info['max_ticks']} ticks
• {info['description']}
• Climate Voucher minimum: {info['climate_voucher_min']} ticks
• More ticks = better efficiency = lower electricity bills

Higher-rated appliances cost more upfront but save money over time through
lower electricity consumption. Use the Climate Voucher ($300) to offset the
higher purchase price!
"""
```

**Example Queries:**
- "What is a 4-tick rating?"
- "Explain energy labels for aircon"
- "Minimum tick rating for Climate Voucher?"

---

### Tool 3: `calculate_appliance_roi`

**Purpose:** Calculate return on investment for upgrading to energy-efficient appliances.

**When to use:**
- User asks about "savings", "payback period", "worth it", "ROI"
- Questions like "Should I upgrade my fridge?"

**Implementation:** [`backend/tools/retailer_tools.py:154-210`](../../backend/tools/retailer_tools.py#L154-L210)

**Key Feature:** Automatically defaults missing parameters (no need to ask user).

```python
@tool
def calculate_appliance_roi(
    product_type: str,
    current_rating: int = 0,  # Default to old/unknown
    new_rating: int = 5,      # Default to best rating
    product_price: float = 0,  # Default to auto-estimate
    apply_voucher: bool = True  # Default to using voucher
) -> str:
    """Calculate ROI for upgrading to energy-efficient appliances.

    IMPORTANT: Always call this tool immediately. Do NOT ask the user for
    missing parameters. Use defaults:
    - current_rating=0 if unknown (assumes old appliance)
    - product_price=0 to auto-estimate from typical market prices
    - apply_voucher=True (always apply $300 Climate Voucher)
    """
    from services.roi_calculator import ROICalculator

    calculator = ROICalculator()
    result = calculator.calculate_roi(
        product_type=product_type,
        current_rating=current_rating,
        new_rating=new_rating,
        product_price=product_price,
        apply_voucher=apply_voucher
    )

    return f"""
ROI Analysis for {product_type} upgrade:

Purchase Details:
• Product price: ${result.product_price}
• Climate Voucher: -${result.voucher_discount}
• Net cost: ${result.net_cost}

Savings:
• Annual savings: ${result.annual_savings}
• Monthly savings: ${result.monthly_savings}
• Payback period: {result.payback_months} months

Long-term Benefits:
• 5-year savings: ${result.savings_5_year}
• 10-year savings: ${result.savings_10_year}

Recommendation: {result.recommendation}
"""
```

**Example Queries:**
- "Is upgrading my aircon worth it?"
- "Calculate savings for 5-tick fridge"
- "ROI for new washing machine"

**Why defaults matter:** Prevents agent from asking user for data they don't have. Better UX.

---

### Tool 4: `search_appliance_recommendations`

**Purpose:** Search the web for specific product recommendations, reviews, and buying guides.

**When to use:**
- User wants product suggestions, model comparisons, latest deals
- Questions like "Best inverter aircon 2025"

**Implementation:** [`backend/tools/web_search.py:58-106`](../../backend/tools/web_search.py#L58-L106)

```python
@tool
def search_appliance_recommendations(query: str) -> str:
    """Perform web search using OpenAI and return text + citations.

    Returns results with URL citations. ALWAYS include source links in response.
    """
    cache_key = query.lower().strip()

    # Check cache (15-minute TTL)
    if cache_key in _response_cache:
        return _response_cache[cache_key]

    # Call OpenAI web search API
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}],
        tools=[{"type": "web_search"}]
    )

    # Extract results with citations
    results = response.choices[0].message.content
    citations = response.citations  # URLs from web search

    # Format with citations
    formatted = f"{results}\n\nSources:\n"
    for i, cite in enumerate(citations, 1):
        formatted += f"{i}. {cite.title}: {cite.url}\n"

    # Cache result
    _response_cache[cache_key] = formatted
    return formatted
```

**Example Queries:**
- "Best inverter aircon 2025"
- "Recommend a fridge for 4-room HDB"
- "Daikin vs Mitsubishi aircon comparison"

**Important:** Always include source URLs in agent response for transparency.

---

### Tool 5: `find_retailers_by_product`

**Purpose:** Find Climate Voucher participating retailers that sell a specific product.

**When to use:**
- User asks "where to buy", "which shops", "near me"
- Questions about Climate Voucher acceptance

**Implementation:** [`backend/tools/retailer_tools.py:251-357`](../../backend/tools/retailer_tools.py#L251-L357)

**This is the most complex tool - uses RRF ranking!**

```python
@tool
async def find_retailers_by_product(
    product: str,
    location: str = "",
    limit: int = 10
) -> str:
    """Find all retailers selling a specific Climate Voucher eligible product.

    Uses multi-signal RRF ranking to return best matches.
    """
    encoder = _get_encoder()
    vector_store = _get_vector_store()

    # 1. Normalize product category
    normalized = _normalize_product_category(product)

    # 2. Generate query embedding
    query_text = f"Find retailers selling {product}"
    if location:
        query_text += f" near {location}"
    query_embedding = await encoder.encode(query_text)

    # 3. Vector search over retailers
    candidates = await vector_store.find_similar(
        query_embedding,
        form_type="retailer",
        limit=800  # Bounded search
    )

    # 4. Filter by product
    matching = [
        c for c in candidates
        if normalized in c.form_data.get("eligible_products", [])
    ]

    # 5. RRF ranking (5 signals)
    from recommender.rrf_scorer import RRFScorer
    scorer = RRFScorer()

    scored = await scorer.score_retailers(
        query_embedding=query_embedding,
        query_text=query_text,
        candidates=matching,
        query_product=normalized,
        query_area=location,
        limit=limit
    )

    # 6. Format results with RRF scores
    results = []
    for ranked in scored:
        retailer = ranked.retailer.form_data
        results.append({
            "rank": ranked.final_rank,
            "name": retailer.get("retail_outlet"),
            "address": retailer.get("outlet_address"),
            "postal_code": retailer.get("postal_code"),
            "planning_area": retailer.get("planning_area"),
            "products": retailer.get("eligible_products"),
            "website": retailer.get("website"),
            "scores": {
                "semantic": ranked.semantic_score,
                "product": ranked.product_score,
                "location": ranked.location_score,
                "breadth": ranked.breadth_score,
                "intent": ranked.intent_score,
                "final_rrf": ranked.final_rrf_score
            }
        })

    return json.dumps(results, indent=2)
```

**Example Queries:**
- "Where to buy aircon with Climate Voucher?"
- "Fridge shops near Bedok"
- "Retailers selling LED lights"

**Performance:** ~300ms (embedding + vector search + RRF ranking)

---

## Tool Selection Strategy

The agent doesn't blindly follow the classifier's hint - it can **override** and invoke multiple tools.

### Classifier Provides Hint

```python
# From backend/agents/classifier.py lines 44-75
class MessageClassifier(BaseModel):
    message_type: Literal[
        "consumption_info",      # → Hint: use Tool 1
        "energy_rating_info",    # → Hint: use Tool 2
        "appliance_roi",         # → Hint: use Tool 3
        "web_search",            # → Hint: use Tool 4
        "retailer_search"        # → Hint: use Tool 5
    ]
```

### Agent Can Override

**System prompt guidance (lines 73-94):**

```python
AGENTIC_RAG_SYSTEM_PROMPT = """...

## Query Strategy

**For product recommendation questions:**
→ First call find_retailers_by_product to find where to buy
→ Then call search_appliance_recommendations for what to buy
→ Present both retailer locations AND product recommendations with source URLs

**For "where to buy" questions:**
→ Call find_retailers_by_product with the product type
→ Optionally call search_appliance_recommendations if user also wants suggestions
"""
```

**Example of agent overriding:**

```
Classifier: "appliance_roi" (suggests Tool 3 only)

Agent reasoning:
  "User asks about ROI, but also wants to know where to buy.
   I should call BOTH calculate_appliance_roi AND find_retailers_by_product."

Tools invoked:
  1. calculate_appliance_roi("air_conditioner", ...)
  2. find_retailers_by_product("air_conditioners", "Bedok")

Response: "Upgrading to 5-tick AC saves $200/year, payback in 18 months.
           Here are retailers near Bedok: Gain City, Courts..."
```

---

## Memory Management

The agent has **persistent memory** across conversations using LangGraph's AsyncPostgresStore.

### Memory Storage

```python
# From backend/agents/agentic_rag.py lines 180-188
async def store_message(self, store: BaseStore, user_id: str, content: str, role: str):
    """Store message to memory store."""
    memory_id = str(uuid.uuid4())
    namespace = ("memories", user_id)
    await store.aput(namespace, memory_id, {
        "data": content,
        "role": role,
        "timestamp": datetime.now().isoformat()
    })
```

### Memory Retrieval (Semantic Search!)

```python
# From backend/agents/agentic_rag.py lines 174-178
async def retrieve_memories(self, store: BaseStore, user_id: str, query: str) -> str:
    """Fetch relevant memories for this user."""
    namespace = ("memories", user_id)
    memories = await store.asearch(namespace, query=query)  # Semantic search
    return "\n".join([d.value.get("data", "") for d in memories])
```

**Key feature:** `store.asearch` performs **semantic search** over memories, not just keyword matching!

### Memory in System Prompt

```python
# Lines 259-270
memory_info = await self.retrieve_memories(store, user_id, str(last_message.content))

system_content = AGENTIC_RAG_SYSTEM_PROMPT
if memory_info:
    system_content += f"\n\n## Previous Conversation Context\n{memory_info}"

messages = [
    SystemMessage(content=system_content),
    HumanMessage(content=last_message.content)
]
```

**Example:**
```
User (Day 1): "My electricity was 450 kWh last month"
[Stored in memory]

User (Day 5): "Should I upgrade my aircon?"
[Memory retrieved: "User mentioned 450 kWh consumption"]

Agent: "Given your 450 kWh consumption (above 400 kWh average), upgrading
        to a 5-tick aircon could save you $200/year..."
```

---

## Grounding Rules

The system prompt enforces strict grounding to **prevent hallucinations**.

### Grounding Prompt (lines 33-38)

```python
"""
## IMPORTANT: Grounding Rules
- ONLY provide information that is returned by your tools.
- NEVER use your own knowledge to suggest retailers, specific products, or prices.
- If no tool results match the user's request, say you couldn't find any matches rather than guessing.
- Always cite which tool result your information came from.
- Do NOT fabricate retailer names, addresses, product details, or consumption data.
"""
```

### Why This Matters

**Without grounding:**
```
User: "Where to buy aircon near Woodlands?"
Agent: "Try Best Denki at Causeway Point or Harvey Norman at Woodlands Civic Centre."
[PROBLEM: Agent hallucinated retailers - Best Denki might not accept Climate Voucher!]
```

**With grounding:**
```
User: "Where to buy aircon near Woodlands?"
Agent calls find_retailers_by_product("air_conditioners", "Woodlands")
Tool returns: [Gain City (Woodlands), Courts (Yishun)]
Agent: "Climate Voucher retailers near Woodlands:
        • Gain City (Woodlands) - 123 Woodlands Ave...
        • Courts (Yishun) - 10 min away..."
[CORRECT: Only recommends verified Climate Voucher retailers]
```

---

## Implementation Details

### Full Agent Initialization

```python
# From backend/agents/agentic_rag.py lines 131-161
class AgenticRAGAgent:
    def __init__(self, llm, encoder=None, vector_store=None):
        self.llm = llm
        self.encoder = encoder
        self.vector_store = vector_store

        # Combine core tools + web search tools
        self.tools = list(AGENT_TOOLS)
        if HAS_WEB_SEARCH_TOOLS:
            self.tools.extend(APPLIANCE_SEARCH_TOOLS)

        # Create ReAct agent with tools
        self.react_agent = create_react_agent(
            model=llm,
            tools=self.tools,
        )
```

### LangGraph Integration

```python
# From backend/graph/builder.py lines 87-103
agentic_rag_agent = AgenticRAGAgent(llm, encoder, vector_store)

graph_builder = StateGraph(State)
graph_builder.add_node("classifier", create_classifier(llm))
graph_builder.add_node("agentic_rag", agentic_rag_agent)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "classifier",
    router,
    {"agentic_rag": "agentic_rag"}
)
graph_builder.add_edge("agentic_rag", END)

graph = graph_builder.compile(
    checkpointer=checkpointer,
    store=store,
)
```

---

## Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Classifier | ~200ms | Pre-categorize query |
| Tool 1 (Consumption RAG) | ~200ms | Embedding + vector search |
| Tool 2 (Energy Ratings) | <10ms | Static data |
| Tool 3 (ROI Calculator) | ~50ms | Pre-computed tables |
| Tool 4 (Web Search) | ~1-2s | OpenAI web search API, cached |
| Tool 5 (Retailer RRF) | ~300ms | Embedding + vector search + RRF |
| **Total (single tool)** | **~400-700ms** | Classifier + tool + response |
| **Total (multi-tool)** | **~1-2s** | Depends on tools invoked |

---

## Cross-References

- [SEALION Integration](./sealion-integration.md) - Embedding generation for Tools 1 & 5
- [Cost Optimization](./cost-optimization.md) - Classifier reduces tool calls by 52%
- [RRF Algorithm](../03-recommender-system/rrf-algorithm.md) - Tool 5 ranking logic
- [LangGraph Orchestration](./langgraph-orchestration.md) - Graph state management
- [API Reference: Tools](../05-api-reference/tools.md) - Complete tool specifications

---

[← Back to Documentation](../README.md) | [Next: SEALION Integration →](./sealion-integration.md)
