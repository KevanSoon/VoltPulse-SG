# Data Flow Architecture

## Table of Contents
- [Overview](#overview)
- [Bill Upload & OCR Flow](#bill-upload--ocr-flow)
- [Analytics Dashboard Flow](#analytics-dashboard-flow)
- [Agentic RAG Chat Flow](#agentic-rag-chat-flow)
- [Retailer Recommendation Flow](#retailer-recommendation-flow)
- [Heatmap Analytics Flow](#heatmap-analytics-flow)
- [ROI Calculation Flow](#roi-calculation-flow)
- [Vector Search Flow](#vector-search-flow)
- [Memory & Persistence Flow](#memory--persistence-flow)
- [Error Handling](#error-handling)

---

## Overview

VoltPulse SG processes data through **8 primary flows**, each optimized for specific user journeys. Data moves from frontend → backend → AI services → database, with intelligent caching and state management.

### System-Wide Data Flow

```mermaid
---
id: 8f9e7d6a-5c4b-4a3e-9f2d-7e8a6c5b4d3f
---
graph TB
    subgraph Frontend
        A[User Browser] --> B[Next.js App]
    end

    subgraph Backend
        C[FastAPI] --> D[LangGraph]
        D --> E[Agentic RAG]
    end

    subgraph AI Services
        F[OpenAI Vision]
        G[Ollama LLM]
        H[SEALION Encoder]
    end

    subgraph Data Layer
        I[(PostgreSQL<br/>pgvector)]
        J[AsyncPostgresSaver]
        K[AsyncPostgresStore]
    end

    B -->|HTTP/REST| C
    C -->|OCR| F
    E -->|LLM Inference| G
    E -->|Embeddings| H
    E -->|Vector Search| I
    D -->|Checkpoints| J
    E -->|Memory| K
    I -->|Results| C
    C -->|JSON| B

    style Frontend fill:#61dafb,color:#000
    style Backend fill:#009688,color:#fff
    style AI Services fill:#ff9800,color:#fff
    style Data Layer fill:#3ecf8e,color:#fff
```

---

## Bill Upload & OCR Flow

### User Journey

1. User uploads SP Group utility bill (image/PDF)
2. Frontend sends to `/api/ocr/process`
3. Backend calls OpenAI Vision API (GPT-4o)
4. Structured data extracted and validated
5. Stored in PostgreSQL with `form_type=vision`
6. User redirected to Analytics Dashboard

### Detailed Sequence

```mermaid
---
id: 7e9f8d6a-5c4b-4a3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant OCR as VisionExtractor
    participant GPT as OpenAI GPT-4o
    participant DB as PostgreSQL

    U->>F: Upload bill image
    F->>F: Validate file (10MB max)
    F->>API: POST /ocr/process

    API->>OCR: process_bill(image_bytes)
    OCR->>OCR: Encode to Base64
    OCR->>GPT: Vision API call<br/>VISION_EXTRACTION_PROMPT

    GPT->>GPT: OCR + Chart Reading
    GPT-->>OCR: JSON response

    OCR->>OCR: Parse & Validate<br/>ElectricityBillExtraction

    OCR->>DB: INSERT INTO my_embeddings<br/>form_type='vision'
    DB-->>OCR: source_id

    OCR-->>API: OCR Result
    API-->>F: {source_id, extraction_data}

    F->>F: localStorage.setItem('ocr_source_id')
    F->>U: Redirect to /analytics
```

### Data Structures

**Request** (`POST /ocr/process`):
```typescript
{
  file: File  // multipart/form-data
}
```

**Response**:
```json
{
  "source_id": "uuid-v4-string",
  "form_data": {
    "form_type": "vision",
    "extraction_data": {
      "account_number": "1234567890",
      "consumption_kwh": 350.5,
      "total_amount": 95.50,
      "billing_period_start": "2024-10-01",
      "billing_period_end": "2024-10-31",
      "consumption_trends": [
        {
          "service_type": "Electricity",
          "monthly_data": [
            {"month": "JAN", "value": 320, "unit": "kWh"},
            {"month": "FEB", "value": 345, "unit": "kWh"}
          ],
          "national_average": 338,
          "neighbour_average": 300
        }
      ],
      "extraction_confidence": 0.92
    }
  },
  "created_at": "2024-11-15T10:30:00Z"
}
```

**Database Record**:
```sql
INSERT INTO my_embeddings (source_id, text_content, metadata, embedding)
VALUES (
    'uuid-here',
    '{"consumption_kwh": 350.5, "total_amount": 95.50, ...}'::jsonb,
    '{"form_type": "vision", "account_number": "****7890"}'::jsonb,
    NULL  -- No embedding for vision bills
);
```

**File**: `backend/app.py` (OCR endpoint), `backend/services/vision_extractor.py`

---

## Analytics Dashboard Flow

### User Journey

1. User navigates to `/analytics`
2. Frontend fetches OCR results from `source_id`
3. If diagnosis exists, display; else run diagnosis
4. Render consumption charts, stats, heatmap

### Detailed Sequence

```mermaid
---
id: 6d8f9e7a-5c4b-4a3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant DIAG as BillDiagnosis
    participant STAT as StatisticalAnalyzer
    participant DB as PostgreSQL

    U->>F: Navigate to /analytics
    F->>F: Read localStorage('ocr_source_id')
    F->>API: GET /ocr/results/{source_id}

    API->>DB: SELECT FROM my_embeddings
    DB-->>API: Bill data + diagnosis

    alt Diagnosis exists
        API-->>F: Full bill + diagnosis
    else No diagnosis
        API->>DIAG: diagnose_bill(bill_data)
        DIAG->>STAT: calculate_cohort_statistics()
        STAT-->>DIAG: CohortStats

        DIAG->>DIAG: detect_anomalies()
        DIAG->>DIAG: analyze_efficiency()
        DIAG->>DIAG: calculate_health_score()

        DIAG->>DB: UPDATE diagnosis
        DIAG-->>API: DiagnosisResult

        API-->>F: Full bill + new diagnosis
    end

    F->>F: Transform data for charts
    F->>U: Render dashboard<br/>Stats | Charts | Diagnosis
```

### Data Transformation

**Backend Response**:
```json
{
  "form_data": {
    "extraction_data": { ... },
    "diagnosis": {
      "overall_health_score": 75,
      "health_grade": "B",
      "anomalies": [
        {
          "severity": "MEDIUM",
          "message": "Consumption 25% above average",
          "z_score": 2.3,
          "p_value": 0.021
        }
      ],
      "efficiency_issues": [ ... ],
      "recommendations": [ ... ]
    }
  }
}
```

**Frontend Transformation**:
```typescript
// Transform for Recharts
const monthlyData = bill.consumption_trends[0].monthly_data.map(m => ({
  month: m.month,
  consumption: m.value,
  average: bill.consumption_trends[0].national_average
}));

// Calculate stats
const currentUsage = bill.consumption_kwh;
const nationalAverage = bill.consumption_trends[0].national_average;
const vsNational = ((currentUsage - nationalAverage) / nationalAverage) * 100;
```

**File**: `frontend/src/app/analytics/page.tsx:44-62,234-246`

---

## Agentic RAG Chat Flow

### User Journey

1. User types question in chat interface
2. Frontend streams to `/chat`
3. LangGraph routes through Classifier → Agentic RAG
4. Agent selects tools, executes, synthesizes response
5. Conversation stored in checkpoints + memory

### Detailed Sequence

```mermaid
---
id: 5c8d9f7e-6a4b-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant G as LangGraph
    participant CLS as Classifier
    participant AGT as AgenticRAG
    participant LLM as Ollama
    participant TOOLS as Tools
    participant DB as PostgreSQL

    U->>F: Type: "Show my consumption"
    F->>API: POST /chat<br/>{message, user_id, thread_id}

    API->>G: invoke(state, config)
    G->>CLS: classify_query(message)
    CLS->>LLM: Classify into 5 categories
    LLM-->>CLS: "consumption_analysis"
    CLS-->>G: tool_hint

    G->>AGT: agentic_rag(state)
    AGT->>AGT: retrieve_memories()
    AGT->>DB: Semantic search memories
    DB-->>AGT: Past conversations

    AGT->>LLM: ReAct loop start<br/>Thought → Action
    LLM-->>AGT: Action: get_user_consumption_info

    AGT->>TOOLS: get_user_consumption_info(user_id)
    TOOLS->>DB: SELECT consumption data
    DB-->>TOOLS: Bill records
    TOOLS-->>AGT: Observation: "350.5 kWh"

    AGT->>LLM: Continue ReAct<br/>Observation → Thought
    LLM-->>AGT: Final Answer

    AGT->>DB: Store memory<br/>"User asked about consumption"
    AGT-->>G: Response

    G->>DB: Save checkpoint
    G-->>API: Stream response

    API-->>F: Server-Sent Events (SSE)
    F->>U: Display response
```

### Request/Response

**Request** (`POST /chat`):
```json
{
  "message": "What's my electricity consumption?",
  "user_id": "user-123",
  "thread_id": "thread-456"
}
```

**Response** (Server-Sent Events):
```
data: {"type": "start"}

data: {"type": "chunk", "content": "Your"}

data: {"type": "chunk", "content": " electricity"}

data: {"type": "chunk", "content": " consumption"}

data: {"type": "chunk", "content": " for October 2024 is **350.5 kWh**."}

data: {"type": "end"}
```

**Memory Storage**:
```python
await store.aput(
    namespace=("memories", user_id),
    key=f"memory-{timestamp}",
    value={
        "data": "User asked about consumption. Responded with 350.5 kWh for October 2024.",
        "timestamp": "2024-11-15T10:30:00Z"
    }
)
```

**File**: `backend/app.py:chat endpoint`, `backend/graph/builder.py`, `backend/agents/agentic_rag.py`

---

## Retailer Recommendation Flow

### User Journey

1. User asks "Find aircon retailers near Bedok"
2. Agent calls `find_retailers_by_product` tool
3. Product normalized, location extracted
4. Vector search on retailer embeddings
5. Product/location filtering
6. Top 10 results returned

### Detailed Sequence

```mermaid
---
id: 4d7c9f8e-6a5b-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant AGT as AgenticRAG
    participant TOOL as find_retailers_by_product
    participant NORM as Normalizer
    participant ENC as SEALIONEncoder
    participant VS as VectorStore
    participant DB as PostgreSQL

    AGT->>TOOL: find_retailers_by_product<br/>("aircon", "Bedok")

    TOOL->>NORM: normalize_product("aircon")
    NORM-->>TOOL: "air_conditioners"

    TOOL->>ENC: encode(query_dict)
    ENC->>ENC: LLM analysis<br/>Extract features
    ENC->>ENC: Construct 1024-dim vector
    ENC-->>TOOL: query_embedding

    TOOL->>VS: find_similar(embedding, form_type='retailer')
    VS->>DB: SELECT ... ORDER BY embedding <-> query::vector

    DB-->>VS: 800 retailers (L2 distance)
    VS-->>TOOL: Candidates

    TOOL->>TOOL: Filter by products<br/>("air_conditioners")
    TOOL->>TOOL: Filter by location<br/>("Bedok")

    TOOL->>TOOL: Format results (Top 10)
    TOOL-->>AGT: JSON with retailers

    AGT->>AGT: Format for user
    AGT->>User: "Here are 10 retailers..."
```

### Data Flow Details

**Tool Call**:
```python
@tool
def find_retailers_by_product(
    product: str,  # "aircon"
    location: str = ""  # "Bedok"
) -> str:
```

**Product Normalization**:
```python
# Input: "aircon", "air conditioner", "AC"
# Output: "air_conditioners"
normalized = PRODUCT_ALIASES.get(product.lower(), product)
```

**SEALION Encoding**:
```python
query_dict = {
    "causes": ["air_conditioners"],
    "country_codes": ["SG"],
    "languages": ["en"],
    "text": f"air conditioner retailer in Bedok Singapore"
}
embedding = await encoder.encode(query_dict)  # 1024-dim vector
```

**Vector Search**:
```sql
SELECT source_id, text_content, metadata, embedding <-> %s::vector AS distance
FROM my_embeddings
WHERE metadata->>'form_type' = 'retailer'
ORDER BY distance ASC
LIMIT 800;
```

**Filtering**:
```python
# Product filter
matches = [r for r in candidates if "air_conditioners" in r.products]

# Location filter (text-based, NOT RRF)
if "bedok" in location.lower():
    matches = [r for r in matches if "bedok" in r.address.lower()]
```

**Output** (to user):
```
Here are 10 authorized Climate Voucher retailers selling air conditioners near Bedok:

1. **Gain City** - 201 Victoria Street #01-23 Singapore 188067
   Products: Air-conditioners, Refrigerators, Washing Machines
   Distance: 0.12 (High relevance)

2. **Courts** - 321 Clementi Ave 3 #01-01 Singapore 129905
   ...
```

**File**: `backend/tools/retailer_tools.py:251-357`

---

## Heatmap Analytics Flow

### User Journey

1. User switches to Heatmap view
2. Frontend fetches GeoJSON from data.gov.sg
3. Backend aggregates district consumption
4. Map renders with color-coded districts
5. Click district for details

### Detailed Sequence

```mermaid
---
id: 3c8e9f7d-6a5b-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant U as User
    participant F as Frontend/Map
    participant GOV as data.gov.sg API
    participant API as FastAPI
    participant AGG as DistrictAggregator
    participant DB as PostgreSQL

    U->>F: Click "Heatmap" view

    par Fetch GeoJSON
        F->>GOV: GET planning area dataset
        GOV-->>F: GeoJSON (55 areas)
    and Fetch Consumption Data
        F->>API: GET /analytics/heatmap
        API->>AGG: aggregate_by_district()

        AGG->>DB: SELECT all bills
        DB-->>AGG: Bill records

        AGG->>AGG: Extract postal codes
        AGG->>AGG: Group by district (first 2 digits)
        AGG->>AGG: Calculate stats (mean, median)

        AGG->>AGG: Normalize intensity
        AGG-->>API: Heatmap points

        API-->>F: [{district, lat, lng, consumption, intensity}]
    end

    F->>F: Render Leaflet map
    F->>F: Apply color scale<br/>(<300=teal, >450=red)
    F->>U: Interactive map

    U->>F: Click district
    F->>F: Show popup<br/>Details panel
```

### Data Aggregation

**District Grouping**:
```python
# Input: Bills with addresses
bills = [
    {"premise_address": "BLK 123 BEDOK NORTH #05-67 S(460123)", "consumption_kwh": 350},
    {"premise_address": "456 ORCHARD ROAD #12-34 S(238888)", "consumption_kwh": 280},
    ...
]

# Extract postal codes
postal_codes = [
    extract_postal_code(bill["premise_address"]) for bill in bills
]  # ["460123", "238888", ...]

# Group by district (first 2 digits)
districts = defaultdict(list)
for bill, postal in zip(bills, postal_codes):
    if postal:
        district = postal[:2]  # "46", "23"
        districts[district].append(bill["consumption_kwh"])
```

**Statistics Calculation**:
```python
for district, consumptions in districts.items():
    result[district] = {
        "postal_district": district,
        "household_count": len(consumptions),
        "average_consumption_kwh": np.mean(consumptions),
        "median_consumption_kwh": np.median(consumptions),
        "min_consumption_kwh": np.min(consumptions),
        "max_consumption_kwh": np.max(consumptions)
    }
```

**Intensity Normalization**:
```python
max_consumption = max(d["average_consumption_kwh"] for d in districts.values())

for district in districts.values():
    district["intensity"] = district["average_consumption_kwh"] / max_consumption
    # intensity ∈ [0, 1]
```

**Color Mapping** (Frontend):
```typescript
function getConsumptionColor(consumption: number): string {
    if (consumption === 0) return "#d1d5db";  // gray
    if (consumption < 300) return "#14b8a6";  // teal
    if (consumption < 350) return "#22c55e";  // green
    if (consumption < 400) return "#eab308";  // yellow
    if (consumption < 450) return "#f97316";  // orange
    return "#ef4444";  // red
}
```

**File**: `backend/analytics/services/district.py:257-402`, `frontend/src/app/analytics/components/SingaporeHeatmap.tsx`

---

## ROI Calculation Flow

### User Journey

1. User selects appliance type (e.g., "Air-conditioner")
2. Inputs current rating (1-tick) and new rating (5-tick)
3. Inputs price ($1,500)
4. Backend calculates ROI with Climate Voucher
5. Returns payback period, savings, 10-year benefit

### Detailed Sequence

```mermaid
---
id: 2b7e9d8f-6a5c-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant U as User
    participant F as Frontend/ROI
    participant API as FastAPI
    participant CALC as ROICalculator
    participant DATA as ENERGY_CONSUMPTION_DATA

    U->>F: Select "Air-conditioner"<br/>Current: 1-tick<br/>New: 5-tick<br/>Price: $1,500

    F->>API: POST /retailers/roi/calculate

    API->>CALC: calculate(product, 1, 5, 1500)

    CALC->>CALC: normalize_product("air-conditioner")
    CALC->>DATA: Lookup consumption by tick
    DATA-->>CALC: 1-tick: 1200 kWh<br/>5-tick: 700 kWh

    CALC->>CALC: annual_savings = (1200-700) × $0.36
    CALC->>CALC: annual_savings = 500 × $0.36 = $180

    CALC->>CALC: Check voucher eligibility<br/>5-tick >= 3-tick ✓
    CALC->>CALC: voucher_amount = min($300, $1500) = $300

    CALC->>CALC: net_cost = $1500 - $300 = $1200

    CALC->>CALC: payback_years = $1200 / $180 = 6.7 years

    CALC->>CALC: net_benefit_10_years<br/>= ($180 × 10) - $1200<br/>= $600

    CALC->>CALC: roi_percent = ($180 / $1200) × 100 = 15%

    CALC-->>API: ROIResult

    API-->>F: JSON response

    F->>U: Display:<br/>- Payback: 6.7 years<br/>- Annual savings: $180<br/>- 10-year benefit: $600<br/>- ROI: 15%
```

### Data Structures

**Request**:
```json
{
  "product_type": "air_conditioners",
  "current_rating": 1,
  "new_rating": 5,
  "product_price": 1500,
  "apply_voucher": true
}
```

**Energy Data Lookup**:
```python
ENERGY_CONSUMPTION_DATA = {
    "air_conditioners": {
        "consumption_by_tick": {
            1: 1200,  # kWh/year
            2: 1050,
            3: 920,
            4: 800,
            5: 700
        },
        "min_voucher_tick": 3,
        "typical_price_range": (599, 2500)
    }
}
```

**Response**:
```json
{
  "product_type": "air_conditioners",
  "product_display_name": "Air-conditioner",
  "current_rating": 1,
  "new_rating": 5,
  "tick_improvement": 4,
  "product_price": 1500.0,
  "voucher_amount": 300.0,
  "net_cost": 1200.0,
  "annual_energy_savings_kwh": 500.0,
  "annual_savings_sgd": 180.0,
  "monthly_savings_sgd": 15.0,
  "payback_period_months": 80,
  "payback_period_years": 6.7,
  "net_benefit_5_years": -300.0,
  "net_benefit_10_years": 600.0,
  "roi_percent_annual": 15.0,
  "is_voucher_eligible": true,
  "notes": [
    "This air-conditioner qualifies for the $300 Climate Voucher!",
    "Tip: Set temperature to 25°C for additional savings."
  ]
}
```

**File**: `backend/services/roi_calculator.py:155-255`

---

## Vector Search Flow

### Embedding Creation Flow

```mermaid
---
id: 1a8e9f7d-6b5c-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant SYS as System
    participant ENC as SEALIONEncoder
    participant LLM as SEALION API
    participant VS as VectorStore
    participant DB as PostgreSQL

    SYS->>ENC: encode(retailer_data)

    ENC->>LLM: POST /chat<br/>Analysis prompt
    LLM->>LLM: Extract features
    LLM-->>ENC: JSON response

    ENC->>ENC: Parse features
    ENC->>ENC: Construct 1024-dim vector<br/>- [0-255]: Text hash<br/>- [256-511]: Causes<br/>- [512-527]: Scores<br/>...

    ENC-->>SYS: embedding (1024-dim)

    SYS->>VS: store(source_id, content, embedding)

    VS->>DB: INSERT INTO my_embeddings
    DB-->>VS: Success

    VS->>DB: CREATE INDEX ivfflat
    DB-->>VS: Index created
```

### Search Flow

```mermaid
---
id: 0d9e8f7c-6a5b-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant Q as Query
    participant ENC as SEALIONEncoder
    participant VS as VectorStore
    participant DB as PostgreSQL
    participant RES as Results

    Q->>ENC: encode(query)
    ENC-->>Q: query_embedding (1024-dim)

    Q->>VS: find_similar(query_embedding, limit=10)

    VS->>DB: SELECT ...<br/>ORDER BY embedding <-> %s::vector

    Note over DB: IVFFlat index used<br/>for fast ANN search

    DB-->>VS: Top 10 matches<br/>(with L2 distances)

    VS->>VS: Convert distance to similarity<br/>similarity = 1 / (1 + distance)

    VS-->>RES: Ranked results
```

**SQL Query**:
```sql
SELECT
    source_id,
    text_content,
    metadata,
    embedding <-> %s::vector AS distance
FROM my_embeddings
WHERE metadata->>'form_type' = %s
ORDER BY distance ASC
LIMIT %s;
```

**File**: `backend/recommender/vector_store.py:200-271`

---

## Memory & Persistence Flow

### Checkpoint Flow (Conversation State)

```mermaid
---
id: f8e9d7c6-5a4b-4c3e-9f2d-8e7a6c5b4d3f
---
graph LR
    A[User Message] --> B[LangGraph Invoke]
    B --> C[State Update]
    C --> D[AsyncPostgresSaver]
    D --> E[(langgraph_checkpoints)]

    E --> F[Resume Conversation]
    F --> B

    style E fill:#3ecf8e
```

**Checkpoint Table**:
```sql
CREATE TABLE langgraph_checkpoints (
    thread_id TEXT,
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    checkpoint BYTEA,  -- Serialized state
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

**Usage**:
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver(pool)

# Save checkpoint
graph = graph.compile(checkpointer=checkpointer)

# Resume from checkpoint
config = {"configurable": {"thread_id": "thread-123"}}
result = await graph.ainvoke({"messages": [...]}, config)
```

### Memory Flow (Semantic Storage)

```mermaid
---
id: e7f9d8c6-5b4a-4c3e-9f2d-8e7a6c5b4d3f
---
sequenceDiagram
    participant AGT as AgenticRAG
    participant STORE as AsyncPostgresStore
    participant DB as PostgreSQL

    AGT->>AGT: Before responding<br/>retrieve_memories(query)

    AGT->>STORE: asearch(namespace, query)
    STORE->>DB: Semantic search<br/>in langgraph_store
    DB-->>STORE: Top 5 memories
    STORE-->>AGT: Memory contexts

    AGT->>AGT: Generate response<br/>with memory context

    AGT->>STORE: aput(namespace, key, value)
    STORE->>DB: INSERT new memory
    DB-->>STORE: Success
```

**Memory Storage**:
```python
await store.aput(
    namespace=("memories", user_id),
    key=f"memory-{uuid.uuid4()}",
    value={
        "data": "User asked about consumption. Current usage is 350.5 kWh.",
        "timestamp": datetime.now().isoformat()
    }
)
```

**Memory Retrieval**:
```python
memories = await store.asearch(
    namespace=("memories", user_id),
    query="consumption usage electricity",
    limit=5
)

context = "\n".join([m.value["data"] for m in memories])
```

**File**: `backend/agents/agentic_rag.py:140-180`

---

## Error Handling

### Error Flow

```mermaid
---
id: d6e9f8c7-5a4b-4c3e-9f2d-8e7a6c5b4d3f
---
graph TB
    A[Request] --> B{Validation}
    B -->|Valid| C[Process]
    B -->|Invalid| D[400 Bad Request]

    C --> E{External API}
    E -->|Success| F[Return Result]
    E -->|Timeout| G[504 Gateway Timeout]
    E -->|Error| H[Retry Logic]

    H --> I{Retry Count}
    I -->|< Max| E
    I -->|≥ Max| J[500 Internal Error]

    C --> K{Database}
    K -->|Success| F
    K -->|Connection Error| L[503 Service Unavailable]

    style D fill:#ffcdd2
    style G fill:#ffccbc
    style J fill:#ef5350,color:#fff
    style L fill:#ff9800,color:#fff
```

### Error Response Format

**Standard Error**:
```json
{
  "detail": "Error message",
  "status_code": 500,
  "timestamp": "2024-11-15T10:30:00Z"
}
```

**Validation Error** (Pydantic):
```json
{
  "detail": [
    {
      "loc": ["body", "consumption_kwh"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Retry Logic** (Vision OCR):
```python
async def extract_with_retry(
    image_bytes: bytes,
    max_retries: int = 2
) -> ElectricityBillExtraction:
    for attempt in range(max_retries + 1):
        try:
            result = await self.extract_from_bytes(image_bytes)
            if result.extraction_confidence > 0.3:
                return result
        except Exception as e:
            if attempt < max_retries:
                continue
            # Return error result on final attempt
            return ElectricityBillExtraction(
                extraction_confidence=0.0,
                extraction_warnings=[f"Failed after {max_retries+1} attempts: {str(e)}"]
            )
```

**File**: `backend/services/vision_extractor.py:274-310`

---

## Summary

VoltPulse SG's data flows are optimized for:

### ✅ Performance
- **Async I/O** - Non-blocking database/API calls
- **Connection Pooling** - Reuse database connections
- **Vector Indexing** - IVFFlat for fast ANN search
- **Caching** - 15-minute TTL for web search

### ✅ Reliability
- **Retry Logic** - OCR extraction, API calls
- **Checkpointing** - Resume interrupted conversations
- **Error Handling** - Graceful degradation
- **Validation** - Pydantic models at every boundary

### ✅ Scalability
- **Stateless APIs** - Horizontal scaling ready
- **Managed Services** - Supabase, Ollama cloud
- **Efficient Queries** - Index-optimized SQL
- **Streaming Responses** - SSE for chat

**Total Data Flows**: 8 primary flows covering all user journeys

**Related Documentation**:
- [System Overview](./overview.md) - High-level architecture
- [Tech Stack](./tech-stack.md) - Technology details
- [LangGraph Orchestration](../02-core-systems/langgraph-orchestration.md) - Graph execution
- [Vector Database](../02-core-systems/vector-database.md) - Storage layer
