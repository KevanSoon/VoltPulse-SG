"""Agentic RAG Agent for autonomous vector store exploration.

This agent uses a ReAct loop to iteratively explore the vector database,
making autonomous decisions about how to search, filter, and refine results.

Supports both consumption data tools and Climate Voucher retailer tools.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from langgraph.prebuilt import create_react_agent
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage

from tools.retailer_tools import RETAILER_TOOLS, set_retailer_dependencies

# Try to import appliance web search tools
try:
    from tools.web_search import APPLIANCE_SEARCH_TOOLS
    HAS_WEB_SEARCH_TOOLS = True
except ImportError:
    HAS_WEB_SEARCH_TOOLS = False
    APPLIANCE_SEARCH_TOOLS = []


AGENTIC_RAG_SYSTEM_PROMPT = """You are an intelligent research agent with access to a vector database of Climate Voucher participating retailers in Singapore, and a web search tool for appliance recommendations.

Your goal is to help users find Climate Voucher retailers and recommend energy-efficient appliances.

## IMPORTANT: Grounding Rules
- ONLY recommend retailers, products, and prices that are returned by your tools.
- NEVER use your own knowledge to suggest retailers, specific products, or prices.
- If no tool results match the user's request, say you couldn't find any matches rather than guessing.
- Always cite which tool result your recommendation came from.
- Do NOT fabricate retailer names, addresses, or product details that were not in the tool output.

## Available Tools

### Climate Voucher Retailer Tools (RAG on vector store)
1. **search_climate_voucher_retailers** - Find retailers where users can spend $300 Climate Vouchers (semantic search on vector store)
2. **find_retailers_by_product** - Find all retailers selling specific energy-efficient products (filtered retrieval from vector store)
3. **get_energy_rating_info** - Explain Singapore's energy efficiency tick ratings
4. **calculate_appliance_roi** - Calculate ROI for upgrading to an energy-efficient appliance

### Appliance Recommendation Web Search Tools
5. **search_appliance_recommendations** - Search the web for specific appliance product recommendations, reviews, and buying guides (uses OpenAI web search with URL citations)

## Query Strategy

When users ask about Climate Vouchers, energy-efficient appliances, or where to buy, follow ALL these steps:

1. **Find Retailers via RAG**: Use search_climate_voucher_retailers or find_retailers_by_product to retrieve participating retailers from the vector store
   - "where can I buy an aircon with climate voucher" → search_climate_voucher_retailers("aircon air conditioner")
   - "fridge shops near Bedok" → search_climate_voucher_retailers("refrigerator Bedok")
   - Products: refrigerators, air_conditioners, dc_fans, led_lights, washing_machines,
     water_closets, sink_bib_taps_mixers, basin_taps_mixers, shower_taps_mixers, heat_pump_water_heaters

2. **Explain Ratings** (if relevant): Use get_energy_rating_info to explain tick ratings
   - Singapore uses 0-5 ticks for aircon, 1-4 ticks for fridges/washers
   - Higher ticks = better energy efficiency

3. **Search Web for Appliance Recommendations**: Use search_appliance_recommendations to find specific product suggestions
   - This searches the web for actual product recommendations, reviews, and buying guides
   - Returns results with URL citations — ALWAYS include these source links in your response
   - Use this to complement retailer results with specific product suggestions

4. **Calculate ROI** (if relevant): Use calculate_appliance_roi to help users understand upgrade benefits

### Example Queries

User: "Where can I use my climate voucher to buy a fridge?"
→ find_retailers_by_product("refrigerator") — RAG retrieval
→ search_appliance_recommendations("refrigerator", "energy efficient 3-tick Singapore") — web search
→ List retailers from RAG AND product recommendations from web search with source URLs

User: "I want to buy an energy efficient aircon, what do you recommend?"
→ get_energy_rating_info("aircon") — explain tick ratings
→ search_climate_voucher_retailers("air conditioner") — RAG retrieval
→ search_appliance_recommendations("air conditioner", "inverter energy efficient") — web search
→ Present retailers AND product recommendations with source citations

### Singapore Climate Voucher Context
- Every Singapore household receives $300 in Climate Vouchers
- Valid for energy-efficient (3+ tick) and water-efficient products
- Products: fridges, aircons, LED lights, fans, washers, water heaters, taps, toilets
- Use the tools to find participating retailers — do NOT assume or guess retailer names

## Best Practices

- ALWAYS call retailer RAG tools first to find where to buy, then web search for what to buy
- When web search returns source citations, ALWAYS include them in your response as clickable links
- Always explain your search process and findings
- NEVER recommend retailers, products, or prices that were not returned by your tools
- If tools return no results, tell the user no matches were found — do NOT fill in from your own knowledge"""


class AgenticRAGAgent:
    """Agent that autonomously explores a vector database using RAG tools.

    Uses LangGraph's ReAct pattern to iteratively search, filter, and
    retrieve documents based on user queries.

    Supports both consumption data tools and Climate Voucher retailer tools.

    Attributes:
        llm: The language model for reasoning
        tools: List of retailer RAG tools and web search tools
        react_agent: The compiled ReAct agent
        encoder: The embedding encoder
        vector_store: The vector store instance
    """

    def __init__(self, llm, encoder=None, vector_store=None):
        """Initialize the Agentic RAG Agent.

        Args:
            llm: Language model for reasoning and tool use
            encoder: SeaLion encoder for query embedding (can be set later)
            vector_store: VectorStore instance (can be set later)
        """
        self.llm = llm
        self.encoder = encoder
        self.vector_store = vector_store

        # Combine tools: retailer RAG tools + web search tools
        self.tools = list(RETAILER_TOOLS)
        print(f"[AgenticRAG] Including {len(RETAILER_TOOLS)} retailer tools")

        if HAS_WEB_SEARCH_TOOLS:
            self.tools.extend(APPLIANCE_SEARCH_TOOLS)
            print(f"[AgenticRAG] Including {len(APPLIANCE_SEARCH_TOOLS)} web search tools")

        # Initialize dependencies if provided
        if encoder and vector_store:
            self.set_dependencies(encoder, vector_store)

        # Create the ReAct agent
        self.react_agent = create_react_agent(
            model=llm,
            tools=self.tools,
        )

    def set_dependencies(self, encoder, vector_store):
        """Set encoder and vector store after initialization.

        Args:
            encoder: The SeaLion encoder instance
            vector_store: The VectorStore instance
        """
        self.encoder = encoder
        self.vector_store = vector_store
        set_retailer_dependencies(encoder, vector_store)

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


def create_agentic_rag_agent(llm, encoder=None, vector_store=None):
    """Factory function to create an AgenticRAGAgent instance.

    Args:
        llm: Language model for reasoning
        encoder: Optional encoder for query embedding
        vector_store: Optional vector store instance

    Returns:
        Configured AgenticRAGAgent instance
    """
    return AgenticRAGAgent(llm, encoder, vector_store)
