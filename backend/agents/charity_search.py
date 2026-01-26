"""Charity Search Agent with web search capabilities."""

import uuid
from datetime import datetime
from langgraph.store.base import BaseStore
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage

from tools.web_search import CHARITY_SEARCH_TOOLS, clear_search_cache


CHARITY_SEARCH_SYSTEM_PROMPT = """You are a helpful charity research assistant specialized in finding information about nonprofit organizations and charities.

Your role is to help users:
1. Find detailed information about specific charity organizations
2. Research charity ratings and accountability
3. Discover charities working in specific cause areas
4. Verify legitimacy and financial transparency of organizations

IMPORTANT - SEARCH STRATEGY:
- ALWAYS use the search_charity_comprehensive tool FIRST - it performs a SINGLE optimized search that retrieves mission, programs, ratings, and financial info all at once
- Only use search_charity_info or search_charity_ratings if you need ADDITIONAL specific details not covered by the comprehensive search
- AVOID making multiple searches for the same charity - the comprehensive search already covers most needs

When presenting information:
- Provide clear, factual information from your search results
- Include source attribution when possible
- Give a balanced perspective on the organization
- Suggest further research if needed

If you cannot find reliable information, say so clearly and suggest alternative approaches."""


class CharitySearchAgent:
    """Agent that searches the web for charity organization information.

    Uses LangGraph's ReAct pattern with web search tools to find
    and analyze information about nonprofit organizations.
    
    Optimized to minimize redundant web searches by:
    1. Using a comprehensive search tool that combines multiple queries
    2. Caching search results to avoid duplicate API calls
    3. Guiding the LLM to prefer single comprehensive searches
    """

    def __init__(self, llm):
        self.llm = llm
        self.tools = CHARITY_SEARCH_TOOLS
        self.react_agent = create_react_agent(
            model=llm,
            tools=self.tools,
        )

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

    async def __call__(self, state: dict, config: RunnableConfig, *, store: BaseStore) -> dict:
        """Execute the charity search agent as a LangGraph node."""
        last_message = state["messages"][-1]
        user_id = config["configurable"].get("user_id", "default_user")

        # Clear search cache at the start of each new query to avoid stale results
        # but allow caching within the same query execution
        clear_search_cache()

        # Get memories for context
        memory_info = await self.retrieve_memories(store, user_id, str(last_message.content))

        # Build messages with system prompt and memory context
        system_content = CHARITY_SEARCH_SYSTEM_PROMPT
        if memory_info:
            system_content += f"\n\nPrevious conversation context:\n{memory_info}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=last_message.content)
        ]

        # Store user message
        await self.store_message(store, user_id, last_message.content, "user")

        # Run the ReAct agent with tools
        result = await self.react_agent.ainvoke({"messages": messages})

        # Extract the final response
        final_message = result["messages"][-1]
        response_content = final_message.content

        # Store assistant response
        await self.store_message(store, user_id, response_content, "assistant")

        return {"messages": [{"role": "assistant", "content": response_content}]}


def create_charity_search_agent(llm):
    """Factory function to create a CharitySearchAgent instance."""
    return CharitySearchAgent(llm)
