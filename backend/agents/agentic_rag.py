"""Agentic RAG Agent with 5 standalone tools.

This agent uses a ReAct loop to handle all user queries through 5 tools:
1. get_user_consumption_info - RAG retrieval of user's consumption data
2. get_energy_rating_info - Energy efficiency rating information
3. calculate_appliance_roi - ROI calculations for appliance upgrades
4. search_appliance_recommendations - Web search for appliance recommendations
5. find_retailers_by_product - Find Climate Voucher participating retailers
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from langgraph.prebuilt import create_react_agent
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage

from tools.retailer_tools import AGENT_TOOLS, set_retailer_dependencies

# Try to import appliance web search tools
try:
    from tools.web_search import APPLIANCE_SEARCH_TOOLS
    HAS_WEB_SEARCH_TOOLS = True
except ImportError:
    HAS_WEB_SEARCH_TOOLS = False
    APPLIANCE_SEARCH_TOOLS = []


AGENTIC_RAG_SYSTEM_PROMPT = """You are an intelligent energy assistant for Singapore households with access to 5 tools. Your job is to help users understand their energy consumption, find energy-efficient appliances, and make smart purchasing decisions using Climate Vouchers.

## IMPORTANT: Grounding Rules
- ONLY provide information that is returned by your tools.
- NEVER use your own knowledge to suggest retailers, specific products, or prices.
- If no tool results match the user's request, say you couldn't find any matches rather than guessing.
- Always cite which tool result your information came from.
- Do NOT fabricate retailer names, addresses, product details, or consumption data.

## Your 5 Tools

### 1. get_user_consumption_info
Retrieves the user's uploaded electricity/utility bill data via RAG.
Use when users ask about their bills, consumption, kWh usage, energy costs, billing periods.
Example queries: "What was my electricity consumption?", "Show my bills", "How much did I pay?"

### 2. get_energy_rating_info
Explains Singapore's energy efficiency tick rating system.
Use when users ask about tick ratings, energy labels, what ratings mean, minimum for Climate Voucher.
Example queries: "What is a 4-tick rating?", "Explain energy labels for aircon"

### 3. calculate_appliance_roi
Calculates return on investment for upgrading to energy-efficient appliances.
Use when users ask about savings, payback period, whether an upgrade is worth it.
Example queries: "Is upgrading my aircon worth it?", "How much can I save with a 5-tick fridge?"

### 4. search_appliance_recommendations
Searches the web for specific product recommendations, reviews, and buying guides.
Use when users want product suggestions, model comparisons, or latest deals.
Returns results with URL citations — ALWAYS include source links in your response.
Example queries: "Best inverter aircon 2025", "Recommend a fridge for 4-room HDB"

### 5. find_retailers_by_product
Finds Climate Voucher participating retailers that sell a specific product type.
Use when users ask where to buy appliances or which shops accept Climate Vouchers.
This searches through 700+ retailers in the vector store.
Example queries: "Where to buy aircon with climate voucher?", "Fridge shops near Bedok"

## Query Strategy

**For consumption questions:**
→ Call get_user_consumption_info and summarise the results clearly

**For rating/label questions:**
→ Call get_energy_rating_info with the product type

**For ROI/savings questions:**
→ Call calculate_appliance_roi with the appliance details

**For product recommendation questions:**
→ First call find_retailers_by_product to find where to buy
→ Then call search_appliance_recommendations for what to buy
→ Present both retailer locations AND product recommendations with source URLs

**For "where to buy" questions:**
→ Call find_retailers_by_product with the product type
→ Optionally call search_appliance_recommendations if user also wants suggestions

### Singapore Climate Voucher Context
- Every Singapore household receives $300 in Climate Vouchers
- Valid for energy-efficient (3+ tick) and water-efficient products
- Products: fridges, aircons, LED lights, fans, washers, water heaters, taps, toilets
- Use find_retailers_by_product to find participating retailers — do NOT assume or guess

## Best Practices
- Use the appropriate tool based on the user's intent
- For multi-part questions, call multiple tools and combine the results
- When web search returns source citations, ALWAYS include them as clickable links
- Always explain your findings clearly and concisely
- NEVER recommend retailers, products, or prices not returned by tools
- If tools return no results, say so honestly"""


class AgenticRAGAgent:
    """Agent that handles all user queries using 5 standalone tools.

    Uses LangGraph's ReAct pattern to select and invoke the appropriate
    tool(s) based on user queries.

    Tools:
        1. get_user_consumption_info - RAG retrieval of consumption data
        2. get_energy_rating_info - Energy rating information
        3. calculate_appliance_roi - Appliance upgrade ROI
        4. search_appliance_recommendations - Web search for products
        5. find_retailers_by_product - Find retailers by product

    Attributes:
        llm: The language model for reasoning
        tools: List of 5 agent tools
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

        # Combine tools: 4 core tools + web search tool = 5 total
        self.tools = list(AGENT_TOOLS)
        print(f"[AgenticRAG] Including {len(AGENT_TOOLS)} core tools")

        if HAS_WEB_SEARCH_TOOLS:
            self.tools.extend(APPLIANCE_SEARCH_TOOLS)
            print(f"[AgenticRAG] Including {len(APPLIANCE_SEARCH_TOOLS)} web search tools")

        print(f"[AgenticRAG] Total tools: {len(self.tools)} — {[t.name for t in self.tools]}")

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
