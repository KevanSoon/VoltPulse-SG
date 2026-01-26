import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool
from langchain_ollama import ChatOllama

from .state import State
from .router import router
from agents.therapist import TherapistAgent
from agents.logical import LogicalAgent
from agents.classifier import create_classifier
from agents.charity_search import CharitySearchAgent
from agents.agentic_rag import AgenticRAGAgent
from encoders.sealion import SeaLionEncoder
from recommender.vector_store import DonorVectorStore


def create_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    db_host = os.getenv("SUPABASE_DB_HOST", "localhost")
    db_port = os.getenv("SUPABASE_DB_PORT", "6543")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_user = os.getenv("SUPABASE_DB_USER", "postgres")
    db_password = os.getenv("SUPABASE_DB_PASSWORD", "")
    db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

    return (
        f"postgres://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
        f"?sslmode={db_sslmode}"
    )


def create_async_pool() -> AsyncConnectionPool:
    """Create AsyncConnectionPool with proper settings."""
    return AsyncConnectionPool(
        conninfo=create_connection_string(),
        max_size=20,
        kwargs={
            "autocommit": True,
            "prepare_threshold": None,
        }
    )


async def build_graph_with_memory():
    """Build the graph with Supabase-backed checkpointer and store."""

    # Create async connection pool
    pool = create_async_pool()
    await pool.open()

    # Create checkpointer and store from the pool
    checkpointer = AsyncPostgresSaver(pool)
    store = AsyncPostgresStore(pool)

    # Setup tables for store and checkpointer
    print("\n[Setup] Setting up LangGraph store and checkpointer tables...")
    await checkpointer.setup()
    await store.setup()
    print("[OK] Store and checkpointer tables created!\n")

    # Use Ollama cloud with API key authentication
    api_key = os.getenv('OLLAMA_API_KEY')
    if api_key:
        llm = ChatOllama(
            model="gpt-oss:120b",
            base_url="https://ollama.com",
            client_kwargs={
                "headers": {"Authorization": f"Bearer {api_key}"}
            }
        )
    else:
        # Fallback to local Ollama if no API key
        llm = ChatOllama(model="gpt-oss:120b-cloud")

    # Initialize encoder and vector store for Agentic RAG
    encoder = None
    vector_store = None
    try:
        sealion_endpoint = os.getenv("SEALION_ENDPOINT")
        if sealion_endpoint:
            encoder = SeaLionEncoder(endpoint_url=sealion_endpoint)
            vector_store = DonorVectorStore(pool)
            print("[OK] Agentic RAG initialized with SeaLion encoder\n")
    except Exception as e:
        print(f"[WARN] Agentic RAG not available: {e}\n")

    # Create Agentic RAG agent
    agentic_rag_agent = AgenticRAGAgent(llm, encoder, vector_store)

    # Build the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("classifier", create_classifier(llm))
    graph_builder.add_node("therapist", TherapistAgent(llm))
    graph_builder.add_node("logical", LogicalAgent(llm))
    graph_builder.add_node("charity_search", CharitySearchAgent(llm))
    graph_builder.add_node("agentic_rag", agentic_rag_agent)

    graph_builder.add_edge(START, "classifier")
    graph_builder.add_conditional_edges(
        "classifier",
        router,
        {
            "therapist": "therapist",
            "logical": "logical",
            "charity_search": "charity_search",
            "agentic_rag": "agentic_rag"
        }
    )
    graph_builder.add_edge("therapist", END)
    graph_builder.add_edge("logical", END)
    graph_builder.add_edge("charity_search", END)
    graph_builder.add_edge("agentic_rag", END)

    # Compile with store and checkpointer
    graph = graph_builder.compile(
        checkpointer=checkpointer,
        store=store,
    )

    return graph, store, checkpointer
