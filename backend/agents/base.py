import uuid
from datetime import datetime
from abc import ABC, abstractmethod
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig


class BaseMemoryAgent(ABC):
    """Base class for agents with memory capabilities.

    Extracts shared logic from therapist_agent and logical_agent:
    - Memory retrieval from store
    - Automatic storage of all conversations (user + assistant messages)
    - Message construction with system prompt + memories
    - LLM invocation and response formatting
    """

    def __init__(self, llm):
        self.llm = llm

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent defines its own personality/system prompt."""
        pass

    async def retrieve_memories(self, store: BaseStore, user_id: str, query: str) -> str:
        """Fetch relevant memories for this user."""
        namespace = ("memories", user_id)
        memories = await store.asearch(namespace, query=query)
        return "\n".join([d.value.get("data", "") for d in memories])

    async def store_message(self, store: BaseStore, user_id: str, content: str, role: str):
        """Store every message to Supabase automatically.

        Args:
            store: The LangGraph store instance
            user_id: User identifier for namespacing
            content: The message content
            role: Either 'user' or 'assistant'
        """
        memory_id = str(uuid.uuid4())
        namespace = ("memories", user_id)
        await store.aput(namespace, memory_id, {
            "data": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        })

    async def __call__(self, state: dict, config: RunnableConfig, *, store: BaseStore) -> dict:
        """Make the agent callable for LangGraph node compatibility."""
        last_message = state["messages"][-1]
        user_id = config["configurable"].get("user_id", "default_user")

        # Get memories
        memory_info = await self.retrieve_memories(store, user_id, str(last_message.content))

        # Build prompt with memories injected
        full_prompt = f"""{self.system_prompt}

        User information from previous sessions:
        {memory_info}"""

        messages = [
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": last_message.content}
        ]

        # Store user message automatically
        await self.store_message(store, user_id, last_message.content, "user")

        # Get response from LLM
        reply = self.llm.invoke(messages)

        # Store assistant response automatically
        await self.store_message(store, user_id, reply.content, "assistant")

        return {"messages": [{"role": "assistant", "content": reply.content}]}
