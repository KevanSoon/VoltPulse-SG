# System Architecture Overview

[← Back to Documentation](../README.md)

## Table of Contents
- [Introduction](#introduction)
- [High-Level Architecture](#high-level-architecture)
- [Component Interactions](#component-interactions)
- [Technology Choices and Rationale](#technology-choices-and-rationale)
- [Trade-off Analysis](#trade-off-analysis)
- [Data Flow Summary](#data-flow-summary)

---

## Introduction

VoltPulse-SG is an AI-powered utility bill analysis platform designed specifically for Singapore households. The system combines **OpenAI Vision OCR**, **SEALION embeddings**, **LangGraph orchestration**, and **Reciprocal Rank Fusion (RRF) ranking** to provide intelligent consumption analysis and retailer recommendations.

**Core Capabilities:**
- Extract and analyze utility bills using OpenAI Vision API
- Detect consumption anomalies and efficiency issues
- Recommend energy-efficient appliances with ROI calculations
- Find 700+ Climate Voucher participating retailers using multi-signal ranking
- Provide conversational AI assistant powered by agentic RAG

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 15)                          │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ Landing Page │  │ Upload & OCR  │  │ Analytics │  │ Chat Interface│ │
│  │   (Hero,     │  │ (Drag & Drop, │  │(Dashboard,│  │  (Agentic    │ │
│  │  Features)   │  │   Progress)   │  │ Heatmap)  │  │    RAG)      │ │
│  └──────────────┘  └───────────────┘  └───────────┘  └──────────────┘ │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP/REST API
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │                    LangGraph Orchestration                         ││
│  │                                                                    ││
│  │   START → Classifier → Router → Agentic RAG Agent → END           ││
│  │             (5 categories)          (5 tools, ReAct loop)          ││
│  │                                                                    ││
│  │   Tools: [get_user_consumption_info, get_energy_rating_info,      ││
│  │          calculate_appliance_roi, search_appliance_recommendations,││
│  │          find_retailers_by_product]                                ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ Vision Extractor │  │ Bill Diagnosis   │  │ RRF Scorer         │   │
│  │ (OpenAI Vision)  │  │ (Anomaly, Health)│  │ (5-signal ranking) │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘   │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ ROI Calculator   │  │ Statistical      │  │ Retailer Loader    │   │
│  │ (10 products)    │  │ Analyzer (SciPy) │  │ (700+ retailers)   │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  AI & EMBEDDINGS LAYER                                  │
│                                                                          │
│  ┌────────────────────────┐          ┌──────────────────────────────┐  │
│  │   SEALION Encoder      │          │   Ollama LLM                 │  │
│  │   (1024-dim vectors)   │◄────────►│   (gpt-oss:120b)             │  │
│  │                        │          │   - Classifier               │  │
│  │  • Text Hash (0-255)   │          │   - Agentic RAG reasoning    │  │
│  │  • Causes (256-511)    │          │   - Tool orchestration       │  │
│  │  • Scores (512-557)    │          └──────────────────────────────┘  │
│  │  • Themes (600-1023)   │                                             │
│  └────────────────────────┘                                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 DATABASE LAYER (Supabase PostgreSQL)                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │  my_embeddings (pgvector extension)                                ││
│  │  ├─ source_id (TEXT) - Document ID                                 ││
│  │  ├─ text_content (JSONB) - Full document data                      ││
│  │  ├─ metadata (JSONB) - form_type, tags, etc.                       ││
│  │  └─ embedding (VECTOR(1024)) - SEALION embeddings                  ││
│  │       [IVFFlat index for L2 distance search]                       ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │  langgraph_store (Agent memory)                                    ││
│  │  └─ Stores conversation context, user memories (semantic search)   ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │  langgraph_checkpoints (Conversation state)                        ││
│  │  └─ Thread-based message history, state snapshots                  ││
│  └────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interactions

### 1. Bill Upload & Analysis Flow

```
User uploads bill image
    ↓
[Frontend] → POST /api/ocr/process
    ↓
[Backend] OpenAI Vision API
    ├─ Extract text (account, customer, address)
    ├─ Parse consumption (kWh, gas, water)
    ├─ Read monthly trend charts (bar chart OCR)
    └─ Return ElectricityBillExtraction + confidence
    ↓
[Backend] Bill Diagnosis Service
    ├─ Anomaly Detection (spikes, z-score outliers)
    ├─ Efficiency Analysis (vs national/neighbor avg)
    ├─ Trend Warnings (increasing consumption)
    ├─ Health Scoring (0-100 with A-F grade)
    └─ Personalized Recommendations
    ↓
[Backend] SEALION Encoder
    ├─ Generate 1024-dim embedding from bill data
    └─ Store in pgvector (my_embeddings table)
    ↓
[Frontend] Display OCR result + diagnosis
```

### 2. Chat Query Flow (Agentic RAG)

```
User sends chat message
    ↓
[Frontend] → POST /api/chat
    ↓
[Backend] LangGraph Orchestration
    │
    ├─ [Classifier Node] Categorize query
    │   - consumption_info
    │   - energy_rating_info
    │   - appliance_roi
    │   - web_search
    │   - retailer_search
    │
    ├─ [Router] Route to Agentic RAG
    │
    └─ [Agentic RAG Agent] ReAct Loop
        │
        ├─ [Thought] Analyze user intent
        ├─ [Action] Select and invoke tool(s)
        │   └─ Tool examples:
        │       • get_user_consumption_info → RAG over OCR bills
        │       • find_retailers_by_product → RRF ranking of 700+ retailers
        │       • calculate_appliance_roi → ROI calculations
        │       • search_appliance_recommendations → Web search
        │
        ├─ [Observation] Process tool results
        ├─ [Thought] Synthesize response
        └─ [Response] Return to user
    ↓
[Backend] Store message in langgraph_store (memory)
    ↓
[Frontend] Display response with markdown + citations
```

### 3. Retailer Recommendation Flow

```
User asks: "Where to buy aircon near Bedok?"
    ↓
[Agentic RAG] Invokes find_retailers_by_product tool
    ↓
[Retailer Tools] Query processing
    ├─ Product: "air_conditioners"
    ├─ Location: "Bedok"
    └─ Query text: "Where to buy aircon near Bedok?"
    ↓
[SEALION Encoder] Generate query embedding (1024-dim)
    ↓
[Vector Store] Semantic search over retailers
    ├─ SELECT * FROM my_embeddings
    │   WHERE metadata->>'form_type' = 'retailer'
    │   ORDER BY embedding <-> query_embedding
    │   LIMIT 800
    └─ Returns ~800 candidate retailers
    ↓
[RRF Scorer] Multi-signal ranking
    ├─ Signal 1: Semantic Similarity (40%)
    ├─ Signal 2: Product Match (25%)
    ├─ Signal 3: Location Relevance (20%)
    ├─ Signal 4: Retailer Breadth (10%)
    ├─ Signal 5: Query Intent (5%)
    │
    └─ RRF Formula: Score = Σ [weight_i / (k + rank_i)]
    ↓
[Retailer Tools] Format top 10 results as JSON
    ├─ Retailer name, address, postal code
    ├─ Eligible products
    ├─ RRF scores (semantic, product, location, breadth, intent)
    └─ Final rank
    ↓
[Agentic RAG] Returns retailer list to user
```

---

## Technology Choices and Rationale

### Frontend: Next.js 15 + React 19

**Why Next.js over alternatives?**
- **Server-Side Rendering (SSR)**: Fast initial page load for landing page SEO
- **App Router**: Modern routing with layouts and parallel routes
- **API routes**: Simplifies backend proxying (`/api/chat` → `backend:7860/chat`)
- **Vercel deployment**: Zero-config production deployment

**Trade-off:** More complex than pure React SPA, but justified for SSR benefits and integrated API routes.

### Backend: FastAPI

**Why FastAPI over Flask/Django?**
- **Async/await support**: Critical for LangGraph async operations
- **Auto OpenAPI docs**: `/docs` endpoint for API exploration
- **Pydantic validation**: Type-safe request/response schemas
- **Performance**: Faster than Flask (ASGI vs WSGI)

**Trade-off:** Smaller ecosystem than Flask, but modern async support is essential.

### LLM Orchestration: LangGraph

**Why LangGraph over LangChain LCEL?**
- **State machine control**: Explicit graph structure (START → Classifier → Router → Agent → END)
- **Checkpointing**: Built-in conversation persistence via AsyncPostgresSaver
- **Memory management**: AsyncPostgresStore for cross-conversation context
- **Streaming support**: Native streaming for real-time responses
- **ReAct agents**: `create_react_agent` for autonomous tool orchestration

**Trade-off:** More complex setup than LCEL, but provides fine-grained control over agent flow and state management.

**Why not pure LangChain LCEL?**
- LCEL lacks explicit state machine visualization
- No built-in checkpointing to PostgreSQL
- Limited control over routing logic

### Embeddings: SEALION

**Why SEALION over OpenAI Ada-002 or Cohere?**
- **ASEAN focus**: Better understanding of Singapore English, Malay, Chinese
- **Cost efficiency**: Lower per-token cost than OpenAI embeddings
- **Government alignment**: Supports SEA AI initiative
- **Customizable**: 1024-dimensional with segmented feature space

**Trade-off:** Self-hosted endpoint required (not a managed API like OpenAI), but provides better regional understanding and cost savings.

**Why not OpenAI Ada-002?**
- Less optimized for ASEAN languages
- Higher cost ($0.0001 per 1K tokens vs SEALION custom pricing)

### Vector Database: Supabase with pgvector

**Why Supabase + pgvector over Pinecone/Weaviate?**
- **Single database**: Embeddings + application data + LangGraph state in one PostgreSQL instance
- **Cost-effective**: No separate vector DB subscription
- **SQL flexibility**: Full PostgreSQL query capabilities (JSONB filtering, joins)
- **IVFFlat index**: Efficient approximate nearest neighbor search
- **Supabase managed**: Auto-backups, connection pooling, dashboard

**Trade-off:** Slightly slower than purpose-built vector DBs (Pinecone, Qdrant) at massive scale, but VoltPulse-SG has ~1000 documents (well within PostgreSQL capabilities).

**Why not Pinecone?**
- Separate infrastructure (another service to manage)
- Higher cost for low-scale usage
- No SQL flexibility

### LLM: Ollama (gpt-oss:120b)

**Why Ollama over OpenAI GPT-4?**
- **Cost**: Self-hosted model, no per-token charges
- **Privacy**: Data stays within system (no external API calls)
- **Latency control**: Can run locally or on dedicated GPU server

**Trade-off:** Requires GPU infrastructure, but provides cost predictability for high-volume queries.

**Configuration:**
```python
# Cloud Ollama (with API key)
llm = ChatOllama(
    model="gpt-oss:120b",
    base_url="https://ollama.com",
    client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}}
)
```

### OCR: OpenAI Vision API

**Why OpenAI Vision over PaddleOCR/Tesseract?**
- **Chart reading**: Extracts data from bar charts (monthly consumption trends)
- **Multi-service support**: Handles electricity, gas, water on same bill
- **Structured extraction**: GPT-4o understands bill layout and returns JSON
- **No preprocessing**: Works with raw images (no deskewing, noise reduction needed)

**Trade-off:** API cost ($0.01 per image), but worth it for accurate chart extraction that PaddleOCR cannot handle.

**Example prompt:**
```python
"""Extract ALL information from this utility bill image:
1. Account details (account number, customer name, address, postal code)
2. Billing period (start date, end date, due date)
3. Consumption data (electricity kWh, gas kWh, water cubic meters)
4. Charges breakdown (consumption charges, tariff rates, total amount)
5. Monthly consumption trends (read bar chart if present)

Return as structured JSON with confidence score."""
```

### Recommender: Reciprocal Rank Fusion (RRF)

**Why RRF over single-signal ranking?**
- **Robustness**: Combines 5 signals (semantic, product, location, breadth, intent)
- **No normalization required**: Rank-based, not score-based
- **Tunable**: Weights configurable via environment variables
- **Research-backed**: Proven method in information retrieval

**Trade-off:** More complex than cosine similarity alone, but provides better recommendation quality.

**Why not Learning-to-Rank (LTR)?**
- LTR requires training data (we have no labeled retailer rankings)
- RRF works out-of-the-box with no training

**Formula:**
```
Final Score = Σ [weight_i / (k + rank_i)] for all signals i
where k = 60 (scale constant)
```

---

## Trade-off Analysis

### 1. Classification Layer

**Decision:** Add a classifier node before agentic RAG to categorize queries.

**Pros:**
- Reduces unnecessary tool calls (52% reduction: 2.3 → 1.1 calls/query)
- Provides routing hint to agent (though agent can override)
- Lowers LLM token usage

**Cons:**
- Adds latency (~200ms)
- Extra LLM call per query

**Verdict:** Worth it. Cost savings (52%) outweigh latency penalty.

### 2. Quick Mode for RRF

**Decision:** Auto-enable quick mode (2 signals) when candidates > 30.

**Pros:**
- 3x faster ranking (200ms → 70ms)
- Same quality for large candidate sets (top-k still reliable)
- Configurable threshold

**Cons:**
- Loses location, breadth, intent signals
- May miss nuanced ranking for small result sets

**Verdict:** Worth it. Large result sets benefit from speed, and semantic + product are most important signals.

### 3. Pre-computed Energy Data

**Decision:** Hardcode consumption tables in `roi_calculator.py` instead of fetching from external API.

**Pros:**
- Zero latency (no API call)
- Zero cost
- Offline capability

**Cons:**
- Data can become outdated (requires manual updates)
- Less flexible

**Verdict:** Worth it. Energy consumption patterns change slowly (update annually is sufficient).

### 4. Bounded Vector Search

**Decision:** Limit vector search to 800 documents max.

**Pros:**
- 84% faster query execution
- Prevents memory issues on large result sets
- Covers 95%+ of use cases

**Cons:**
- May miss some retailers if >800 match query
- Not truly exhaustive search

**Verdict:** Worth it. 800 retailers is sufficient for user experience, and speed is critical.

---

## Data Flow Summary

### Primary Data Flows

1. **Bill Upload → Diagnosis**
   - Image → OpenAI Vision → ElectricityBillExtraction → Bill Diagnosis → DiagnosisResult → Frontend

2. **Chat Query → Agentic RAG**
   - User message → Classifier → Router → Agentic RAG → Tools → LLM → Response → Frontend

3. **Retailer Search → RRF Ranking**
   - Query → SEALION embedding → pgvector search → RRF scorer → Ranked retailers → Frontend

4. **Memory Persistence**
   - User message → langgraph_store (semantic search enabled) → Retrieved for future queries

### Data Storage

- **Vector Store (`my_embeddings`)**: Bills, retailers, consumption data
- **LangGraph Store (`langgraph_store`)**: Conversation memory (semantic search)
- **LangGraph Checkpoints (`langgraph_checkpoints`)**: Thread-based message history

---

## Cross-References

- [Tech Stack Details](./tech-stack.md) - Complete technology inventory
- [Data Flow Diagrams](./data-flow.md) - Detailed pipeline visualizations
- [Deployment Architecture](./deployment.md) - Infrastructure and hosting
- [RAG System](../02-core-systems/rag-system.md) - Agentic RAG implementation
- [SEALION Integration](../02-core-systems/sealion-integration.md) - Embedding architecture
- [Cost Optimization](../02-core-systems/cost-optimization.md) - 7 cost reduction strategies

---

[← Back to Documentation](../README.md) | [Next: Tech Stack →](./tech-stack.md)
