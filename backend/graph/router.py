from .state import State


def router(state: State):
    """Route to appropriate agent based on message type."""
    message_type = state.get("message_type", "logical")

    # Route to Agentic RAG for consumption and Climate Voucher queries
    agentic_rag_types = {
        "consumption_query",
        "utility_search",
        "bill_analysis",
        "climate_voucher",
    }

    if message_type in agentic_rag_types:
        print(f"[Router] Routing to 'agentic_rag' ({message_type})")
        return "agentic_rag"

    print(f"[Router] Routing to 'logical' (default)")
    return "logical"
