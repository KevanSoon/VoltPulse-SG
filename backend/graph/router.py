from .state import State


def router(state: State):
    """Route to appropriate agent based on message type."""
    message_type = state.get("message_type", "logical")
    if message_type == "donor_search":
        return "agentic_rag"
    elif message_type == "volunteer_search":
        return "agentic_rag"
    elif message_type == "consumption_query":
        return "agentic_rag"
    return "logical"
