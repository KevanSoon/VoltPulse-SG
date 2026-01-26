"""
FastAPI endpoints for Ollama chat and donor/volunteer recommendation system.

Endpoints:
- /chat: Chat with Ollama model using LangGraph with memory
- /rag/search: Agentic RAG search (includes consumption data extraction)
- /singpass/mock: Mock Singpass data
- /ocr/process: Process images with OCR
- /consumption/extract: Extract structured consumption data from OCR documents
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

# Add app directory to path for local module imports
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import tempfile
import uuid

# Windows-specific fix for psycopg async compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Lazy imports for encoder/recommender (avoid import errors if deps missing)
encoder = None
vector_store = None
pool = None


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatResponse(BaseModel):
    response: str


class SingpassMockData(BaseModel):
    """Mock Singpass data for autofill."""

    name: str
    nric_masked: str
    email: str
    mobile: str
    registered_address: str
    planning_area: str
    organization_name: Optional[str] = None
    organization_uen: Optional[str] = None
    organization_type: Optional[str] = None


class OCRResult(BaseModel):
    """Single OCR detection result."""
    text: str
    box: List[List[float]]


class OCRResponse(BaseModel):
    """Response from OCR processing."""
    ocr_results: Dict[str, OCRResult]
    extracted_texts: List[str]
    embedding_stored: bool
    source_id: str


# ============================================================================
# Database & Encoder Setup
# ============================================================================

async def init_services():
    """Initialize encoder and database connection."""
    global encoder, vector_store, pool

    try:
        from encoders.sealion import SeaLionEncoder
        from recommender.vector_store import DonorVectorStore
        from psycopg_pool import AsyncConnectionPool

        # Initialize encoder (reads SEALION_ENDPOINT from env)
        encoder = SeaLionEncoder()

        # Build connection string from env vars
        db_host = os.getenv("SUPABASE_DB_HOST")
        db_port = os.getenv("SUPABASE_DB_PORT", "6543")
        db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        db_user = os.getenv("SUPABASE_DB_USER")
        db_password = os.getenv("SUPABASE_DB_PASSWORD")
        db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

        if db_host and db_user and db_password:
            conn_string = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                f"?sslmode={db_sslmode}"
            )
            pool = AsyncConnectionPool(
                conninfo=conn_string,
                max_size=10,
                kwargs={"autocommit": True, "prepare_threshold": None},
            )
            await pool.open()
            vector_store = DonorVectorStore(pool)
            print("[OK] Database connection pool initialized")
        else:
            print("[WARN] Database credentials not configured, vector store disabled")

        print("[OK] SeaLion encoder initialized")

    except Exception as e:
        print(f"[WARN] Service initialization error: {e}")
        print("  Some endpoints may not be available")


async def close_services():
    """Close database connections."""
    global pool
    if pool:
        await pool.close()
        print("[OK] Database connection pool closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    await init_services()
    await init_langgraph()
    yield
    await close_services()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="VoltPulse API",
    description="API for chat, RAG search, and OCR processing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# LangGraph Chat Setup
# ============================================================================

# Global graph instance (initialized at startup)
langgraph_chat = None


async def init_langgraph():
    """Initialize LangGraph with memory."""
    global langgraph_chat
    try:
        from graph.builder import build_graph_with_memory
        graph, _, _ = await build_graph_with_memory()
        langgraph_chat = graph
        print("[OK] LangGraph chat with memory initialized")
    except Exception as e:
        import traceback
        print(f"[WARN] LangGraph initialization error: {e}")
        traceback.print_exc()
        print("  /chat endpoint may not be available")


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/")
def root():
    """Root endpoint with service status."""
    return {
        "status": "healthy",
        "message": "VoltPulse API is running",
        "services": {
            "langgraph_chat": langgraph_chat is not None,
            "encoder": encoder is not None,
            "database": vector_store is not None,
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# Chat Endpoints
# ============================================================================

class ChatRequestWithMemory(BaseModel):
    message: str
    user_id: str = "default_user"
    thread_id: str = "default_thread"
    stream: bool = False


@app.post("/chat")
async def chat(request: ChatRequestWithMemory):
    """Chat with LangGraph-powered chatbot with memory."""
    if not langgraph_chat:
        raise HTTPException(
            status_code=503,
            detail="LangGraph chat not initialized. Check server logs."
        )

    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "user_id": request.user_id,
        }
    }

    try:
        if request.stream:
            async def generate_stream():
                async for chunk in langgraph_chat.astream(
                    {"messages": [{"role": "user", "content": request.message}]},
                    config,
                    stream_mode="values",
                ):
                    if chunk.get("messages"):
                        last_msg = chunk["messages"][-1]
                        if hasattr(last_msg, 'content') and last_msg.type == 'ai':
                            yield last_msg.content

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming: collect full response
            response_content = ""
            async for chunk in langgraph_chat.astream(
                {"messages": [{"role": "user", "content": request.message}]},
                config,
                stream_mode="values",
            ):
                if chunk.get("messages"):
                    last_msg = chunk["messages"][-1]
                    if hasattr(last_msg, 'content') and last_msg.type == 'ai':
                        response_content = last_msg.content

            return ChatResponse(response=response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Agentic RAG Endpoints
# ============================================================================

# Global agentic RAG agent instance
agentic_rag_agent = None


class AgenticRAGRequest(BaseModel):
    """Request for Agentic RAG search."""
    query: str = Field(..., description="Natural language query for search")
    max_iterations: int = Field(default=10, ge=1, le=20, description="Max tool call iterations")


class AgenticRAGResponse(BaseModel):
    """Response from Agentic RAG search."""
    response: str
    tool_calls: List[Dict[str, Any]]
    message_count: int


async def init_agentic_rag():
    """Initialize the Agentic RAG agent."""
    global agentic_rag_agent

    if encoder is None or vector_store is None:
        print("[WARN] Cannot initialize Agentic RAG: encoder or vector_store not available")
        return

    try:
        from agents.agentic_rag import AgenticRAGAgent
        from langchain_ollama import ChatOllama

        # Create LLM for the agent
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
            llm = ChatOllama(model="gpt-oss:120b-cloud")

        agentic_rag_agent = AgenticRAGAgent(llm, encoder, vector_store)
        print("[OK] Agentic RAG agent initialized")

    except Exception as e:
        import traceback
        print(f"[WARN] Agentic RAG initialization error: {e}")
        traceback.print_exc()


@app.post("/rag/search", response_model=AgenticRAGResponse)
async def agentic_rag_search(request: AgenticRAGRequest):
    """
    Agentic RAG search - the agent autonomously explores the vector store.

    The agent will:
    1. Analyze your query to understand what you're looking for
    2. Explore available categories in the database
    3. Perform semantic and/or filtered searches
    4. Iteratively refine results if needed
    5. Return detailed findings with reasoning
    """
    global agentic_rag_agent

    # Lazy initialization if not done yet
    if agentic_rag_agent is None:
        await init_agentic_rag()

    if agentic_rag_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agentic RAG not available. Ensure encoder and database are configured."
        )

    try:
        result = await agentic_rag_agent.search(request.query)

        return AgenticRAGResponse(
            response=result["response"],
            tool_calls=result["tool_calls"],
            message_count=result["message_count"]
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/tools")
async def list_rag_tools():
    """List available RAG tools and their descriptions."""
    from tools.rag_tools import RAG_TOOLS

    tools_info = []
    for tool in RAG_TOOLS:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
        })

    return {
        "tools": tools_info,
        "total": len(tools_info)
    }


@app.get("/rag/categories")
async def get_rag_categories():
    """Get available categories in the vector store for filtering."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    from tools.rag_tools import list_available_categories, set_rag_dependencies

    # Ensure dependencies are set
    if encoder and vector_store:
        set_rag_dependencies(encoder, vector_store)

    try:
        result = await list_available_categories.ainvoke({})
        import json
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Singpass Mock Data Endpoints
# ============================================================================

# Mock Singpass data for different organization profiles
MOCK_SINGPASS_PROFILES = {
    "org_001": SingpassMockData(
        name="Sarah Tan Wei Ling",
        nric_masked="S****567A",
        email="sarah.tan@example.org",
        mobile="+65 9123 4567",
        registered_address="123 Orchard Road, #12-01, Singapore 238867",
        planning_area="orchard",
        organization_name="Hearts of Hope Foundation",
        organization_uen="201912345K",
        organization_type="charity",
    ),
    "org_002": SingpassMockData(
        name="Ahmad bin Ibrahim",
        nric_masked="S****234B",
        email="ahmad.ibrahim@greensg.org",
        mobile="+65 9876 5432",
        registered_address="45 Jurong East Ave 1, #05-12, Singapore 609788",
        planning_area="jurong_east",
        organization_name="Green Singapore Initiative",
        organization_uen="201823456M",
        organization_type="ngo",
    ),
    "org_003": SingpassMockData(
        name="Lee Mei Hua",
        nric_masked="S****789C",
        email="meihua@eldercare.sg",
        mobile="+65 8765 4321",
        registered_address="78 Toa Payoh Lorong 1, #08-22, Singapore 310078",
        planning_area="toa_payoh",
        organization_name="ElderCare Singapore",
        organization_uen="200934567N",
        organization_type="social_enterprise",
    ),
}


@app.get("/singpass/mock/{profile_id}", response_model=SingpassMockData)
async def get_singpass_mock_data(profile_id: str):
    """
    Get mock Singpass data for autofill demonstration.

    Available profiles: org_001, org_002, org_003
    """
    if profile_id not in MOCK_SINGPASS_PROFILES:
        # Return a random profile if not found
        profile_id = "org_001"

    return MOCK_SINGPASS_PROFILES[profile_id]


@app.get("/singpass/mock", response_model=Dict[str, SingpassMockData])
async def list_singpass_mock_profiles():
    """List all available mock Singpass profiles."""
    return MOCK_SINGPASS_PROFILES


# ============================================================================
# OCR Endpoints
# ============================================================================

@app.post("/ocr/process", response_model=OCRResponse)
async def process_ocr(file: UploadFile = File(...)):
    """
    Process an uploaded image using PaddleOCR via Gradio client.

    1. Receives uploaded image file
    2. Saves temporarily and sends to PaddleOCR Gradio Space
    3. Extracts text from OCR results
    4. Generates embedding using SeaLion encoder
    5. Stores embedding in Supabase vector database

    Returns OCR results and extracted text for embedding.
    """
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/bmp", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {allowed_types}"
        )

    temp_file_path = None
    try:
        # Save uploaded file to temp location
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Call PaddleOCR via Gradio client
        from gradio_client import Client, handle_file

        client = Client("kevansoon/PaddleOCR")
        result = client.predict(
            img=handle_file(temp_file_path),
            lang="en",
            api_name="/predict"
        )

        # Parse OCR results - result is typically a list of [box, text, confidence]
        ocr_results = {}
        extracted_texts = []

        if isinstance(result, list):
            for idx, item in enumerate(result):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    # Format: [box_coords, text, confidence]
                    box = item[0] if len(item) > 0 else []
                    text = str(item[1]) if len(item) > 1 else ""

                    if text.strip():
                        ocr_results[str(idx)] = OCRResult(
                            text=text,
                            box=box if isinstance(box, list) else []
                        )
                        extracted_texts.append(text)
                elif isinstance(item, dict):
                    # Alternative dict format
                    text = item.get("text", item.get("label", ""))
                    box = item.get("box", item.get("bbox", []))

                    if text.strip():
                        ocr_results[str(idx)] = OCRResult(
                            text=text,
                            box=box if isinstance(box, list) else []
                        )
                        extracted_texts.append(text)

        # Clean up extracted texts - only keep actual words/phrases
        cleaned_texts = []
        for text in extracted_texts:
            # Filter out very short strings or purely numeric strings that aren't meaningful
            cleaned = text.strip()
            if len(cleaned) > 0:
                cleaned_texts.append(cleaned)

        # Generate unique source ID for this OCR result
        source_id = f"ocr_{uuid.uuid4().hex[:12]}"

        # Combine extracted texts for embedding
        combined_text = " ".join(cleaned_texts)

        embedding_stored = False
        if combined_text.strip():
            # Generate embedding using SeaLion encoder
            embedding = await encoder.encode(combined_text)

            # Store in vector database
            form_data = {
                "source_type": "ocr",
                "original_filename": file.filename,
                "extracted_texts": cleaned_texts,
                "text_count": len(cleaned_texts),
                "combined_text": combined_text
            }

            await vector_store.store_embedding(
                form_id=source_id,
                form_type="ocr",
                embedding=embedding,
                form_data=form_data
            )
            embedding_stored = True
            print(f"[OK] OCR embedding stored: {source_id} with {len(cleaned_texts)} text items")

        return OCRResponse(
            ocr_results=ocr_results,
            extracted_texts=cleaned_texts,
            embedding_stored=embedding_stored,
            source_id=source_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass


@app.get("/ocr/results/{source_id}")
async def get_ocr_result(source_id: str):
    """
    Retrieve a stored OCR result by its source ID.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    result = await vector_store.get_embedding(source_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"OCR result {source_id} not found")

    return {
        "id": result.id,
        "form_type": result.form_type,
        "form_data": result.form_data
    }


# ============================================================================
# Consumption Data Extraction Endpoints
# ============================================================================

class ConsumptionExtractRequest(BaseModel):
    """Request for consumption data extraction."""
    source_id: str = Field(..., description="The OCR document source ID")


class ConsumptionExtractResponse(BaseModel):
    """Response with extracted consumption data."""
    source_id: str
    original_filename: Optional[str] = None
    extraction_successful: bool
    consumption_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@app.post("/consumption/extract", response_model=ConsumptionExtractResponse)
async def extract_consumption(request: ConsumptionExtractRequest):
    """
    Extract structured consumption data from a stored OCR document.

    This endpoint extracts Singapore electricity bill information including:
    - kWh consumption
    - Total cost in SGD
    - Billing period dates
    - Provider name (SP Services, Geneco, etc.)
    - Tariff breakdown (if available)

    The extraction uses an LLM to parse the OCR text.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Retrieve the OCR document
        result = await vector_store.get_embedding(request.source_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"OCR document '{request.source_id}' not found"
            )

        # Check if it's an OCR document
        form_data = result.form_data or {}
        if form_data.get("source_type") != "ocr":
            raise HTTPException(
                status_code=400,
                detail=f"Document '{request.source_id}' is not an OCR result"
            )

        # Get OCR text
        ocr_text = form_data.get("combined_text", "")
        if not ocr_text:
            raise HTTPException(
                status_code=400,
                detail=f"No OCR text found in document '{request.source_id}'"
            )

        # Initialize extractor with LLM
        from services.consumption_extractor import ConsumptionExtractor
        from langchain_ollama import ChatOllama

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
            llm = ChatOllama(model="gpt-oss:120b-cloud")

        extractor = ConsumptionExtractor(llm)

        # Extract consumption data
        extraction = await extractor.extract_with_retry(ocr_text)

        return ConsumptionExtractResponse(
            source_id=request.source_id,
            original_filename=form_data.get("original_filename"),
            extraction_successful=extraction.extraction_confidence > 0.3,
            consumption_data=extraction.model_dump(exclude={"raw_ocr_text"}),
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ConsumptionExtractResponse(
            source_id=request.source_id,
            extraction_successful=False,
            error=str(e),
        )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Windows-specific fix: must be set before uvicorn starts its event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(app, host="0.0.0.0", port=7860)
