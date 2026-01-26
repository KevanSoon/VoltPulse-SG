"""Agentic RAG Agent for autonomous vector store exploration.

This agent uses a ReAct loop to iteratively explore the vector database,
making autonomous decisions about how to search, filter, and refine results.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from langgraph.prebuilt import create_react_agent
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage

from tools.rag_tools import RAG_TOOLS, set_rag_dependencies


AGENTIC_RAG_SYSTEM_PROMPT = """You are an intelligent research agent with access to a vector database containing donor and volunteer profiles.

Your goal is to help users find the most relevant matches by autonomously exploring the database.

## Available Tools

1. **list_available_categories** - Start here to understand what data exists (countries, causes, types)
2. **get_statistics** - Get database size and composition
3. **semantic_search** - Find profiles by natural language query
4. **filter_by_metadata** - Browse by specific field values (country, form_type, etc.)
5. **hybrid_search** - Combine semantic search with filters for precise results
6. **get_document_by_id** - Get full details of a specific profile

## Search Strategy

Follow this iterative exploration process:

1. **Understand the Request**: Parse what the user is looking for
2. **Explore Categories**: Use list_available_categories to see what's available
3. **Initial Search**: Start with semantic_search or hybrid_search
4. **Evaluate Results**: Check if results match user needs
5. **Refine if Needed**: Try different queries or filters if initial results aren't ideal
6. **Deep Dive**: Use get_document_by_id for promising candidates

## Best Practices

- Always explore categories first to understand the data structure
- Combine semantic understanding with metadata filters for best results
- If results seem off, try rephrasing the query or adjusting filters
- Look at multiple candidates before making recommendations
- Provide clear reasoning about why you selected certain results

## Example Exploration

User: "Find donors interested in education in Singapore"

Your approach:
1. Call list_available_categories() to confirm "education" is a valid cause and "SG" is a country
2. Call hybrid_search(query="education donors", country="SG", form_type="donor")
3. Review results - if they're corporate donors but user wants individuals, refine
4. Call hybrid_search(query="individual education supporters", country="SG", form_type="donor")
5. Call get_document_by_id() on top matches for full details
6. Present findings with explanation

Always explain your search process and reasoning to the user."""


class AgenticRAGAgent:
    """Agent that autonomously explores a vector database using RAG tools.
    
    Uses LangGraph's ReAct pattern to iteratively search, filter, and
    retrieve documents based on user queries.
    
    Attributes:
        llm: The language model for reasoning
        tools: List of RAG tools for vector store exploration
        react_agent: The compiled ReAct agent
        encoder: The embedding encoder
        vector_store: The vector store instance
    """

    def __init__(self, llm, encoder=None, vector_store=None):
        """Initialize the Agentic RAG Agent.
        
        Args:
            llm: Language model for reasoning and tool use
            encoder: SeaLion encoder for query embedding (can be set later)
            vector_store: DonorVectorStore instance (can be set later)
        """
        self.llm = llm
        self.tools = RAG_TOOLS
        self.encoder = encoder
        self.vector_store = vector_store
        
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
            vector_store: The DonorVectorStore instance
        """
        self.encoder = encoder
        self.vector_store = vector_store
        set_rag_dependencies(encoder, vector_store)

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
        result = await self.react_agent.ainvoke({"messages": messages})

        # Extract the final response
        final_message = result["messages"][-1]
        response_content = final_message.content

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
