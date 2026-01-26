"""
FastAPI endpoints for Ollama chat and donor/volunteer recommendation system.

Endpoints:
- /chat: Chat with Ollama model using LangGraph with memory
- /donors/register: Register a donor and generate embedding
- /volunteers/register: Register a volunteer and generate embedding
- /donors/recommend: Find similar donors based on query
- /volunteers/recommend: Find similar volunteers based on query
- /forms/{id}: Get/Delete a stored form
- /forms/stats: Get form counts by type
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
gis_recommender = None


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatResponse(BaseModel):
    response: str


class DonorFormRequest(BaseModel):
    """Donor registration form."""
    id: str = Field(..., description="Unique identifier for the donor")
    name: str = Field(..., description="Donor name")
    donor_type: str = Field(..., description="Type: individual, corporate, foundation")
    country: str = Field(..., description="ASEAN country code (SG, MY, TH, VN, ID, PH, etc.)")
    preferred_language: str = Field(..., description="Primary language code")
    causes: List[str] = Field(default_factory=list, description="Interested causes")
    donation_frequency: Optional[str] = Field(None, description="one-time, monthly, quarterly, annual")
    amount_range: Optional[str] = Field(None, description="Preferred donation range")
    bio: Optional[str] = Field(None, description="Donor background")
    motivation: Optional[str] = Field(None, description="Why they want to donate")


class VolunteerFormRequest(BaseModel):
    """Volunteer registration form."""
    id: str = Field(..., description="Unique identifier for the volunteer")
    name: str = Field(..., description="Volunteer name")
    volunteer_type: str = Field(..., description="Type: regular, event_based, skilled")
    country: str = Field(..., description="ASEAN country code")
    preferred_language: str = Field(..., description="Primary language code")
    languages_spoken: List[str] = Field(default_factory=list, description="All languages spoken")
    skills: List[str] = Field(default_factory=list, description="Professional/technical skills")
    availability: str = Field(..., description="weekends, evenings, flexible, full_time")
    causes: List[str] = Field(default_factory=list, description="Interested causes")
    experience: Optional[str] = Field(None, description="Prior volunteer experience")
    goals: Optional[str] = Field(None, description="What they hope to achieve")


class RecommendRequest(BaseModel):
    """Request for recommendations based on a query form."""
    # Either provide a form_id to use existing embedding, or provide form data
    form_id: Optional[str] = Field(None, description="Existing form ID to use as query")
    # Or provide inline form data
    country: Optional[str] = None
    preferred_language: Optional[str] = None
    causes: List[str] = Field(default_factory=list)
    bio: Optional[str] = None
    motivation: Optional[str] = None
    # Search options
    limit: int = Field(default=10, ge=1, le=50)
    country_filter: Optional[str] = None
    exclude_ids: List[str] = Field(default_factory=list)


class FormResponse(BaseModel):
    """Response for form operations."""
    id: str
    form_type: str
    message: str
    embedding_dimension: Optional[int] = None


class ClientProfileRequest(BaseModel):
    """Client profile with spatial and behavioral data."""

    user_id: str
    coordinates: List[float] = Field(
        default=[1.3521, 103.8198], description="[lat, lng]"
    )
    planning_area: str = Field(default="central", description="Singapore planning area")
    housing_type: str = Field(
        default="hdb_4_room", description="Housing type for income proxy"
    )
    interests: List[str] = Field(default_factory=list)
    causes: List[str] = Field(default_factory=list)
    preferred_language: str = Field(default="en")
    is_donor: bool = False
    total_donated: float = 0.0
    donation_count: int = 0
    age_range: Optional[str] = None


class LookalikeRequest(BaseModel):
    """Request for lookalike client search."""

    seed_causes: List[str] = Field(..., description="Causes to find lookalikes for")
    seed_interests: List[str] = Field(default_factory=list)
    planning_area_filter: Optional[str] = Field(
        None, description="Geo-fence by planning area"
    )
    housing_type_filter: Optional[List[str]] = Field(
        None, description="Filter by housing types"
    )
    limit: int = Field(default=50, ge=1, le=200)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_geojson: bool = Field(
        default=True, description="Include GeoJSON for mapping"
    )


class ScoredClientResponse(BaseModel):
    """Single scored client result."""

    user_id: str
    planning_area: str
    housing_type: str
    causes: List[str]
    interests: List[str]
    is_donor: bool
    final_score: float
    vector_similarity: float
    spatial_proxy: float
    proximity: float
    coordinates: Optional[List[float]] = None  # Reduced precision


class LookalikeResponse(BaseModel):
    """Response containing lookalike clients with optional GeoJSON."""

    seed_causes: List[str]
    total_found: int
    tiers: Dict[str, List[ScoredClientResponse]]
    geojson: Optional[Dict[str, Any]] = None


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


class RecommendationResult(BaseModel):
    """Single recommendation result."""
    id: str
    form_type: str
    score: float
    distance: float
    form_data: Dict[str, Any]


class RecommendResponse(BaseModel):
    """Response containing recommendations."""
    query_id: Optional[str]
    results: List[RecommendationResult]
    total_found: int


class StatsResponse(BaseModel):
    """Form statistics response."""
    donor: int
    volunteer: int
    total: int


# ============================================================================
# Database & Encoder Setup
# ============================================================================

async def init_services():
    """Initialize encoder and database connection."""
    global encoder, vector_store, pool, gis_recommender

    try:
        from encoders.sealion import SeaLionEncoder
        from recommender.vector_store import DonorVectorStore
        from recommender.gis_recommender import GISRecommender
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
            gis_recommender = GISRecommender(vector_store=vector_store, encoder=encoder)
            print("[OK] Database connection pool initialized")
            print("[OK] GIS Recommender initialized")
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
    title="Donor Recommendation API",
    description="API for chat, donor/volunteer registration, and recommendations",
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
# Helper Functions
# ============================================================================

def donor_form_to_text(form: DonorFormRequest) -> str:
    """Convert donor form to encoding text."""
    parts = [
        f"Donor type: {form.donor_type}",
        f"Country: {form.country}",
        f"Preferred language: {form.preferred_language}",
    ]
    if form.causes:
        parts.append(f"Causes interested in: {', '.join(form.causes)}")
    if form.donation_frequency:
        parts.append(f"Donation frequency: {form.donation_frequency}")
    if form.amount_range:
        parts.append(f"Amount range: {form.amount_range}")
    if form.bio:
        parts.append(f"Bio: {form.bio}")
    if form.motivation:
        parts.append(f"Motivation: {form.motivation}")
    return "\n".join(parts)


def volunteer_form_to_text(form: VolunteerFormRequest) -> str:
    """Convert volunteer form to encoding text."""
    parts = [
        f"Volunteer type: {form.volunteer_type}",
        f"Country: {form.country}",
        f"Preferred language: {form.preferred_language}",
    ]
    if form.languages_spoken:
        parts.append(f"Languages spoken: {', '.join(form.languages_spoken)}")
    if form.skills:
        parts.append(f"Skills: {', '.join(form.skills)}")
    parts.append(f"Availability: {form.availability}")
    if form.causes:
        parts.append(f"Causes interested in: {', '.join(form.causes)}")
    if form.experience:
        parts.append(f"Experience: {form.experience}")
    if form.goals:
        parts.append(f"Goals: {form.goals}")
    return "\n".join(parts)


def recommend_request_to_text(req: RecommendRequest) -> str:
    """Convert recommendation request to encoding text."""
    parts = []
    if req.country:
        parts.append(f"Country: {req.country}")
    if req.preferred_language:
        parts.append(f"Preferred language: {req.preferred_language}")
    if req.causes:
        parts.append(f"Causes interested in: {', '.join(req.causes)}")
    if req.bio:
        parts.append(f"Bio: {req.bio}")
    if req.motivation:
        parts.append(f"Motivation: {req.motivation}")
    return "\n".join(parts) if parts else "General query"


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/")
def root():
    """Root endpoint with service status."""
    return {
        "status": "healthy",
        "message": "Donor Recommendation API is running",
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
    query: str = Field(..., description="Natural language query for donor/volunteer search")
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
    
    Example queries:
    - "Find donors interested in education in Singapore"
    - "Show me corporate donors who focus on environmental causes"
    - "Find volunteers with tech skills available on weekends"
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
# Donor Endpoints
# ============================================================================

@app.post("/donors/register", response_model=FormResponse)
async def register_donor(form: DonorFormRequest):
    """Register a donor and generate embedding."""
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Convert form to encoding text
        text = donor_form_to_text(form)

        # Generate embedding
        embedding = await encoder.encode(text)

        # Store in database
        form_data = form.model_dump()
        await vector_store.store_embedding(
            form_id=form.id,
            form_type="donor",
            embedding=embedding,
            form_data=form_data
        )

        return FormResponse(
            id=form.id,
            form_type="donor",
            message="Donor registered successfully",
            embedding_dimension=len(embedding)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/donors/recommend", response_model=RecommendResponse)
async def recommend_donors(request: RecommendRequest):
    """Find similar donors based on query."""
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Get query embedding
        if request.form_id:
            # Use existing form's embedding
            existing = await vector_store.get_embedding(request.form_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Form {request.form_id} not found")
            # Re-encode for query (could also store raw embedding)
            text = recommend_request_to_text(request)
            query_embedding = await encoder.encode(text)
        else:
            # Generate new embedding from request data
            text = recommend_request_to_text(request)
            query_embedding = await encoder.encode(text)

        # Find similar donors
        results = await vector_store.find_similar(
            query_embedding=query_embedding,
            form_type="donor",
            limit=request.limit,
            country_filter=request.country_filter,
            exclude_ids=request.exclude_ids if request.exclude_ids else None
        )

        return RecommendResponse(
            query_id=request.form_id,
            results=[
                RecommendationResult(
                    id=r.id,
                    form_type=r.form_type,
                    score=r.score,
                    distance=r.distance,
                    form_data=r.form_data
                )
                for r in results
            ],
            total_found=len(results)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Volunteer Endpoints
# ============================================================================

@app.post("/volunteers/register", response_model=FormResponse)
async def register_volunteer(form: VolunteerFormRequest):
    """Register a volunteer and generate embedding."""
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Convert form to encoding text
        text = volunteer_form_to_text(form)

        # Generate embedding
        embedding = await encoder.encode(text)

        # Store in database
        form_data = form.model_dump()
        await vector_store.store_embedding(
            form_id=form.id,
            form_type="volunteer",
            embedding=embedding,
            form_data=form_data
        )

        return FormResponse(
            id=form.id,
            form_type="volunteer",
            message="Volunteer registered successfully",
            embedding_dimension=len(embedding)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/volunteers/recommend", response_model=RecommendResponse)
async def recommend_volunteers(request: RecommendRequest):
    """Find similar volunteers based on query."""
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Generate query embedding
        text = recommend_request_to_text(request)
        query_embedding = await encoder.encode(text)

        # Find similar volunteers
        results = await vector_store.find_similar(
            query_embedding=query_embedding,
            form_type="volunteer",
            limit=request.limit,
            country_filter=request.country_filter,
            exclude_ids=request.exclude_ids if request.exclude_ids else None
        )

        return RecommendResponse(
            query_id=request.form_id,
            results=[
                RecommendationResult(
                    id=r.id,
                    form_type=r.form_type,
                    score=r.score,
                    distance=r.distance,
                    form_data=r.form_data
                )
                for r in results
            ],
            total_found=len(results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Form Management Endpoints
# ============================================================================

@app.get("/forms/{form_id}")
async def get_form(form_id: str):
    """Get a stored form by ID."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    result = await vector_store.get_embedding(form_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Form {form_id} not found")

    return {
        "id": result.id,
        "form_type": result.form_type,
        "form_data": result.form_data
    }


@app.delete("/forms/{form_id}")
async def delete_form(form_id: str):
    """Delete a form by ID."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    deleted = await vector_store.delete_embedding(form_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Form {form_id} not found")

    return {"message": f"Form {form_id} deleted successfully"}


@app.get("/forms/stats/summary", response_model=StatsResponse)
async def get_form_stats():
    """Get form counts by type."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        counts = await vector_store.count_by_type()
        return StatsResponse(
            donor=counts.get("donor", 0),
            volunteer=counts.get("volunteer", 0),
            total=counts.get("total", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Cause-based Search Endpoint
# ============================================================================

@app.post("/forms/search/causes")
async def search_by_causes(
    causes: List[str],
    limit: int = 20
):
    """Search forms by causes with embedding ranking."""
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Create a synthetic query embedding for ranking
        query_text = f"Causes interested in: {', '.join(causes)}"
        query_embedding = await encoder.encode(query_text)

        results = await vector_store.find_by_causes(
            target_causes=causes,
            query_embedding=query_embedding,
            limit=limit
        )

        return {
            "causes": causes,
            "results": [
                {
                    "id": r.id,
                    "form_type": r.form_type,
                    "score": r.score,
                    "distance": r.distance,
                    "form_data": r.form_data
                }
                for r in results
            ],
            "total_found": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GIS & Client Targeting Endpoints
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


@app.get("/planning-areas")
async def get_planning_areas():
    """Get all Singapore planning areas with coordinates."""
    from recommender.gis_recommender import PLANNING_AREAS

    return PLANNING_AREAS


@app.get("/housing-types")
async def get_housing_types():
    """Get all housing types with income proxy scores."""
    from recommender.gis_recommender import HOUSING_INCOME_PROXY, HousingType

    return {
        "types": [h.value for h in HousingType],
        "income_proxy": {h.value: score for h, score in HOUSING_INCOME_PROXY.items()},
    }


@app.post("/clients/register", response_model=FormResponse)
async def register_client(profile: ClientProfileRequest):
    """
    Register a client profile with spatial and behavioral data.

    This creates an embedding combining interests/causes with spatial context.
    """
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        from recommender.gis_recommender import ClientProfile, HousingType

        # Create client profile
        client = ClientProfile(
            user_id=profile.user_id,
            coordinates=tuple(profile.coordinates),
            planning_area=profile.planning_area,
            housing_type=HousingType(profile.housing_type),
            interests=profile.interests,
            causes=profile.causes,
            preferred_language=profile.preferred_language,
            is_donor=profile.is_donor,
            total_donated=profile.total_donated,
            donation_count=profile.donation_count,
            age_range=profile.age_range,
        )

        # Generate embedding
        text = client.to_embedding_text()
        embedding = await encoder.encode(text)

        # Store in database
        form_data = client.to_dict()
        form_data["country"] = "SG"  # For existing filter compatibility

        await vector_store.store_embedding(
            form_id=profile.user_id,
            form_type="client",
            embedding=embedding,
            form_data=form_data,
        )

        return FormResponse(
            id=profile.user_id,
            form_type="client",
            message="Client profile registered successfully",
            embedding_dimension=len(embedding),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clients/lookalike", response_model=LookalikeResponse)
async def find_lookalike_clients(request: LookalikeRequest):
    """
    Find lookalike clients (potential donors) based on a seed profile.

    This uses the GIS recommender with hybrid semantic-spatial matching:
    1. Find registered donors from database via vector search
    2. Apply spatial/housing filters
    3. Score using tiered targeting (vector + spatial proxy + proximity)
    4. Fall back to mock data if database has insufficient results
    5. Return results with optional GeoJSON for mapping

    Note: Searches BOTH donors (from /donors/register) and clients
    (from /clients/register) to find potential matches.
    """
    try:
        from recommender.gis_recommender import (
            ClientProfile,
            HousingType,
            GISRecommender,
            generate_seed_donor_profile,
            generate_mock_clients,
        )

        # Create seed profile from request
        seed = generate_seed_donor_profile(
            cause=request.seed_causes[0] if request.seed_causes else "education"
        )
        seed.causes = request.seed_causes
        seed.interests = request.seed_interests

        # Update seed coordinates if planning area specified
        if request.planning_area_filter:
            from recommender.gis_recommender import PLANNING_AREAS

            if request.planning_area_filter in PLANNING_AREAS:
                area = PLANNING_AREAS[request.planning_area_filter]
                seed.coordinates = (area["lat"], area["lng"])
                seed.planning_area = request.planning_area_filter

        # Regenerate embeddings for updated seed
        seed.embedding = None  # Force regeneration
        local_recommender = GISRecommender()
        seed.embedding = local_recommender._generate_fallback_embedding(seed)
        seed.compute_reduced_embeddings()

        # Convert housing type filter
        housing_filter = None
        if request.housing_type_filter:
            housing_filter = [HousingType(h) for h in request.housing_type_filter]

        scored_clients = []
        db_results_count = 0

        # Try database search first if available
        if gis_recommender and encoder and vector_store:
            try:
                print(
                    f"Searching database for donors matching causes: {request.seed_causes}"
                )
                scored_clients = await gis_recommender.find_lookalikes(
                    seed_profile=seed,
                    k=request.limit * 2,  # Get more to allow for filtering
                    planning_area_filter=None,  # Remove strict filter for DB search
                    housing_type_filter=None,  # Filter after retrieval
                    use_hybrid=False,
                )
                db_results_count = len(scored_clients)
                print(f"Found {db_results_count} donors/clients from database")

                # Apply filters after retrieval for more flexible matching
                if request.planning_area_filter:
                    scored_clients = [
                        sc
                        for sc in scored_clients
                        if sc.client.planning_area == request.planning_area_filter
                    ]

                if housing_filter:
                    scored_clients = [
                        sc
                        for sc in scored_clients
                        if sc.client.housing_type in housing_filter
                    ]

            except Exception as e:
                print(f"Database search failed: {e}")
                import traceback

                traceback.print_exc()

        # If insufficient results from database, supplement with mock data
        min_results = max(request.limit // 2, 10)  # At least half the requested or 10
        if len(scored_clients) < min_results:
            print(f"Only {len(scored_clients)} from DB, supplementing with mock data")

            # Generate mock candidates
            fallback_candidates = generate_mock_clients(150)

            # Filter by causes for relevance
            if request.seed_causes:
                cause_matched = [
                    c
                    for c in fallback_candidates
                    if any(cause in c.causes for cause in request.seed_causes)
                ]
                if len(cause_matched) >= 20:
                    fallback_candidates = cause_matched

            # Use hybrid matching on mock data
            mock_results = local_recommender.find_lookalikes_hybrid(
                seed_profile=seed,
                candidates=fallback_candidates,
                k=request.limit - len(scored_clients),
                planning_area_filter=request.planning_area_filter,
                housing_type_filter=housing_filter,
            )

            scored_clients.extend(mock_results)
            print(
                f"Added {len(mock_results)} mock results, total: {len(scored_clients)}"
            )

        # Sort combined results by score
        scored_clients.sort(key=lambda x: x.final_score, reverse=True)
        scored_clients = scored_clients[: request.limit]

        # Apply tiered targeting with relaxed min_score for small datasets
        effective_min_score = max(0, request.min_score - 0.1)  # Relax slightly
        tiered = local_recommender.apply_tiered_targeting(
            scored_clients, min_score=effective_min_score
        )

        # Convert to response format
        def to_response(sc):
            return ScoredClientResponse(
                user_id=sc.client.user_id,
                planning_area=sc.client.planning_area,
                housing_type=sc.client.housing_type.value,
                causes=sc.client.causes,
                interests=sc.client.interests,
                is_donor=sc.client.is_donor,
                final_score=round(sc.final_score, 3),
                vector_similarity=round(sc.vector_similarity_score, 3),
                spatial_proxy=round(sc.spatial_proxy_score, 3),
                proximity=round(sc.proximity_score, 3),
                coordinates=(
                    list(sc.client.coordinates) if request.include_geojson else None
                ),
            )

        tiers_response = {
            "tier_1": [to_response(sc) for sc in tiered["tier_1"]],
            "tier_2": [to_response(sc) for sc in tiered["tier_2"]],
            "tier_3": [to_response(sc) for sc in tiered["tier_3"]],
        }

        # Generate GeoJSON if requested
        geojson = None
        if request.include_geojson:
            all_clients = tiered["tier_1"] + tiered["tier_2"] + tiered["tier_3"]
            geojson = local_recommender.to_geojson(all_clients)

        total = sum(len(t) for t in tiered.values())

        return LookalikeResponse(
            seed_causes=request.seed_causes,
            total_found=total,
            tiers=tiers_response,
            geojson=geojson,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _get_mock_lookalike_response(request: LookalikeRequest) -> LookalikeResponse:
    """Generate mock lookalike response when GIS recommender unavailable."""
    from recommender.gis_recommender import (
        generate_mock_clients,
        PLANNING_AREAS,
        HOUSING_INCOME_PROXY,
        HousingType,
    )

    # Generate mock clients
    mock_clients = generate_mock_clients(100)

    # Filter by causes
    filtered = [
        c
        for c in mock_clients
        if any(cause in c.causes for cause in request.seed_causes)
    ]

    # Apply planning area filter
    if request.planning_area_filter:
        filtered = [
            c for c in filtered if c.planning_area == request.planning_area_filter
        ]

    # Score and sort
    scored = []
    for client in filtered[: request.limit]:
        # Calculate mock scores
        cause_match = len(set(client.causes) & set(request.seed_causes)) / max(
            len(request.seed_causes), 1
        )
        spatial_score = HOUSING_INCOME_PROXY.get(client.housing_type, 0.5)
        final_score = 0.5 * cause_match + 0.3 * spatial_score + 0.2 * 0.5

        scored.append(
            {
                "client": client,
                "final_score": final_score,
                "vector_similarity": cause_match,
                "spatial_proxy": spatial_score,
                "proximity": 0.5,
            }
        )

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    # Apply min score filter
    scored = [s for s in scored if s["final_score"] >= request.min_score]

    # Create tiers
    n = len(scored)
    tier_size = max(n // 3, 1)

    def to_response(s):
        c = s["client"]
        return ScoredClientResponse(
            user_id=c.user_id,
            planning_area=c.planning_area,
            housing_type=c.housing_type.value,
            causes=c.causes,
            interests=c.interests,
            is_donor=c.is_donor,
            final_score=round(s["final_score"], 3),
            vector_similarity=round(s["vector_similarity"], 3),
            spatial_proxy=round(s["spatial_proxy"], 3),
            proximity=round(s["proximity"], 3),
            coordinates=list(c.coordinates) if request.include_geojson else None,
        )

    tiers = {
        "tier_1": [to_response(s) for s in scored[:tier_size]],
        "tier_2": [to_response(s) for s in scored[tier_size : tier_size * 2]],
        "tier_3": [to_response(s) for s in scored[tier_size * 2 :]],
    }

    # Generate GeoJSON
    geojson = None
    if request.include_geojson:
        features = []
        for s in scored:
            c = s["client"]
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            round(c.coordinates[1], 3),
                            round(c.coordinates[0], 3),
                        ],
                    },
                    "properties": {
                        "user_id": c.user_id,
                        "planning_area": c.planning_area,
                        "housing_type": c.housing_type.value,
                        "causes": c.causes,
                        "is_donor": c.is_donor,
                        "final_score": round(s["final_score"], 3),
                    },
                }
            )
        geojson = {"type": "FeatureCollection", "features": features}

    return LookalikeResponse(
        seed_causes=request.seed_causes,
        total_found=len(scored),
        tiers=tiers,
        geojson=geojson,
    )


@app.post("/clients/seed-mock-data")
async def seed_mock_client_data(count: int = 100):
    """
    Seed the database with mock client profiles for testing.

    This populates the vector store with realistic Singapore client data.
    """
    if not encoder:
        raise HTTPException(status_code=503, detail="Encoder not initialized")
    if not vector_store:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        from recommender.gis_recommender import generate_mock_clients

        clients = generate_mock_clients(count)
        registered = 0

        for client in clients:
            text = client.to_embedding_text()
            embedding = await encoder.encode(text)

            form_data = client.to_dict()
            form_data["country"] = "SG"

            await vector_store.store_embedding(
                form_id=client.user_id,
                form_type="client",
                embedding=embedding,
                form_data=form_data,
            )
            registered += 1

        return {
            "message": f"Seeded {registered} mock client profiles",
            "count": registered,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/database-stats")
async def get_database_stats():
    """
    Debug endpoint to check what's stored in the vector database.

    Returns counts of donors, volunteers, and clients in the database.
    """
    if not vector_store:
        return {"error": "Database not connected", "stats": None}

    try:
        async with vector_store.pool.connection() as conn:
            async with conn.cursor() as cur:
                # Count by form_type
                await cur.execute(
                    """
                    SELECT 
                        metadata->>'form_type' as form_type,
                        COUNT(*) as count
                    FROM my_embeddings
                    GROUP BY metadata->>'form_type'
                    ORDER BY count DESC
                """
                )
                type_counts = await cur.fetchall()

                # Get sample entries
                await cur.execute(
                    """
                    SELECT source_id, metadata->>'form_type', 
                           LEFT(text_content::text, 200) as preview
                    FROM my_embeddings
                    ORDER BY id DESC
                    LIMIT 10
                """
                )
                recent = await cur.fetchall()

        return {
            "connected": True,
            "form_type_counts": {row[0]: row[1] for row in type_counts},
            "total_entries": sum(row[1] for row in type_counts),
            "recent_entries": [
                {"id": row[0], "form_type": row[1], "preview": row[2]} for row in recent
            ],
        }
    except Exception as e:
        return {"error": str(e), "stats": None}


@app.get("/clients/map-demographics")
async def get_map_demographics(
    causes: Optional[str] = None,  # Comma-separated causes
    include_donors: bool = True,
    include_clients: bool = True,
):
    """
    Get aggregated demographics data for Singapore map visualization.

    Returns:
    - Planning area aggregates (donor counts, cause distribution, housing breakdown)
    - Individual donor/client points with coordinates
    - Demographics summary for clusters
    """
    from recommender.gis_recommender import (
        PLANNING_AREAS,
        HousingType,
        HOUSING_INCOME_PROXY,
    )

    if not vector_store:
        # Return mock data if database not available
        return await _generate_mock_map_demographics(causes)

    try:
        cause_list = causes.split(",") if causes else None

        # Query all donors and clients from database
        all_entries = []

        if include_donors:
            donor_results = await vector_store.find_by_form_type("donor", limit=500)
            all_entries.extend(donor_results)

        if include_clients:
            client_results = await vector_store.find_by_form_type("client", limit=500)
            all_entries.extend(client_results)

        # Aggregate by planning area
        area_stats = {}
        individual_points = []

        for entry in all_entries:
            form_data = (
                entry.form_data
                if hasattr(entry, "form_data")
                else entry.get("form_data", {})
            )
            entry_id = entry.id if hasattr(entry, "id") else entry.get("id", "")
            form_type = (
                entry.form_type
                if hasattr(entry, "form_type")
                else entry.get("form_type", "")
            )

            # Get planning area
            planning_area = form_data.get("planning_area", "unknown")
            if planning_area == "unknown" and form_data.get("country") == "SG":
                # Infer planning area from ID hash for donors without explicit area
                import hashlib

                area_list = list(PLANNING_AREAS.keys())
                idx = int(hashlib.md5(entry_id.encode()).hexdigest(), 16) % len(
                    area_list
                )
                planning_area = area_list[idx]

            # Get causes
            entry_causes = form_data.get("causes", [])
            if isinstance(entry_causes, str):
                entry_causes = [entry_causes]

            # Filter by causes if specified
            if cause_list:
                if not any(c in entry_causes for c in cause_list):
                    continue

            # Get housing type
            housing_type = form_data.get("housing_type", "hdb_4_room")
            amount_range = form_data.get("amount_range", "")
            if not housing_type or housing_type == "unknown":
                # Infer from amount_range
                if "10000" in str(amount_range) or "5000" in str(amount_range):
                    housing_type = "landed"
                elif "1000" in str(amount_range):
                    housing_type = "condo"
                elif "500" in str(amount_range):
                    housing_type = "hdb_executive"
                else:
                    housing_type = "hdb_4_room"

            # Get coordinates
            if planning_area in PLANNING_AREAS:
                area_info = PLANNING_AREAS[planning_area]
                lat = area_info["lat"] + (hash(entry_id) % 100 - 50) * 0.0005
                lng = area_info["lng"] + (hash(entry_id[::-1]) % 100 - 50) * 0.0005
            else:
                lat, lng = 1.3521, 103.8198  # Singapore center

            # Aggregate by area
            if planning_area not in area_stats:
                area_stats[planning_area] = {
                    "name": PLANNING_AREAS.get(planning_area, {}).get(
                        "name", planning_area.replace("_", " ").title()
                    ),
                    "lat": PLANNING_AREAS.get(planning_area, {}).get("lat", 1.3521),
                    "lng": PLANNING_AREAS.get(planning_area, {}).get("lng", 103.8198),
                    "total_count": 0,
                    "donor_count": 0,
                    "client_count": 0,
                    "causes": {},
                    "housing_breakdown": {},
                    "avg_income_proxy": 0,
                    "income_proxies": [],
                }

            stats = area_stats[planning_area]
            stats["total_count"] += 1
            if form_type == "donor":
                stats["donor_count"] += 1
            else:
                stats["client_count"] += 1

            # Count causes
            for cause in entry_causes:
                stats["causes"][cause] = stats["causes"].get(cause, 0) + 1

            # Count housing
            stats["housing_breakdown"][housing_type] = (
                stats["housing_breakdown"].get(housing_type, 0) + 1
            )

            # Track income proxy
            try:
                income_proxy = HOUSING_INCOME_PROXY.get(HousingType(housing_type), 0.5)
            except:
                income_proxy = 0.5
            stats["income_proxies"].append(income_proxy)

            # Add individual point
            individual_points.append(
                {
                    "id": entry_id,
                    "type": form_type,
                    "lat": lat,
                    "lng": lng,
                    "planning_area": planning_area,
                    "housing_type": housing_type,
                    "causes": entry_causes[:5],  # Limit for performance
                    "is_donor": form_type == "donor",
                }
            )

        # Calculate averages
        for area, stats in area_stats.items():
            if stats["income_proxies"]:
                stats["avg_income_proxy"] = round(
                    sum(stats["income_proxies"]) / len(stats["income_proxies"]), 3
                )
            del stats["income_proxies"]

        # Create GeoJSON for areas (polygons would need actual boundary data, using circles)
        area_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [stats["lng"], stats["lat"]],
                    },
                    "properties": {
                        "planning_area": area,
                        "name": stats["name"],
                        **{k: v for k, v in stats.items() if k not in ["lat", "lng"]},
                    },
                }
                for area, stats in area_stats.items()
            ],
        }

        # Create GeoJSON for individual points
        points_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [p["lng"], p["lat"]],
                    },
                    "properties": {
                        "id": p["id"],
                        "type": p["type"],
                        "planning_area": p["planning_area"],
                        "housing_type": p["housing_type"],
                        "causes": p["causes"],
                        "is_donor": p["is_donor"],
                    },
                }
                for p in individual_points
            ],
        }

        # Summary statistics
        all_causes = {}
        all_housing = {}
        for stats in area_stats.values():
            for cause, count in stats["causes"].items():
                all_causes[cause] = all_causes.get(cause, 0) + count
            for housing, count in stats["housing_breakdown"].items():
                all_housing[housing] = all_housing.get(housing, 0) + count

        return {
            "total_donors": sum(s["donor_count"] for s in area_stats.values()),
            "total_clients": sum(s["client_count"] for s in area_stats.values()),
            "areas_with_data": len(area_stats),
            "summary": {
                "top_causes": sorted(
                    all_causes.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "housing_distribution": all_housing,
            },
            "area_aggregates": area_geojson,
            "individual_points": points_geojson,
            "planning_areas": PLANNING_AREAS,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return await _generate_mock_map_demographics(causes)


async def _generate_mock_map_demographics(causes: Optional[str] = None):
    """Generate mock demographics data for map visualization."""
    from recommender.gis_recommender import (
        PLANNING_AREAS,
        HOUSING_INCOME_PROXY,
        HousingType,
    )
    import random

    cause_list = (
        causes.split(",")
        if causes
        else ["education", "animals", "poverty", "environment", "health"]
    )

    area_stats = {}
    individual_points = []

    for area_id, area_info in PLANNING_AREAS.items():
        count = random.randint(3, 25)
        donors = random.randint(1, count)

        area_stats[area_id] = {
            "name": area_info["name"],
            "lat": area_info["lat"],
            "lng": area_info["lng"],
            "total_count": count,
            "donor_count": donors,
            "client_count": count - donors,
            "causes": {
                cause: random.randint(1, count)
                for cause in random.sample(cause_list, min(3, len(cause_list)))
            },
            "housing_breakdown": {
                "hdb_4_room": random.randint(0, count // 2),
                "condo": random.randint(0, count // 3),
                "landed": random.randint(0, count // 4),
            },
            "avg_income_proxy": round(random.uniform(0.3, 0.8), 3),
        }

        # Generate individual points
        for i in range(count):
            lat = area_info["lat"] + (random.random() - 0.5) * 0.02
            lng = area_info["lng"] + (random.random() - 0.5) * 0.02
            housing_types = [
                "hdb_3_room",
                "hdb_4_room",
                "hdb_5_room",
                "hdb_executive",
                "condo",
                "landed",
            ]

            individual_points.append(
                {
                    "id": f"mock_{area_id}_{i}",
                    "type": "donor" if i < donors else "client",
                    "lat": lat,
                    "lng": lng,
                    "planning_area": area_id,
                    "housing_type": random.choice(housing_types),
                    "causes": random.sample(cause_list, min(2, len(cause_list))),
                    "is_donor": i < donors,
                }
            )

    # Create GeoJSON
    area_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [stats["lng"], stats["lat"]],
                },
                "properties": {
                    "planning_area": area,
                    "name": stats["name"],
                    **{k: v for k, v in stats.items() if k not in ["lat", "lng"]},
                },
            }
            for area, stats in area_stats.items()
        ],
    }

    points_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["lng"], p["lat"]]},
                "properties": {k: v for k, v in p.items() if k not in ["lat", "lng"]},
            }
            for p in individual_points
        ],
    }

    return {
        "total_donors": sum(s["donor_count"] for s in area_stats.values()),
        "total_clients": sum(s["client_count"] for s in area_stats.values()),
        "areas_with_data": len(area_stats),
        "summary": {
            "top_causes": [(c, random.randint(10, 50)) for c in cause_list[:5]],
            "housing_distribution": {
                "hdb_4_room": 120,
                "condo": 45,
                "landed": 20,
                "hdb_5_room": 30,
            },
        },
        "area_aggregates": area_geojson,
        "individual_points": points_geojson,
        "planning_areas": PLANNING_AREAS,
    }


@app.get("/debug/search-donors")
async def debug_search_donors(cause: str = "education", limit: int = 10):
    """
    Debug endpoint to directly search for donors in the database.

    This bypasses the GIS recommender to see raw database results.
    """
    if not encoder or not vector_store:
        return {"error": "Encoder or database not available"}

    try:
        # Create a simple query embedding
        query_text = f"Donor interested in {cause} causes, looking to support {cause} initiatives"
        query_embedding = await encoder.encode(query_text)

        # Search for donors
        donor_results = await vector_store.find_similar(
            query_embedding=query_embedding,
            form_type="donor",
            limit=limit,
        )

        # Also search for clients
        client_results = await vector_store.find_similar(
            query_embedding=query_embedding,
            form_type="client",
            limit=limit,
        )

        return {
            "query_cause": cause,
            "donor_results": [
                {
                    "id": r.id,
                    "form_type": r.form_type,
                    "score": round(r.score, 4),
                    "distance": round(r.distance, 4),
                    "causes": r.form_data.get("causes", []),
                    "country": r.form_data.get("country"),
                }
                for r in donor_results
            ],
            "client_results": [
                {
                    "id": r.id,
                    "form_type": r.form_type,
                    "score": round(r.score, 4),
                    "distance": round(r.distance, 4),
                    "causes": r.form_data.get("causes", []),
                    "planning_area": r.form_data.get("planning_area"),
                }
                for r in client_results
            ],
            "total_donors": len(donor_results),
            "total_clients": len(client_results),
        }
    except Exception as e:
        import traceback

        return {"error": str(e), "traceback": traceback.format_exc()}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Windows-specific fix: must be set before uvicorn starts its event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(app, host="0.0.0.0", port=7860)
