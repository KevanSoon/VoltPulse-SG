"""
FastAPI endpoints for Ollama chat and consumption data management.

Endpoints:
- /chat: Chat with Ollama model using LangGraph with memory
- /rag/search: Agentic RAG search for consumption data
- /singpass/mock: Mock Singpass data
- /ocr/process: Process images with OCR
- /consumption/extract: Extract structured consumption data from OCR documents
- /retailers/*: Climate Voucher retailer search and recommendations
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

# Analytics module import
from analytics.router import router as analytics_router, set_vector_store as set_analytics_vector_store

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


class OCRResponse(BaseModel):
    """Response from OCR/Vision processing."""
    extracted_texts: List[str]
    embedding_stored: bool
    source_id: str
    extraction_data: Optional[Dict[str, Any]] = None
    extraction_confidence: float = 0.0
    diagnosis: Optional[Dict[str, Any]] = None


# ============================================================================
# Database & Encoder Setup
# ============================================================================

async def init_services():
    """Initialize encoder and database connection."""
    global encoder, vector_store, pool

    try:
        from encoders.sealion import SeaLionEncoder
        from recommender.vector_store import VectorStore
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
            vector_store = VectorStore(pool)
            # Set vector store for analytics module
            set_analytics_vector_store(vector_store)
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

# Register analytics router
app.include_router(analytics_router)


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
    Process an uploaded utility bill image using OpenAI Vision.

    1. Receives uploaded image file
    2. Uses OpenAI Vision API to extract ALL text AND chart data
    3. Generates embedding using SeaLion encoder
    4. Stores embedding and extraction data in Supabase vector database

    Returns extracted data including consumption trends from bar charts.
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

    try:
        # Read file content
        image_bytes = await file.read()

        # Use OpenAI Vision to extract all data including charts
        from services.vision_extractor import VisionExtractor

        vision_extractor = VisionExtractor()
        extraction = await vision_extractor.extract_with_retry(
            image_bytes=image_bytes,
            filename=file.filename
        )

        # Build extracted texts list from extraction for embedding
        extracted_texts = []

        if extraction.customer_name:
            extracted_texts.append(f"Customer: {extraction.customer_name}")
        if extraction.premise_address:
            extracted_texts.append(f"Address: {extraction.premise_address}")
        if extraction.provider_name:
            extracted_texts.append(f"Provider: {extraction.provider_name}")
        if extraction.consumption_kwh:
            extracted_texts.append(f"Electricity: {extraction.consumption_kwh} kWh")
        if extraction.gas_usage_kwh:
            extracted_texts.append(f"Gas: {extraction.gas_usage_kwh} kWh")
        if extraction.water_usage_cu_m:
            extracted_texts.append(f"Water: {extraction.water_usage_cu_m} Cu M")
        if extraction.total_amount:
            extracted_texts.append(f"Total: S${extraction.total_amount}")

        # Add consumption trend summaries
        for trend in extraction.consumption_trends:
            if trend.service_type and trend.monthly_data:
                values = [f"{m.month}:{m.value}" for m in trend.monthly_data if m.month and m.value]
                if values:
                    extracted_texts.append(f"{trend.service_type} trend: {', '.join(values)}")

        # Generate unique source ID
        source_id = f"vision_{uuid.uuid4().hex[:12]}"

        # Combine texts for embedding
        combined_text = " ".join(extracted_texts)

        # Get full extraction data as dict (excluding raw_ocr_text for storage)
        extraction_dict = extraction.model_dump(exclude={"raw_ocr_text"})

        embedding_stored = False
        if combined_text.strip():
            # Generate embedding using SeaLion encoder
            embedding = await encoder.encode(combined_text)

            # Store in vector database with full extraction data
            form_data = {
                "source_type": "vision",
                "original_filename": file.filename,
                "extracted_texts": extracted_texts,
                "text_count": len(extracted_texts),
                "combined_text": combined_text,
                "extraction_data": extraction_dict
            }

            # Generate diagnosis for the extracted bill data
            from services.bill_diagnosis import BillDiagnosisService

            diagnosis_service = BillDiagnosisService()
            diagnosis_result = await diagnosis_service.diagnose(extraction)
            diagnosis_dict = diagnosis_result.model_dump()

            # Add diagnosis to form_data
            form_data["diagnosis"] = diagnosis_dict

            await vector_store.store_embedding(
                form_id=source_id,
                form_type="utility_bill",
                embedding=embedding,
                form_data=form_data
            )
            embedding_stored = True
            print(f"[OK] Vision extraction stored: {source_id}")
            print(f"    - Confidence: {extraction.extraction_confidence:.0%}")
            print(f"    - Consumption trends: {len(extraction.consumption_trends)} services")
            print(f"    - Health score: {diagnosis_result.overall_health_score:.0f}/100 ({diagnosis_result.health_grade})")

        # Generate diagnosis even if embedding not stored (for response)
        diagnosis_dict = None
        if 'diagnosis_result' not in locals():
            from services.bill_diagnosis import BillDiagnosisService
            diagnosis_service = BillDiagnosisService()
            diagnosis_result = await diagnosis_service.diagnose(extraction)
            diagnosis_dict = diagnosis_result.model_dump()
        else:
            diagnosis_dict = diagnosis_result.model_dump()

        return OCRResponse(
            extracted_texts=extracted_texts,
            embedding_stored=embedding_stored,
            source_id=source_id,
            extraction_data=extraction_dict,
            extraction_confidence=extraction.extraction_confidence,
            diagnosis=diagnosis_dict
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
    Retrieve structured consumption data from a stored vision-processed document.

    This endpoint returns pre-extracted Singapore utility bill information including:
    - Electricity, Gas, Water consumption
    - Total cost in SGD
    - Billing period dates
    - Provider names
    - Consumption trends from bar charts

    Note: Extraction is done at upload time using OpenAI Vision.
    This endpoint retrieves the already-extracted data.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Retrieve the document
        result = await vector_store.get_embedding(request.source_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{request.source_id}' not found"
            )

        form_data = result.form_data or {}
        source_type = form_data.get("source_type", "")

        # Check if extraction data exists (from vision processing)
        extraction_data = form_data.get("extraction_data")

        if extraction_data:
            # Vision-processed document - return pre-extracted data
            confidence = extraction_data.get("extraction_confidence", 0.0)
            return ConsumptionExtractResponse(
                source_id=request.source_id,
                original_filename=form_data.get("original_filename"),
                extraction_successful=confidence > 0.3,
                consumption_data=extraction_data,
            )

        # Legacy OCR document - try to extract using LLM
        if source_type == "ocr":
            ocr_text = form_data.get("combined_text", "")
            if not ocr_text:
                raise HTTPException(
                    status_code=400,
                    detail=f"No text found in document '{request.source_id}'"
                )

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
            extraction = await extractor.extract_with_retry(ocr_text)

            return ConsumptionExtractResponse(
                source_id=request.source_id,
                original_filename=form_data.get("original_filename"),
                extraction_successful=extraction.extraction_confidence > 0.3,
                consumption_data=extraction.model_dump(exclude={"raw_ocr_text"}),
            )

        raise HTTPException(
            status_code=400,
            detail=f"Document '{request.source_id}' has no extraction data"
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
# Climate Voucher Retailer Endpoints
# ============================================================================

class RetailerSearchRequest(BaseModel):
    """Request for Climate Voucher retailer search."""
    query: str = Field(..., description="Natural language search query")
    product_category: Optional[str] = Field(None, description="Product filter (e.g., refrigerators, air_conditioners)")
    planning_area: Optional[str] = Field(None, description="Singapore planning area filter")
    limit: int = Field(10, ge=1, le=50)


class RetailerLoadRequest(BaseModel):
    """Request to load retailer data."""
    use_sample_data: bool = Field(True, description="Use sample data (True) or full PDF parse (False)")


# Global flag for retailer tools initialization
_retailer_tools_initialized = False


async def init_retailer_tools():
    """Initialize Climate Voucher retailer tools."""
    global _retailer_tools_initialized

    if _retailer_tools_initialized:
        return True

    if encoder is None or vector_store is None:
        print("[WARN] Cannot initialize retailer tools: encoder or vector_store not available")
        return False

    try:
        from tools.retailer_tools import set_retailer_dependencies

        set_retailer_dependencies(encoder, vector_store)
        _retailer_tools_initialized = True
        print("[OK] Climate Voucher retailer tools initialized")

        return True

    except Exception as e:
        import traceback
        print(f"[WARN] Retailer tools initialization error: {e}")
        traceback.print_exc()
        return False


@app.post("/retailers/load")
async def load_retailer_data(request: RetailerLoadRequest):
    """
    Load Climate Voucher retailer data into the vector store.

    This embeds retailer information using SeaLion and stores it for
    semantic search. Run this once to populate the retailer database.
    """
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        from services.retailer_loader import load_retailers_to_vector_store, SAMPLE_RETAILERS_DATA

        # Load retailers
        if request.use_sample_data:
            result = await load_retailers_to_vector_store(
                encoder=encoder,
                vector_store=vector_store,
                retailers_data=SAMPLE_RETAILERS_DATA
            )
        else:
            # Try to parse full PDF data
            from services.pdf_retailer_parser import get_full_retailer_data
            full_data = get_full_retailer_data()
            result = await load_retailers_to_vector_store(
                encoder=encoder,
                vector_store=vector_store,
                retailers_data=full_data
            )

        return {
            "status": "success",
            "message": f"Loaded {result['loaded']} retailers into vector store",
            "details": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retailers/load-pdf")
async def load_retailers_from_pdf(file: UploadFile = File(...)):
    """
    Upload and load Climate Voucher retailers PDF directly.

    This endpoint:
    1. Receives the PDF file
    2. Parses all retailer data using pdfplumber
    3. Embeds each retailer using SeaLion
    4. Stores in the vector database for semantic search

    The PDF should be the official NEA Climate Vouchers retailer list.
    """
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF. Please upload the Climate Vouchers retailer PDF."
        )

    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="pdfplumber not installed. Run: pip install pdfplumber"
        )

    try:
        import tempfile
        import os as os_module

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Parse PDF
            from scripts.load_retailers_from_pdf import parse_pdf_to_retailers
            retailers_data = parse_pdf_to_retailers(tmp_path)

            if not retailers_data:
                raise HTTPException(
                    status_code=400,
                    detail="No retailers found in PDF. Ensure this is the correct Climate Vouchers retailer list."
                )

            # Load into vector store
            from services.retailer_loader import load_retailers_to_vector_store
            result = await load_retailers_to_vector_store(
                encoder=encoder,
                vector_store=vector_store,
                retailers_data=retailers_data
            )

            return {
                "status": "success",
                "message": f"Loaded {result['loaded']} retailers from PDF",
                "filename": file.filename,
                "details": result
            }

        finally:
            # Clean up temp file
            os_module.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retailers/search")
async def search_retailers(request: RetailerSearchRequest):
    """
    Search for Climate Voucher participating retailers.

    Use natural language to find retailers where you can spend your
    Singapore Climate Vouchers on energy-efficient appliances.
    """
    # Ensure retailer tools are initialized
    await init_retailer_tools()

    if not _retailer_tools_initialized:
        raise HTTPException(
            status_code=503,
            detail="Retailer tools not available. Ensure encoder and database are configured."
        )

    try:
        from tools.retailer_tools import search_climate_voucher_retailers
        import json

        # Call the tool
        result = await search_climate_voucher_retailers.ainvoke({
            "query": request.query,
            "product_category": request.product_category,
            "planning_area": request.planning_area,
            "limit": request.limit
        })

        return json.loads(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retailers/products/{product}")
async def find_retailers_by_product(product: str, limit: int = 15):
    """
    Find all retailers selling a specific Climate Voucher eligible product.

    Product options: refrigerators, air_conditioners, dc_fans, led_lights,
    washing_machines, water_closets, sink_bib_taps_mixers, basin_taps_mixers,
    shower_taps_mixers, heat_pump_water_heaters

    Common aliases work too: fridge, aircon, fan, light, washer, toilet, tap, etc.
    """
    await init_retailer_tools()

    if not _retailer_tools_initialized:
        raise HTTPException(
            status_code=503,
            detail="Retailer tools not available."
        )

    try:
        from tools.retailer_tools import find_retailers_by_product
        import json

        result = await find_retailers_by_product.ainvoke({
            "product": product,
            "limit": limit
        })

        return json.loads(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retailers/energy-ratings/{product_type}")
async def get_energy_rating_info(product_type: str):
    """
    Get information about energy efficiency ratings for a product type.

    Explains Singapore's energy label system and tick ratings for
    Climate Voucher eligible appliances.
    """
    await init_retailer_tools()

    try:
        from tools.retailer_tools import get_energy_rating_info
        import json

        result = await get_energy_rating_info.ainvoke({
            "product_type": product_type
        })

        return json.loads(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retailers/tools")
async def list_retailer_tools():
    """List available Climate Voucher retailer tools."""
    from tools.retailer_tools import RETAILER_TOOLS

    tools_info = []
    for tool in RETAILER_TOOLS:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
        })

    return {
        "tools": tools_info,
        "total": len(tools_info),
        "total_tools": len(tools_info)
    }


# ============================================================================
# ROI Calculator Endpoints
# ============================================================================

class ROICalculationRequest(BaseModel):
    """Request for ROI calculation."""
    product_type: str = Field(..., description="Type of appliance (e.g., 'air_conditioners', 'refrigerators')")
    current_rating: int = Field(0, ge=0, le=5, description="Current appliance tick rating (0 for unknown/old)")
    new_rating: int = Field(..., ge=1, le=5, description="New appliance tick rating")
    product_price: float = Field(..., gt=0, description="Price of new appliance in SGD")
    apply_voucher: bool = Field(True, description="Whether to apply Climate Voucher")
    custom_voucher_amount: Optional[float] = Field(None, description="Custom voucher amount if different from $300")


@app.post("/retailers/roi/calculate")
async def calculate_roi(request: ROICalculationRequest):
    """
    Calculate ROI for an appliance upgrade with Climate Voucher.

    Returns detailed analysis including:
    - Annual energy and cost savings
    - Payback period
    - 5-year and 10-year net benefits
    - Voucher eligibility status
    """
    from services.roi_calculator import ROICalculator

    try:
        calculator = ROICalculator()
        result = calculator.calculate(
            product_type=request.product_type,
            current_rating=request.current_rating,
            new_rating=request.new_rating,
            product_price=request.product_price,
            apply_voucher=request.apply_voucher,
            custom_voucher_amount=request.custom_voucher_amount
        )
        return result.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retailers/roi/products")
async def list_roi_products():
    """
    List all product types supported by the ROI calculator.

    Returns information about each product including tick rating ranges
    and typical price ranges.
    """
    from services.roi_calculator import ROICalculator

    calculator = ROICalculator()
    return {
        "products": calculator.get_all_products(),
        "voucher_value": calculator.voucher_value,
        "electricity_rate": calculator.electricity_rate
    }


@app.get("/retailers/roi/product/{product_type}")
async def get_roi_product_info(product_type: str):
    """
    Get detailed information about a specific product type for ROI calculation.
    """
    from services.roi_calculator import ROICalculator

    calculator = ROICalculator()
    info = calculator.get_product_info(product_type)

    if "error" in info:
        raise HTTPException(status_code=404, detail=info["error"])

    return info


@app.get("/retailers/roi/recommendations/{source_id}")
async def get_roi_recommendations(source_id: str, budget_max: float = 2000.0):
    """
    Get personalized appliance upgrade recommendations based on a user's bill diagnosis.

    Uses the diagnosis from a stored OCR result to recommend appliances
    that would have the highest impact on the user's energy bills.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Get the stored OCR result
    result = await vector_store.get_embedding(source_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"OCR result {source_id} not found")

    # Get diagnosis from stored data
    diagnosis_data = result.form_data.get("diagnosis")
    if not diagnosis_data:
        raise HTTPException(status_code=404, detail="No diagnosis found for this bill. Please re-upload.")

    from services.roi_calculator import ROICalculator
    from models.diagnosis import DiagnosisResult

    try:
        # Reconstruct diagnosis object
        diagnosis = DiagnosisResult(**diagnosis_data)

        calculator = ROICalculator()
        recommendations = calculator.recommend_from_diagnosis(diagnosis, budget_max)

        return {
            "source_id": source_id,
            "budget_max": budget_max,
            "recommendations": [r.model_dump() for r in recommendations],
            "total_recommendations": len(recommendations)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Windows-specific fix: must be set before uvicorn starts its event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(app, host="0.0.0.0", port=7860)
