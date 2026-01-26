from typing import Literal
from pydantic import BaseModel, Field
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig


class MessageClassifier(BaseModel):
    """Classification result for routing messages."""
    message_type: Literal["logical", "donor_search", "volunteer_search", "consumption_query"] = Field(
        ...,
        description="Classify message for routing to appropriate agent."
    )


async def classify_message(state: dict, config: RunnableConfig, *, store: BaseStore, llm) -> dict:
    """Classify user message to route to appropriate agent.

    Args:
        state: Graph state containing messages
        config: Runtime config with user_id, thread_id
        store: Memory store (required by graph but not used here)
        llm: Language model instance

    Returns:
        Dict with message_type for routing
    """
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)

    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """Classify the user message into one of these categories:

Respond ONLY with valid JSON in this exact format:
{"message_type": "TYPE"}

Where TYPE is one of:
- 'consumption_query': Questions about utility bills, electricity usage, kWh consumption, energy costs, billing periods, comparing bills
- 'donor_search': Looking for donors in the database, finding people who donate, matching donors by criteria
- 'volunteer_search': Looking for volunteers in the database, finding people who volunteer, matching volunteers
- 'logical': Facts, information, logical analysis, practical solutions (default for general queries)

Examples:
- "What was my electricity consumption?" → consumption_query
- "Show me my utility bills" → consumption_query
- "How much kWh did I use last month?" → consumption_query
- "Compare my energy bills" → consumption_query
- "How much did I pay for electricity?" → consumption_query
- "Find donors interested in education in Singapore" → donor_search
- "Show me volunteers with tech skills" → volunteer_search
- "What is the capital of France?" → logical
- "Help me find charities" → logical"""
        },
        {
            "role": "user",
            "content": last_message.content
        }
    ])
    return {"message_type": result.message_type}


def create_classifier(llm):
    """Factory to create classifier function with LLM bound.

    Usage:
        llm = ChatOllama(model="gpt-oss:120b-cloud")
        classify = create_classifier(llm)
        graph_builder.add_node("classifier", classify)
    """
    async def classifier_node(state: dict, config: RunnableConfig, *, store: BaseStore):
        return await classify_message(state, config, store=store, llm=llm)

    return classifier_node
