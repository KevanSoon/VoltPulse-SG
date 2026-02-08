# Retailer Recommendation System Infrastructure

**VoltPulse SG - Climate Voucher Retailer Search**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Configuration](#configuration)
7. [Deployment](#deployment)
8. [Maintenance](#maintenance)

---

## Architecture Overview

The retailer recommendation system uses **semantic vector search** to match user queries with Climate Voucher participating retailers in Singapore.

### High-Level Architecture

```
User Query ("refrigerator shops in Bedok")
    ↓
Query Enhancement (synonyms, context)
    ↓
SeaLion Encoder (1024-dim embedding)
    ↓
Vector Database (PostgreSQL + pgvector)
    ↓
Similarity Search (L2 distance)
    ↓
Hybrid Scoring (semantic + product + location)
    ↓
Ranking & Filtering
    ↓
Top-K Retailer Results
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 15, React 19 | User interface |
| **API** | FastAPI (Python 3.13) | REST endpoints |
| **Embeddings** | SeaLion Encoder | 1024-dim vectors |
| **Vector DB** | PostgreSQL 17 + pgvector | Semantic search |
| **Database** | Supabase (managed PostgreSQL) | Cloud hosting |
| **Agent Framework** | LangGraph, LangChain | Agentic RAG |
| **LLM** | Ollama (GPT-OSS 120B) | Natural language |

---

## System Components

### 1. SeaLion Encoder (`backend/encoders/sealion.py`)

**Purpose**: Convert text to 1024-dimensional embeddings

**Architecture**:
```python
Text → SeaLion API → Feature Extraction → Vector Building → L2 Normalization
```

**Embedding Composition** (1024 dimensions):
- Dims 0-255: Text hash (SHA256-based semantic coverage)
- Dims 256-511: Cause categories (multi-hot encoding)
- Dims 512-527: Cause scores (0.0-1.0 values)
- Dims 528-537: ASEAN countries (one-hot)
- Dims 538-547: Languages (one-hot)
- Dims 548-553: Continuous scores (engagement, experience, consumption)
- Dims 558-577: Profile type encoding
- Dims 600-1023: Motivation themes hash

**API Endpoint**: `https://cf-sealion.mitrarahul2002.workers.dev`

**Configuration**:
```python
SEALION_ENDPOINT=https://cf-sealion.mitrarahul2002.workers.dev
```

### 2. Vector Store (`backend/recommender/vector_store.py`)

**Purpose**: Store and retrieve retailer embeddings from PostgreSQL

**Key Methods**:

```python
class VectorStore:
    async def store_embedding(form_id, form_type, embedding, form_data)
    async def find_similar(query_embedding, form_type, limit)
    async def find_by_form_type(form_type, limit)
    async def find_by_causes(target_causes, query_embedding, limit)
    async def get_embedding(form_id)
    async def count_by_type()
```

**Database Table**: `my_embeddings`

**Connection**: Uses `AsyncConnectionPool` from psycopg3

### 3. Retailer Data Model (`backend/services/retailer_loader.py`)

**ClimateVoucherRetailer**:
```python
@dataclass
class ClimateVoucherRetailer:
    serial_number: int
    retail_outlet: str           # Store name
    outlet_address: str          # Full address
    postal_code: str             # 6-digit Singapore postal
    planning_area: str           # Derived from postal code
    website: Optional[str]       # Retailer website
    eligible_products: List[str] # Product categories
    remarks: Optional[str]       # Special notes

    def to_embedding_text(self) -> str:
        """Generate text for embedding."""
        # Current implementation (needs improvement)
```

**Product Categories** (10 types):
1. `refrigerators`
2. `air_conditioners`
3. `dc_fans`
4. `led_lights`
5. `washing_machines`
6. `water_closets`
7. `sink_bib_taps_mixers`
8. `basin_taps_mixers`
9. `shower_taps_mixers`
10. `heat_pump_water_heaters`

### 4. Retailer Tools (`backend/tools/retailer_tools.py`)

**Available Tools** (LangChain tools for RAG):

1. **search_climate_voucher_retailers**
   - Semantic search with filters
   - Parameters: query, product_category, planning_area, limit
   - Returns: JSON list of retailers with similarity scores

2. **find_retailers_by_product**
   - Find all retailers selling a specific product
   - Parameters: product, limit
   - Returns: Filtered retailer list

3. **get_energy_rating_info**
   - Energy efficiency rating information
   - Parameters: product_type
   - Returns: Energy label guide

4. **calculate_appliance_roi**
   - ROI calculator for appliance upgrades
   - Parameters: product_type, current_rating, new_rating, price, apply_voucher
   - Returns: ROI analysis

5. **search_appliance_recommendations**
   - Web search for product recommendations
   - Parameters: appliance_type, context
   - Returns: Product suggestions with sources

### 5. Agentic RAG (`backend/agents/agentic_rag.py`)

**Purpose**: Autonomous agent that uses retailer tools to answer queries

**Architecture**:
```python
LangGraph ReAct Agent
    ├── System Prompt (grounding, step-by-step strategy)
    ├── Tools: 5 retailer tools
    ├── LLM: Ollama GPT-OSS 120B
    └── Memory: LangGraph store
```

**Workflow**:
1. Analyze user query
2. Search retailers via semantic search
3. Filter by product/location
4. Explain energy ratings if relevant
5. Calculate ROI if requested
6. Cite sources

---

## Data Flow

### Retailer Data Loading

```
Climate Voucher PDF
    ↓
PDF Parser (pdfplumber)
    ↓
ParsedRetailer objects (775 retailers)
    ↓
ClimateVoucherRetailer model
    ↓
Postal Code → Planning Area mapping
    ↓
to_embedding_text() → Rich text representation
    ↓
SeaLion Encoder → 1024-dim embedding
    ↓
VectorStore.store_embedding()
    ↓
PostgreSQL my_embeddings table
```

### Query Processing

```
User Query: "refrigerator shops in Bedok"
    ↓
Query Enhancement
    ├→ Add synonyms: "refrigerator fridge freezer"
    ├→ Add product: "Refrigerators"
    └→ Add location: "Bedok Singapore"
    ↓
Enhanced Query: "refrigerator fridge freezer Refrigerators Bedok Singapore"
    ↓
SeaLion Encoder → 1024-dim query embedding
    ↓
Vector Search: find_similar(form_type="retailer", limit=20)
    ↓
PostgreSQL: SELECT ... ORDER BY embedding <-> query_vector
    ↓
Results: Top-K retailers by L2 distance
    ↓
Post-Filtering
    ├→ Product filter: has "refrigerators"
    └→ Area filter: planning_area == "Bedok"
    ↓
Hybrid Scoring
    ├→ 0.5 * semantic_similarity
    ├→ 0.3 * product_match (0 or 1)
    └→ 0.2 * location_match (0 or 1)
    ↓
Re-rank by hybrid score
    ↓
Return Top-K retailers
```

---

## Database Schema

### Table: `my_embeddings`

```sql
CREATE TABLE my_embeddings (
    id SERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,           -- Unique retailer ID
    chunk_index INTEGER DEFAULT 0,     -- Always 0 for retailers
    text_content JSONB,                -- Full retailer data
    metadata JSONB,                    -- {"form_type": "retailer"}
    embedding VECTOR(1024)             -- pgvector embedding
);

-- Index for fast vector search
CREATE INDEX my_embeddings_embedding_idx
    ON my_embeddings
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);
```

### Retailer Document Structure (text_content)

```json
{
    "serial_number": 123,
    "retail_outlet": "Gain City (Ang Mo Kio Showroom)",
    "outlet_address": "8 Ang Mo Kio Industrial Park 2, Singapore 569500",
    "postal_code": "569500",
    "planning_area": "Ang Mo Kio",
    "district": "28",
    "website": "https://www.gaincity.com/",
    "eligible_products": [
        "refrigerators",
        "air_conditioners",
        "dc_fans",
        "led_lights",
        "washing_machines",
        "water_closets",
        "sink_bib_taps_mixers",
        "basin_taps_mixers",
        "shower_taps_mixers",
        "heat_pump_water_heaters"
    ],
    "remarks": "Accepts vouchers upon delivery",
    "source_type": "climate_voucher_retailer",
    "country": "SG"
}
```

### Metadata Structure

```json
{
    "form_type": "retailer"
}
```

---

## API Endpoints

### FastAPI Backend (`backend/app.py`)

**Base URL**: `http://localhost:7860`

#### 1. `/rag/search` (POST)

**Purpose**: Agentic RAG search for retailers

**Request**:
```json
{
    "query": "Where can I buy a refrigerator with Climate Vouchers?"
}
```

**Response**:
```json
{
    "response": "I found several Climate Voucher retailers selling refrigerators...",
    "tool_calls": ["search_climate_voucher_retailers", "get_energy_rating_info"],
    "message_count": 3
}
```

#### 2. `/rag/tools` (GET)

**Purpose**: List available retailer tools

**Response**:
```json
{
    "tools": [
        {
            "name": "search_climate_voucher_retailers",
            "description": "Search for Climate Voucher participating retailers..."
        },
        ...
    ],
    "total": 5
}
```

#### 3. `/health` (GET)

**Purpose**: Health check

**Response**:
```json
{
    "status": "healthy"
}
```

---

## Configuration

### Environment Variables (`.env`)

```env
# Supabase Database
SUPABASE_DB_HOST=aws-1-ap-south-1.pooler.supabase.com
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.xlsfdthtzpacjerutjyy
SUPABASE_DB_PASSWORD=<password>
SUPABASE_DB_SSLMODE=require

# SeaLion Encoder
SEALION_ENDPOINT=https://cf-sealion.mitrarahul2002.workers.dev

# Ollama LLM
OLLAMA_API_KEY=<api_key>

# OpenAI (for web search)
OPENAI_API_KEY=<api_key>
```

### Dependencies (`backend/requirements.txt`)

```txt
fastapi>=0.109.0
uvicorn>=0.27.0
psycopg[binary,pool]>=3.1.0
langchain
langgraph
langgraph-checkpoint-postgres
httpx>=0.24.0
numpy>=1.24.0
pdfplumber>=0.10.0
```

---

## Deployment

### Local Development

1. **Setup environment**:
```bash
cd VoltPulse-SG/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure `.env`**:
   - Copy environment variables from documentation
   - Update credentials for Supabase, SeaLion, Ollama

3. **Start backend**:
```bash
# Windows (with event loop fix)
python run.py

# Linux/Mac
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

4. **Verify**:
```bash
curl http://localhost:7860/health
curl http://localhost:7860/rag/tools
```

### Production Deployment

**Recommended**: Deploy on cloud platform with async support

**Options**:
1. **Railway** - Easy deployment for Python apps
2. **Render** - Free tier available
3. **Google Cloud Run** - Serverless containers
4. **AWS ECS** - Production-grade

**Docker Deployment**:
```dockerfile
# Already exists: backend/Dockerfile
FROM python:3.13-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "run.py"]
```

---

## Maintenance

### Regular Tasks

1. **Monitor retailer data** (quarterly):
   - Check for new Climate Voucher retailers
   - Update `FULL_RETAILER_DATA` in `pdf_retailer_parser.py`
   - Re-load retailer embeddings

2. **Check embedding quality** (monthly):
   - Run diagnostic tests
   - Monitor similarity scores
   - Verify search relevance

3. **Update planning area mapping** (as needed):
   - Singapore district changes are rare
   - Verify new postal codes map correctly

4. **Optimize vector index** (annually):
   - Tune IVFFlat parameters
   - Consider upgrading to HNSW index

### Monitoring Metrics

Track these KPIs:
- **Average similarity score** (target > 0.7)
- **Query latency** (target < 3s)
- **Top-5 precision** (target > 90%)
- **Zero-result queries** (target < 5%)
- **Planning area accuracy** (target 100%)

### Troubleshooting

**Issue**: Low similarity scores
- **Solution**: Improve embedding text in `to_embedding_text()`

**Issue**: Wrong planning areas
- **Solution**: Fix `DISTRICT_TO_PLANNING_AREA` mapping

**Issue**: Slow queries
- **Solution**: Optimize vector index, reduce limit

**Issue**: No results
- **Solution**: Check if data loaded, verify filters

---

## Performance Characteristics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| **Retailer Count** | 775 | 775 | Full dataset loaded |
| **Embedding Dimension** | 1024 | 1024 | Fixed by SeaLion |
| **Query Encoding** | 1-2s | <2s | SeaLion API latency |
| **Vector Search** | 100-500ms | <500ms | pgvector L2 distance |
| **Total Query Time** | 2-3s | <3s | End-to-end |
| **Semantic Quality** | 3/10 | 8/10 | Needs improvement |
| **Location Accuracy** | 0/10 | 9/10 | Mapping broken |
| **Top-5 Precision** | ~30% | >90% | With fixes |

---

## Key File Reference

| File | Purpose | LOC |
|------|---------|-----|
| `backend/app.py` | FastAPI server, endpoints | ~600 |
| `backend/encoders/sealion.py` | SeaLion encoder | ~400 |
| `backend/recommender/vector_store.py` | Vector database interface | ~400 |
| `backend/recommender/gis_recommender.py` | GIS-based client recommender | ~1100 |
| `backend/services/retailer_loader.py` | Retailer data model | ~400 |
| `backend/services/pdf_retailer_parser.py` | PDF parser + data | ~1200 |
| `backend/tools/retailer_tools.py` | LangChain retailer tools | ~430 |
| `backend/agents/agentic_rag.py` | Agentic RAG agent | ~280 |
| `backend/scripts/load_retailers_from_pdf.py` | Data loading script | ~120 |

---

## Summary

The retailer recommendation infrastructure is **well-designed and functional**. The database works, the embeddings are generated, and the tools are integrated. The main issues are **data quality** (planning areas) and **search relevance** (similarity scoring), which can be fixed with the improvements outlined in the diagnosis report.

With the recommended fixes, this system can achieve **8/10 recommendation quality** and provide excellent Climate Voucher retailer recommendations for Singapore households.
