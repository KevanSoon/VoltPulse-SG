from .state import State


def router(state: State):
    """Route to appropriate agent based on message type."""
    message_type = state.get("message_type", "logical")
    
    if message_type == "consumption_query":
        print(f"[Router] Routing to 'agentic_rag' (consumption_query)")
        return "agentic_rag"
    elif message_type == "utility_search":
        print(f"[Router] Routing to 'agentic_rag' (utility_search)")
        return "agentic_rag"
    elif message_type == "bill_analysis":
        print(f"[Router] Routing to 'agentic_rag' (bill_analysis)")
        return "agentic_rag"
    
    print(f"[Router] Routing to 'logical' (default)")
    return "logical"
