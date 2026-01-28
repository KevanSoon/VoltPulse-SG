"""Agentic RAG Agent for autonomous vector store exploration.

This agent uses a ReAct loop to iteratively explore the vector database,
making autonomous decisions about how to search, filter, and refine results.

Supports both consumption data tools and Climate Voucher retailer tools.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from langgraph.prebuilt import create_react_agent
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage

from tools.rag_tools import RAG_TOOLS, set_rag_dependencies

# Try to import retailer tools
try:
    from tools.retailer_tools import RETAILER_TOOLS, set_retailer_dependencies
    HAS_RETAILER_TOOLS = True
except ImportError:
    HAS_RETAILER_TOOLS = False
    RETAILER_TOOLS = []


AGENTIC_RAG_SYSTEM_PROMPT = """You are an intelligent research agent with access to a vector database containing:
1. Client profiles with consumption data
2. Utility bill documents (Singapore electricity bills processed via OCR)
3. Climate Voucher participating retailers in Singapore

Your goal is to help users find relevant matches, extract consumption data, and recommend Climate Voucher retailers autonomously.

## Available Tools

### Profile Search Tools
1. **list_available_categories** - Understand what data exists (countries, providers, types)
2. **get_statistics** - Get database size and composition
3. **semantic_search** - Find profiles by natural language query
4. **filter_by_metadata** - Browse by specific field values
5. **hybrid_search** - Combine semantic search with filters
6. **get_document_by_id** - Get full details of a specific document

### Consumption Data Tools (for Singapore electricity bills)
7. **search_utility_bills** - Find stored electricity bills by query
8. **extract_consumption_data** - Extract kWh, costs, billing period from a bill
9. **compare_consumption** - Compare usage across multiple bills

### Climate Voucher Retailer Tools
10. **search_climate_voucher_retailers** - Find retailers where users can spend $300 Climate Vouchers
11. **find_retailers_by_product** - Find all retailers selling specific energy-efficient products
12. **search_appliance_recommendations** - Search web (Tavily) for product recommendations and reviews
13. **get_retailer_promotions** - Find current promotions at specific retailers
14. **compare_appliances_across_retailers** - Compare prices for a specific model
15. **get_energy_rating_info** - Explain Singapore's energy efficiency tick ratings

## Search Strategy for Profiles

1. **Understand the Request**: Parse what the user is looking for
2. **Explore Categories**: Use list_available_categories to see what's available
3. **Initial Search**: Start with semantic_search or hybrid_search
4. **Evaluate Results**: Check if results match user needs
5. **Refine if Needed**: Try different queries or filters
6. **Deep Dive**: Use get_document_by_id for promising candidates

## Consumption Query Strategy

When users ask about electricity bills, usage, or consumption:

1. **Find Bills**: Use search_utility_bills to locate relevant OCR documents
   - "my electricity bills" → search_utility_bills("electricity bills")
   - "recent bills" → search_utility_bills("recent electricity")

2. **Extract Data**: Use extract_consumption_data on found bills
   - Takes source_id from search results
   - Returns structured data: kWh, costs, billing period, provider

3. **Compare Bills**: Use compare_consumption for trends
   - Pass list of source_ids to compare
   - Returns consumption trends, cost analysis

## Climate Voucher Query Strategy

When users ask about Climate Vouchers, energy-efficient appliances, or where to buy:

1. **Find Retailers**: Use search_climate_voucher_retailers with natural language
   - "where can I buy an aircon with climate voucher" → search_climate_voucher_retailers("aircon air conditioner")
   - "fridge shops near Bedok" → search_climate_voucher_retailers("refrigerator Bedok")

2. **Filter by Product**: Use find_retailers_by_product for specific categories
   - Products: refrigerators, air_conditioners, dc_fans, led_lights, washing_machines,
     water_closets, sink_bib_taps_mixers, basin_taps_mixers, shower_taps_mixers, heat_pump_water_heaters

3. **Get Recommendations**: Use search_appliance_recommendations with Tavily
   - Search for specific models, reviews, and prices
   - Include budget and brand preferences

4. **Check Promotions**: Use get_retailer_promotions to find deals
   - Major retailers: Gain City, Courts, Best Denki, Harvey Norman, Audio House

5. **Explain Ratings**: Use get_energy_rating_info to explain tick ratings
   - Singapore uses 0-5 ticks for aircon, 1-4 ticks for fridges/washers
   - Higher ticks = better energy efficiency

### Example Climate Voucher Queries

User: "Where can I use my climate voucher to buy a fridge?"
→ find_retailers_by_product("refrigerator")
→ List retailers with addresses and websites

User: "I want to buy an energy efficient aircon, what do you recommend?"
→ get_energy_rating_info("aircon") - explain tick ratings
→ search_appliance_recommendations("inverter aircon 4-5 tick Singapore")
→ search_climate_voucher_retailers("air conditioner")
→ Present recommendations with where to buy

User: "Best deals on washing machines for climate vouchers?"
→ find_retailers_by_product("washing machine")
→ get_retailer_promotions("Gain City", "washing machine")
→ search_appliance_recommendations("energy efficient washing machine")

### Singapore Climate Voucher Context
- Every Singapore household receives $300 in Climate Vouchers
- Valid for energy-efficient (3+ tick) and water-efficient products
- Products: fridges, aircons, LED lights, fans, washers, water heaters, taps, toilets
- Major participating retailers: Gain City, Courts, Best Denki, Harvey Norman, FairPrice

### Singapore Electricity Context
- Providers: SP Services, Geneco, Keppel, Senoko, Tuas Power
- GST: 9%
- Bills show: kWh consumed, tariff tiers, total cost in SGD

## Best Practices

- For profiles: explore categories first, combine semantic + filters
- For consumption: search bills first, then extract structured data
- For Climate Vouchers: combine retailer search with Tavily recommendations
- Always explain your search process and findings
- Present consumption data clearly with units (kWh, SGD)
- When comparing bills, highlight changes and trends
- For product recommendations, include energy ratings and prices when available"""


class AgenticRAGAgent:
    """Agent that autonomously explores a vector database using RAG tools.

    Uses LangGraph's ReAct pattern to iteratively search, filter, and
    retrieve documents based on user queries.

    Supports both consumption data tools and Climate Voucher retailer tools.

    Attributes:
        llm: The language model for reasoning
        tools: List of RAG tools for vector store exploration
        react_agent: The compiled ReAct agent
        encoder: The embedding encoder
        vector_store: The vector store instance
        include_retailer_tools: Whether retailer tools are included
    """

    def __init__(self, llm, encoder=None, vector_store=None, include_retailer_tools: bool = True):
        """Initialize the Agentic RAG Agent.

        Args:
            llm: Language model for reasoning and tool use
            encoder: SeaLion encoder for query embedding (can be set later)
            vector_store: VectorStore instance (can be set later)
            include_retailer_tools: Whether to include Climate Voucher retailer tools
        """
        self.llm = llm
        self.encoder = encoder
        self.vector_store = vector_store
        self.include_retailer_tools = include_retailer_tools and HAS_RETAILER_TOOLS

        # Combine tools
        self.tools = list(RAG_TOOLS)
        if self.include_retailer_tools:
            self.tools.extend(RETAILER_TOOLS)
            print(f"[AgenticRAG] Including {len(RETAILER_TOOLS)} retailer tools")

        # Initialize dependencies if provided (pass LLM for consumption extraction)
        if encoder and vector_store:
            self.set_dependencies(encoder, vector_store, llm)

        # Create the ReAct agent
        self.react_agent = create_react_agent(
            model=llm,
            tools=self.tools,
        )

    def set_dependencies(self, encoder, vector_store, llm=None):
        """Set encoder and vector store after initialization.

        Args:
            encoder: The SeaLion encoder instance
            vector_store: The VectorStore instance
            llm: Optional LLM for consumption extraction tools
        """
        self.encoder = encoder
        self.vector_store = vector_store
        # Pass LLM for consumption extraction tools
        set_rag_dependencies(encoder, vector_store, llm or self.llm)

        # Also set retailer dependencies if enabled
        if self.include_retailer_tools and HAS_RETAILER_TOOLS:
            tavily_key = os.getenv("TAVILY_API_KEY")
            set_retailer_dependencies(encoder, vector_store, tavily_key)

    async def retrieve_memories(self, store: BaseStore, user_id: str, query: str) -> str:
        """Fetch relevant memories for this user."""
        namespace = ("memories", user_id)
        memories = await store.asearch(namespace, query=query)
        return "\n".join([d.value.get("data", "") for d in memories])

    async def store_message(self, store: BaseStore, user_id: str, content: str, role: str):
        """Store message to memory store."""
        memory_id = str(uuid.uuid4())
        namespace = ("memories", user_id)
        await store.aput(namespace, memory_id, {
            "data": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        })

    async def search(self, query: str, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute a standalone RAG search without state management.
        
        Args:
            query: The user's search query
            config: Optional runnable config
            
        Returns:
            Dictionary with 'response' and 'tool_calls' keys
        """
        print(f"\n[Agentic RAG] search() called with query: '{query}'")
        
        messages = [
            SystemMessage(content=AGENTIC_RAG_SYSTEM_PROMPT),
            HumanMessage(content=query)
        ]
        
        result = await self.react_agent.ainvoke(
            {"messages": messages},
            config=config
        )
        
        # Extract response and tool call history
        final_message = result["messages"][-1]
        
        # Collect tool calls from message history
        tool_calls = []
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "tool": tc.get("name", "unknown"),
                        "args": tc.get("args", {})
                    })
        
        return {
            "response": final_message.content,
            "tool_calls": tool_calls,
            "message_count": len(result["messages"])
        }

    async def __call__(
        self, 
        state: dict, 
        config: RunnableConfig, 
        *, 
        store: BaseStore
    ) -> dict:
        """Execute the agentic RAG agent as a LangGraph node.
        
        This allows the agent to be used within a larger LangGraph workflow.
        
        Args:
            state: Current graph state with messages
            config: Runnable configuration with user_id etc.
            store: LangGraph store for memory persistence
            
        Returns:
            Updated state with agent response
        """
        last_message = state["messages"][-1]
        user_id = config["configurable"].get("user_id", "default_user")
        
        print(f"\n{'='*60}")
        print(f"[Agentic RAG] __call__() invoked via LangGraph")
        print(f"[Agentic RAG] User ID: {user_id}")
        print(f"[Agentic RAG] Message: '{last_message.content}'")
        print(f"{'='*60}")

        # Get memories for context
        memory_info = await self.retrieve_memories(store, user_id, str(last_message.content))

        # Build messages with system prompt and memory context
        system_content = AGENTIC_RAG_SYSTEM_PROMPT
        if memory_info:
            system_content += f"\n\n## Previous Conversation Context\n{memory_info}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=last_message.content)
        ]

        # Store user message
        await self.store_message(store, user_id, last_message.content, "user")

        # Run the ReAct agent with tools
        print(f"[Agentic RAG] Running ReAct agent with tools...")
        result = await self.react_agent.ainvoke({"messages": messages})

        # Extract the final response
        final_message = result["messages"][-1]
        response_content = final_message.content
        
        # Log tool calls made during execution
        tool_calls_made = []
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_made.append(tc.get("name", "unknown"))
        
        print(f"[Agentic RAG] Tools called: {tool_calls_made if tool_calls_made else 'None'}")
        print(f"[Agentic RAG] Response length: {len(response_content)} chars")
        print(f"{'='*60}\n")

        # Store assistant response
        await self.store_message(store, user_id, response_content, "assistant")

        return {"messages": [{"role": "assistant", "content": response_content}]}


def create_agentic_rag_agent(
    llm,
    encoder=None,
    vector_store=None,
    include_retailer_tools: bool = True
):
    """Factory function to create an AgenticRAGAgent instance.

    Args:
        llm: Language model for reasoning
        encoder: Optional encoder for query embedding
        vector_store: Optional vector store instance
        include_retailer_tools: Whether to include Climate Voucher retailer tools

    Returns:
        Configured AgenticRAGAgent instance
    """
    return AgenticRAGAgent(llm, encoder, vector_store, include_retailer_tools)
