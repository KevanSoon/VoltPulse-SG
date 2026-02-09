from typing import Literal
from pydantic import BaseModel, Field
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig


class MessageClassifier(BaseModel):
    """Classification result for routing messages to Agentic RAG with tool hints."""
    message_type: Literal[
        "consumption_info",
        "energy_rating_info",
        "appliance_roi",
        "web_search",
        "retailer_search",
    ] = Field(
        ...,
        description="Classify message into one of 5 tool categories for Agentic RAG."
    )


async def classify_message(state: dict, config: RunnableConfig, *, store: BaseStore, llm) -> dict:
    """Classify user message into one of 5 tool categories.

    All categories route to the Agentic RAG agent, which uses the classification
    as a hint for which tool to invoke first.

    Args:
        state: Graph state containing messages
        config: Runtime config with user_id, thread_id
        store: Memory store (required by graph but not used here)
        llm: Language model instance

    Returns:
        Dict with message_type for tool hint routing
    """
    last_message = state["messages"][-1]
    print(f"\n[Classifier] Classifying message: '{last_message.content[:100]}...'" if len(str(last_message.content)) > 100 else f"\n[Classifier] Classifying message: '{last_message.content}'")
    
    classifier_llm = llm.with_structured_output(MessageClassifier)

    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """Classify the user message into one of these 5 categories. Each category maps to a specific tool the agent will use.

Respond ONLY with valid JSON in this exact format:
{"message_type": "TYPE"}

Where TYPE is one of:

- 'consumption_info': Questions about the user's utility bills, electricity/water/gas usage, kWh consumption, energy costs, billing periods, comparing bills, consumption summaries, meter readings, daily averages
- 'energy_rating_info': Questions about energy efficiency ratings, tick ratings, energy labels, what ticks mean, minimum ratings for Climate Vouchers, comparing energy ratings between products
- 'appliance_roi': Questions about cost savings from upgrading appliances, payback period, return on investment, whether an appliance upgrade is worth it, annual savings calculations, energy cost comparisons between old and new appliances
- 'web_search': Questions seeking specific product recommendations, reviews, buying guides, best models of appliances, comparisons between specific brands/models, latest deals or promotions on appliances
- 'retailer_search': Questions about where to buy appliances, which shops/stores sell specific products, Climate Voucher participating retailers, finding retailers by location or product, store addresses, outlet locations

Examples:
- "What was my electricity consumption?" → consumption_info
- "Show me my utility bills" → consumption_info
- "How much kWh did I use last month?" → consumption_info
- "Summarize my energy usage" → consumption_info
- "How much did I pay for electricity?" → consumption_info
- "What is a 4-tick rating?" → energy_rating_info
- "Explain energy labels for aircon" → energy_rating_info
- "What's the minimum tick for climate voucher?" → energy_rating_info
- "Is upgrading my aircon worth it?" → appliance_roi
- "How much can I save with a 5-tick fridge?" → appliance_roi
- "Calculate savings for new washing machine" → appliance_roi
- "Recommend me an energy efficient aircon" → web_search
- "Best inverter aircon 2025" → web_search
- "What's a good fridge for a 4-room HDB?" → web_search
- "Where can I use my climate voucher?" → retailer_search
- "Which shops sell fridges with climate voucher?" → retailer_search
- "Where to buy LED lights near Bedok?" → retailer_search
- "Gain City locations" → retailer_search"""
        },
        {
            "role": "user",
            "content": last_message.content
        }
    ])
    
    tool_map = {
        "consumption_info": "get_user_consumption_info",
        "energy_rating_info": "get_energy_rating_info",
        "appliance_roi": "calculate_appliance_roi",
        "web_search": "search_appliance_recommendations",
        "retailer_search": "find_retailers_by_product",
    }
    print(f"[Classifier] Category: '{result.message_type}' → Tool hint: '{tool_map.get(result.message_type)}' → Agentic RAG")
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
