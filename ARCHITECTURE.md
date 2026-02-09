# VoltPulse SG - Architecture Documentation

## 📊 Complete Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 15.1.0 | React framework with App Router |
| **React** | 19.0.0 | UI library |
| **TypeScript** | 5.7.2 | Type safety |
| **Tailwind CSS** | 3.4.17 | Utility-first styling |
| **Recharts** | 2.15.0 | Data visualization charts |
| **Leaflet + React-Leaflet** | 1.9.4 / 5.0.0 | Interactive maps & heatmaps |
| **Lucide React** | 0.563.0 | Icon library |
| **React Markdown** | 10.1.0 | Markdown rendering in chat |
| **React Dropzone** | 14.3.5 | File upload drag-and-drop |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | ≥0.109.0 | REST API framework |
| **Uvicorn** | ≥0.27.0 | ASGI server |
| **Pydantic** | ≥2.0.0 | Data validation & schemas |
| **Python** | 3.11 | Runtime |

### AI/ML Stack
| Technology | Purpose |
|------------|---------|
| **LangGraph** | Agent orchestration with state machine |
| **LangChain Core** | LLM abstractions and tool framework |
| **LangChain Ollama** | Ollama LLM integration (gpt-oss:120b) |
| **OpenAI GPT-4o** | Vision-based OCR for utility bills |
| **OpenAI GPT-5** | Web search for charity/organization info |
| **Tavily** | Real-time web search for product recommendations |
| **SeaLion Encoder** | ASEAN multilingual embeddings (1024-dim) |

### Database & Storage
| Technology | Purpose |
|------------|---------|
| **Supabase (PostgreSQL)** | Primary cloud database |
| **pgvector** | Vector similarity search |
| **AsyncPostgresSaver** | LangGraph conversation memory |
| **AsyncPostgresStore** | LangGraph agent state storage |
| **psycopg3 (async)** | PostgreSQL driver with connection pool |

### External Services
| Service | Purpose |
|---------|---------|
| **Singpass Mock** | Singapore citizen data autofill |
| **Climate Voucher DB** | Participating retailers database |
| **Gradio Client** | OCR processing interface |
| **Tavily API** | Web search for appliance recommendations |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **Hugging Face Spaces** | Backend deployment |

---

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VOLTPULSE SG ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND                                       │
│                              (Next.js 15 + React 19)                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Chat UI    │  │  Bill Upload │  │  Analytics   │  │   Heatmap View       │ │
│  │  (Markdown)  │  │  (Dropzone)  │  │  (Recharts)  │  │   (Leaflet)          │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                 │                 │                     │              │
│         └─────────────────┼─────────────────┼─────────────────────┘              │
│                           │                 │                                    │
│                    ┌──────┴─────────────────┴──────┐                            │
│                    │     Next.js API Routes        │                            │
│                    │  /api/chat  /api/ocr  /api/   │                            │
│                    │       analytics               │                            │
│                    └──────────────┬─────────────────┘                            │
└───────────────────────────────────┼─────────────────────────────────────────────┘
                                    │ HTTP/REST
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND                                        │
│                            (FastAPI + Uvicorn)                                   │
│                              Port 7860                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         API ENDPOINTS                                    │    │
│  ├─────────────────┬──────────────────┬─────────────────┬──────────────────┤    │
│  │  POST /chat     │  POST /ocr/*     │ GET /analytics/*│ GET /retailers/* │    │
│  │  (LangGraph)    │  (Vision OCR)    │ (Stats Service) │ (Climate Voucher)│    │
│  └────────┬────────┴────────┬─────────┴────────┬────────┴────────┬─────────┘    │
│           │                 │                  │                 │              │
│           ▼                 ▼                  ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         SERVICES LAYER                                   │    │
│  ├──────────────────┬────────────────────┬──────────────────────────────────┤    │
│  │  Bill Diagnosis  │  Vision Extractor  │  Statistical Analyzer           │    │
│  │  (Pattern Det.)  │  (OpenAI GPT-4o)   │  (Scipy + Anomaly Detection)    │    │
│  └──────────────────┴────────────────────┴──────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      LANGGRAPH ORCHESTRATION                             │    │
│  │                     (See Agent Diagram Below)                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
┌──────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   SUPABASE       │    │    SEALION API       │    │   EXTERNAL APIs      │
│   PostgreSQL     │    │   (Embeddings)       │    │                      │
├──────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│  • my_embeddings │    │  • 1024-dim vectors  │    │  • OpenAI Vision     │
│    (pgvector)    │    │  • ASEAN multilingual│    │  • Tavily Search     │
│  • checkpoints   │    │  • Semantic encoding │    │  • Ollama Cloud      │
│  • store         │    │                      │    │  • Gradio OCR        │
│  • interventions │    └──────────────────────┘    └──────────────────────┘
└──────────────────┘
```

---

## 🤖 LangGraph Agent Orchestration Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH AGENT ORCHESTRATION                             │
│                    (State Machine with Persistent Memory)                        │
└─────────────────────────────────────────────────────────────────────────────────┘

                              User Message
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              [START NODE]                                        │
│                                   │                                              │
│                                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          CLASSIFIER NODE                                   │  │
│  │                    (LLM with Structured Output)                            │  │
│  │                                                                            │  │
│  │   Input: User message                                                      │  │
│  │   Output: message_type ∈ {consumption_info, energy_rating_info,           │  │
│  │            appliance_roi, web_search, retailer_search}                     │  │
│  │                                                                            │  │
│  │   Each category is a tool hint for the Agentic RAG agent:                 │  │
│  │                                                                            │  │
│  │   • "Show my electricity bills"          → consumption_info               │  │
│  │   • "What is a 4-tick rating?"           → energy_rating_info             │  │
│  │   • "Is upgrading my aircon worth it?"   → appliance_roi                  │  │
│  │   • "Best inverter aircon 2025"          → web_search                     │  │
│  │   • "Where to buy fridge near Bedok?"    → retailer_search               │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                              │
│                                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           ROUTER FUNCTION                                  │  │
│  │                  (All categories → agentic_rag)                            │  │
│  │                                                                            │  │
│  │        consumption_info ──┐                                                │  │
│  │        energy_rating_info ┤                                                │  │
│  │        appliance_roi ─────┼──────▶  AGENTIC RAG AGENT                     │  │
│  │        web_search ────────┤                                                │  │
│  │        retailer_search ───┘                                                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                              │
│                                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                       AGENTIC RAG AGENT                                    │  │
│  │                    (ReAct Pattern Agent)                                    │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                            │  │
│  │   ┌─────────────────────────────────────────────────────────────────────┐  │  │
│  │   │               ReAct Loop (Autonomous Tool Selection)                │  │  │
│  │   │                                                                     │  │  │
│  │   │          Thought → Action (Tool Call) → Observe Result              │  │  │
│  │   │                       ↺ (iterate until done)                        │  │  │
│  │   └─────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                            │  │
│  │   5 STANDALONE TOOLS:                                                      │  │
│  │                                                                            │  │
│  │   ┌──────────────────────────────────────────────────────────────────┐     │  │
│  │   │  1. get_user_consumption_info                                    │     │  │
│  │   │     RAG retrieval over user's uploaded utility bill documents    │     │  │
│  │   │     Returns: provider, billing period, kWh, costs, averages     │     │  │
│  │   ├──────────────────────────────────────────────────────────────────┤     │  │
│  │   │  2. get_energy_rating_info                                       │     │  │
│  │   │     Singapore energy efficiency tick rating system info          │     │  │
│  │   │     Returns: tick scales, minimum for voucher, tips              │     │  │
│  │   ├──────────────────────────────────────────────────────────────────┤     │  │
│  │   │  3. calculate_appliance_roi                                      │     │  │
│  │   │     ROI calculation for upgrading to energy-efficient appliance  │     │  │
│  │   │     Returns: payback period, annual savings, 5/10yr benefits     │     │  │
│  │   ├──────────────────────────────────────────────────────────────────┤     │  │
│  │   │  4. search_appliance_recommendations                             │     │  │
│  │   │     OpenAI web search for product reviews & buying guides        │     │  │
│  │   │     Returns: recommendations text + source URL citations         │     │  │
│  │   ├──────────────────────────────────────────────────────────────────┤     │  │
│  │   │  5. find_retailers_by_product                                    │     │  │
│  │   │     Search 700+ Climate Voucher retailers (limit=800 rows)       │     │  │
│  │   │     Returns: retailer name, address, area, eligible products     │     │  │
│  │   └──────────────────────────────────────────────────────────────────┘     │  │
│  │                                                                            │  │
│  │   Memory: AsyncPostgresStore (per-user conversation context)               │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                              │
│                                   ▼                                              │
│                              [END NODE]                                          │
│                                   │                                              │
└───────────────────────────────────┼──────────────────────────────────────────────┘
                                    │
                                    ▼
                            Final Response
                            (with Memory)


┌─────────────────────────────────────────────────────────────────────────────────┐
│                          PERSISTENCE LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌────────────────────────┐         ┌────────────────────────────────────┐    │
│    │  AsyncPostgresSaver    │         │      AsyncPostgresStore            │    │
│    │  (Checkpointer)        │         │      (Memory Store)                │    │
│    ├────────────────────────┤         ├────────────────────────────────────┤    │
│    │ • Saves graph state    │         │ • Persists agent memories          │    │
│    │ • Thread-based history │         │ • Cross-thread knowledge           │    │
│    │ • Enables resumption   │         │ • User preferences                 │    │
│    │ • Conversation replay  │         │ • Learned context                  │    │
│    └────────────────────────┘         └────────────────────────────────────┘    │
│                                                                                  │
│                         ┌─────────────────────────┐                             │
│                         │   AsyncConnectionPool   │                             │
│                         │   (psycopg3, max=20)    │                             │
│                         └─────────────────────────┘                             │
│                                     │                                           │
│                                     ▼                                           │
│                         ┌─────────────────────────┐                             │
│                         │    Supabase PostgreSQL  │                             │
│                         │    (with pgvector)      │                             │
│                         └─────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW OVERVIEW                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────────────┐
                        │     User Uploads        │
                        │   SP Group Utility Bill │
                        │       (Image/PDF)       │
                        └───────────┬─────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          1. OCR PROCESSING                                     │
│                                                                                │
│   ┌─────────────────┐    ┌──────────────────────┐    ┌────────────────────┐   │
│   │  Image Upload   │───▶│  OpenAI GPT-4o       │───▶│  Structured JSON   │   │
│   │  (Base64)       │    │  Vision Extraction   │    │  ElectricityBill   │   │
│   └─────────────────┘    │                      │    │  Extraction        │   │
│                          │  - Account info      │    └─────────┬──────────┘   │
│                          │  - Consumption kWh   │              │              │
│                          │  - Cost breakdown    │              │              │
│                          │  - Bar chart reading │              │              │
│                          │  - Trend analysis    │              │              │
│                          └──────────────────────┘              │              │
└────────────────────────────────────────────────────────────────┼──────────────┘
                                                                 │
                                    ┌────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          2. EMBEDDING & STORAGE                                │
│                                                                                │
│   ┌─────────────────┐    ┌──────────────────────┐    ┌────────────────────┐   │
│   │  Bill JSON      │───▶│  SeaLion Encoder     │───▶│  1024-dim Vector   │   │
│   │  Data           │    │  (ASEAN Multilingual)│    │  Embedding         │   │
│   └─────────────────┘    └──────────────────────┘    └─────────┬──────────┘   │
│                                                                │              │
│                                                                ▼              │
│                                                    ┌────────────────────────┐ │
│                                                    │  Supabase pgvector     │ │
│                                                    │  my_embeddings table   │ │
│                                                    │                        │ │
│                                                    │  - source_id           │ │
│                                                    │  - text_content (JSON) │ │
│                                                    │  - metadata            │ │
│                                                    │  - embedding (VECTOR)  │ │
│                                                    └────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          3. DIAGNOSIS & ANALYSIS                               │
│                                                                                │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │
│   │                    BillDiagnosisService                                  │ │
│   ├─────────────────────────────────────────────────────────────────────────┤ │
│   │                                                                          │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│   │  │   Anomaly    │  │  Efficiency  │  │    Trend     │  │   Personalized │ │
│   │  │  Detection   │  │   Analysis   │  │   Warnings   │  │   Recommendations│
│   │  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├─────────────┤  │ │
│   │  │ • Spike det. │  │ • vs National│  │ • Increasing │  │ • Energy tips│  │ │
│   │  │ • Z-score    │  │ • vs Neighbor│  │ • Decreasing │  │ • Appliance  │  │ │
│   │  │ • 95% CI     │  │ • % Deviation│  │ • Seasonal   │  │   upgrades   │  │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          4. ANALYTICS DASHBOARD                                │
│                                                                                │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│   │ District        │  │ Anomaly         │  │ Intervention    │               │
│   │ Heatmap         │  │ Detection       │  │ Tracking        │               │
│   │ (Leaflet)       │  │ (Stats)         │  │ (Before/After)  │               │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                                │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │
│   │                    StatisticalAnalyzer (SciPy)                           │ │
│   │                                                                          │ │
│   │  • Z-score calculation     • 95% confidence intervals                    │ │
│   │  • Outlier detection       • Cohort statistics                           │ │
│   │  • Trend analysis          • District aggregation                        │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Module Structure

```
VoltPulse-SG/
├── frontend/                          # Next.js 15 Application
│   ├── src/app/
│   │   ├── page.tsx                   # Landing page
│   │   ├── chat/page.tsx              # AI Chatbot interface
│   │   ├── upload/page.tsx            # Bill upload with dropzone
│   │   ├── analytics/                 # Urban planner dashboard
│   │   │   ├── page.tsx               # Main analytics view
│   │   │   └── components/            # Charts, heatmaps, stats
│   │   ├── api/                       # Next.js API routes (proxy)
│   │   │   ├── chat/route.ts          # → POST /chat
│   │   │   ├── ocr/route.ts           # → POST /ocr/*
│   │   │   └── analytics/route.ts     # → GET /analytics/*
│   │   └── components/                # Shared UI components
│   └── package.json
│
├── backend/                           # FastAPI Application
│   ├── app.py                         # Main FastAPI app & routes
│   ├── graph/                         # LangGraph orchestration
│   │   ├── builder.py                 # Graph construction
│   │   ├── state.py                   # TypedDict state schema
│   │   └── router.py                  # Conditional routing logic
│   ├── agents/                        # AI Agents
│   │   ├── classifier.py              # 5-category message classification
│   │   └── agentic_rag.py             # ReAct agent with 5 tools
│   ├── tools/                         # LangChain Tools (5 total)
│   │   ├── retailer_tools.py          # 4 core tools (consumption, retailers,
│   │   │                              #   energy ratings, ROI calculator)
│   │   └── web_search.py              # OpenAI web search tool
│   ├── services/                      # Business logic
│   │   ├── vision_extractor.py        # GPT-4o OCR
│   │   ├── bill_diagnosis.py          # Pattern detection
│   │   └── consumption_extractor.py   # Data extraction
│   ├── analytics/                     # Urban planner features
│   │   ├── router.py                  # Analytics API routes
│   │   └── services/                  # Stats, district, intervention
│   ├── encoders/                      # Embedding generation
│   │   └── sealion.py                 # SeaLion API client
│   ├── recommender/                   # Vector similarity
│   │   └── vector_store.py            # pgvector operations
│   └── models/                        # Pydantic schemas
│       ├── utility_bill.py            # Bill extraction schema
│       ├── diagnosis.py               # Diagnosis result schema
│       └── intervention.py            # Intervention tracking
│
└── Dockerfile                         # HF Spaces deployment
```

---

## 🔑 Key Integration Points

### LangGraph Configuration
```python
# Compiled graph with persistence
graph = graph_builder.compile(
    checkpointer=AsyncPostgresSaver(pool),  # Conversation memory
    store=AsyncPostgresStore(pool),          # Agent memory
)

# Invocation with thread tracking
config = {
    "configurable": {
        "thread_id": "user_123_thread_456",
        "user_id": "user_123"
    }
}
result = await graph.ainvoke({"messages": [user_msg]}, config)
```

### Vector Store Schema
```sql
CREATE TABLE my_embeddings (
    id SERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    text_content JSONB,
    metadata JSONB,
    embedding VECTOR(1024)
);
```

### Agent Tool Binding
```python
# Agentic RAG uses LangGraph's prebuilt ReAct agent with 5 tools
react_agent = create_react_agent(
    model=llm,
    tools=[
        get_user_consumption_info,        # RAG over user's uploaded bills
        get_energy_rating_info,           # Energy tick rating info
        calculate_appliance_roi,          # ROI for appliance upgrades
        search_appliance_recommendations, # OpenAI web search
        find_retailers_by_product,        # 700+ retailers (limit=800)
    ]
)
```
