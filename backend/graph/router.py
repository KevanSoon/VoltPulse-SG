from .state import State


def router(state: State):
    """Route all messages to agentic_rag agent.

    The classifier categorizes into 5 tool-hint categories, but all
    messages are handled by the Agentic RAG agent which selects the
    appropriate tool based on the classification.
    """
    message_type = state.get("message_type", "retailer_search")
    print(f"[Router] Routing to 'agentic_rag' (category: {message_type})")
    return "agentic_rag"
