from .state import State


def router(state: State):
    """Route to appropriate agent based on message type."""
    message_type = state.get("message_type", "logical")
    if message_type == "emotional":
        return "therapist"
    elif message_type == "charity_search":
        return "charity_search"
    elif message_type == "donor_search":
        return "agentic_rag"
    elif message_type == "volunteer_search":
        return "agentic_rag"
    return "logical"
