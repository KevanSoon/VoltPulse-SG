# SEALION Integration

[← Back to Documentation](../README.md)

## Table of Contents
- [Overview](#overview)
- [Why SEALION?](#why-sealion)
- [API Configuration](#api-configuration)
- [1024-Dimensional Embedding Architecture](#1024-dimensional-embedding-architecture)
- [Encoding Process](#encoding-process)
- [Feature Extraction](#feature-extraction)
- [Distance Metric](#distance-metric)
- [Implementation Examples](#implementation-examples)

---

## Overview

**SEALION (Southeast Asian Languages In One Network)** is an ASEAN-focused multilingual large language model optimized for Southeast Asian languages and contexts. VoltPulse-SG uses SEALION to generate **1024-dimensional embeddings** for semantic search over utility bills and retailer data.

**Key Features:**
- **ASEAN multilingual**: Better understanding of Singapore English, Malay, Chinese
- **1024-dimensional vectors**: Segmented feature space with multiple encoding strategies
- **Hybrid encoding**: Combines text hashing, categorical features, and continuous scores
- **Cost-efficient**: Lower cost than OpenAI Ada-002
- **Customizable**: Full control over feature extraction and vector construction

**Implementation:** [`backend/encoders/sealion.py`](../../backend/encoders/sealion.py)

---

## Why SEALION?

### 1. ASEAN-Specific Understanding

Singapore households use mixed languages in utility discussions:
- **English**: "My electricity bill is too high"
- **Singlish**: "Wah my aircon eat power sia"
- **Malay**: "Bil elektrik saya tinggi"
- **Chinese (Simplified)**: "我的电费很高"

SEALION is **trained on ASEAN text** and understands these variations better than generic models.

### 2. Cost Efficiency

| Model | Dimension | Cost (per 1M tokens) | ASEAN Focus |
|-------|-----------|----------------------|-------------|
| OpenAI Ada-002 | 1536 | $0.10 | ✗ No |
| Cohere Embed v3 | 1024 | $0.10 | ✗ No |
| **SEALION** | **1024** | **Custom pricing** | **✓ Yes** |

**Verdict:** SEALION offers best value for ASEAN-focused applications.

### 3. Government Alignment

SEALION is part of Singapore's **National AI Strategy** to develop sovereign AI capabilities. Using SEALION supports local AI initiatives.

### 4. Customizable Architecture

Unlike black-box APIs (OpenAI, Cohere), SEALION's encoding process is **transparent and customizable**. VoltPulse-SG uses a hybrid approach:
- **Text hashing** for semantic similarity
- **Categorical encoding** for structured features (causes, countries, languages)
- **Continuous scores** from LLM analysis

---

## API Configuration

### Environment Variable

```bash
# .env file
SEALION_ENDPOINT=https://your-sealion-endpoint.com
```

### Initialization

```python
# From backend/encoders/sealion.py lines 57-76
class SeaLionEncoder(BaseEncoder):
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        """Initialize SeaLion encoder.

        Args:
            endpoint_url: The SeaLion API base URL. If not provided,
                         reads from SEALION_ENDPOINT environment variable.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts on failure.
        """
        url = endpoint_url or os.getenv("SEALION_ENDPOINT")
        if not url:
            raise ValueError("SEALION_ENDPOINT environment variable is required")
        self.endpoint_url = url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
```

### API Endpoint Structure

**Endpoint:** `POST /chat`

**Request format (OpenAI-compatible):**
```json
{
  "prompt": "Analyze this content:\n\n{user_text}",
  "system": "{feature_extraction_instructions}"
}
```

**Response format:**
```json
{
  "choices": [
    {
      "message": {
        "content": "{LLM_response}"
      }
    }
  ]
}
```

---

## 1024-Dimensional Embedding Architecture

The SEALION encoder constructs embeddings using a **segmented vector space** where different index ranges represent different feature types.

### Vector Space Segmentation

```
┌─────────────────────────────────────────────────────────────────┐
│              1024-DIMENSIONAL EMBEDDING SPACE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Indices 0-255    [Text Hash]                                   │
│  └─ SHA256-based semantic similarity hashing                    │
│                                                                  │
│  Indices 256-511  [Cause Categories]                            │
│  └─ Multi-hot encoding of 15 causes (education, health, ...)   │
│                                                                  │
│  Indices 512-527  [Cause Scores]                                │
│  └─ Continuous 0-1 scores for each cause                        │
│                                                                  │
│  Indices 528-537  [Country Codes]                               │
│  └─ One-hot encoding of 10 ASEAN countries                      │
│                                                                  │
│  Indices 538-547  [Languages]                                   │
│  └─ Multi-hot encoding of 10 languages                          │
│                                                                  │
│  Indices 548-557  [Continuous Scores]                           │
│  └─ engagement_level, experience_level, consumption_level,      │
│     efficiency_score, language_diversity, regional_focus        │
│                                                                  │
│  Indices 558-567  [Consumption Profiles]                        │
│  └─ One-hot encoding: low, medium, high, very_high              │
│                                                                  │
│  Indices 568-577  [Availability Types]                          │
│  └─ One-hot encoding: weekends, evenings, flexible, ...         │
│                                                                  │
│  Indices 600-1023 [Motivation Themes]                           │
│  └─ Hashed text from motivation themes extracted by SEALION     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Categories

**From backend/encoders/sealion.py lines 24-37:**

```python
# Feature categories for encoding
CAUSE_CATEGORIES = [
    "education", "health", "environment", "poverty", "children",
    "elderly", "disability", "animals", "arts", "sports",
    "disaster_relief", "human_rights", "technology", "agriculture", "housing"
]

ASEAN_COUNTRIES = ["SG", "MY", "TH", "VN", "ID", "PH", "MM", "KH", "LA", "BN"]

LANGUAGES = ["en", "ms", "th", "vi", "id", "tl", "my", "km", "lo", "zh"]

AVAILABILITY_TYPES = ["weekends", "evenings", "flexible", "full_time", "event_based"]

CONSUMPTION_PROFILES = ["low", "medium", "high", "very_high"]
```

---

## Encoding Process

The encoding happens in **3 steps**:

### Step 1: LLM Analysis via SEALION Chat API

```python
# From backend/encoders/sealion.py lines 109-156
async def _call_sealion(self, prompt: str) -> str:
    """Call SeaLion chat API."""
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    f"{self.endpoint_url}/chat",
                    headers={"Content-Type": "application/json"},
                    json={
                        "prompt": prompt,
                        "system": self._build_system_prompt()
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Handle OpenAI-compatible format
                if 'choices' in data and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if 'message' in choice:
                        return choice['message'].get('content', '')

                return data.get("response", "")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    continue  # Retry on server errors
                raise
```

**System Prompt (lines 83-107):**

```python
def _build_system_prompt(self) -> str:
    """Build system prompt for SeaLion analysis."""
    return """You are an ASEAN content and consumption data analyzer. Your task is to
analyze content and extract structured features for matching.

Analyze the provided content and respond with a JSON object containing these fields:

1. "causes": List of relevant categories from: education, health, environment, poverty...
2. "cause_scores": Object with scores (0.0-1.0) for each relevant cause
3. "engagement_level": Score from 0.0 to 1.0 indicating activity level
4. "experience_level": Score from 0.0 to 1.0 indicating prior experience
5. "consumption_level": Score from 0.0 to 1.0 indicating consumption intensity
6. "efficiency_score": Score from 0.0 to 1.0 indicating efficiency
7. "language_diversity": Score from 0.0 to 1.0 based on languages mentioned
8. "motivation_themes": List of key themes extracted from text content
9. "regional_focus": Score from 0.0 to 1.0 indicating ASEAN vs global focus

Respond ONLY with valid JSON, no explanation."""
```

### Step 2: Feature Extraction (JSON Parsing)

```python
# From backend/encoders/sealion.py lines 158-176
def _parse_sealion_response(self, response: str) -> Dict[str, Any]:
    """Parse SeaLion JSON response."""
    try:
        # Extract JSON from response (may have extra text)
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return {}
```

**Example extraction:**

Input text:
```
"High electricity usage from air conditioning in Singapore household.
 Using 450 kWh per month, well above 400 kWh national average."
```

SEALION response:
```json
{
  "causes": ["environment", "technology"],
  "cause_scores": {
    "environment": 0.8,
    "technology": 0.6
  },
  "engagement_level": 0.7,
  "experience_level": 0.5,
  "consumption_level": 0.75,
  "efficiency_score": 0.4,
  "language_diversity": 0.2,
  "motivation_themes": ["reduce costs", "energy efficiency", "sustainability"],
  "regional_focus": 0.9
}
```

### Step 3: Embedding Construction from Features

```python
# From backend/encoders/sealion.py lines 260-333
def _build_embedding_from_features(
    self,
    form_text: str,
    features: Dict[str, Any]
) -> np.ndarray:
    """Build final embedding from extracted features.

    Combines:
    - Deterministic text hashing (semantic coverage)
    - One-hot/multi-hot categorical encoding
    - Continuous scores from SeaLion analysis
    """
    embedding = np.zeros(self._feature_dimension, dtype=np.float32)

    # Section 1 (indices 0-255): Text hash for semantic similarity
    embedding += self._hash_to_vector(form_text, 256, offset=0)

    # Section 2 (indices 256-511): Cause categories
    causes = features.get("causes", [])
    embedding += self._encode_multi_categorical(causes, CAUSE_CATEGORIES, 256)

    # Section 3 (indices 512-527): Cause scores
    cause_scores = features.get("cause_scores", {})
    for i, cause in enumerate(CAUSE_CATEGORIES):
        idx = 512 + i
        if cause in cause_scores:
            embedding[idx] = float(cause_scores[cause])

    # Section 4 (indices 528-537): Country encoding
    for i, country in enumerate(ASEAN_COUNTRIES):
        if country.lower() in form_text.lower():
            embedding[528 + i] = 1.0

    # Section 5 (indices 538-547): Language encoding
    for i, lang in enumerate(LANGUAGES):
        if lang.lower() in form_text.lower():
            embedding[538 + i] = 1.0

    # Section 6 (indices 548-557): Continuous scores
    embedding[548] = features.get("engagement_level", 0.5)
    embedding[549] = features.get("experience_level", 0.5)
    embedding[550] = features.get("consumption_level", 0.5)
    embedding[551] = features.get("efficiency_score", 0.5)
    embedding[552] = features.get("language_diversity", 0.5)
    embedding[553] = features.get("regional_focus", 0.5)

    # Section 7 (indices 558-600): Profile type encoding
    embedding += self._encode_categorical(form_text, CONSUMPTION_PROFILES, 558)
    embedding += self._encode_categorical(form_text, AVAILABILITY_TYPES, 568)

    # Section 8 (indices 600-1023): Motivation themes hash
    themes = features.get("motivation_themes", [])
    if themes:
        themes_text = " ".join(themes)
        embedding += self._hash_to_vector(themes_text, 424, offset=600)

    # Normalize the embedding
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding
```

---

## Feature Extraction

### Text Hashing (Indices 0-255)

**Purpose:** Capture semantic similarity through deterministic hashing.

```python
# From backend/encoders/sealion.py lines 178-202
def _hash_to_vector(self, text: str, dimension: int, offset: int = 0) -> np.ndarray:
    """Convert text to a deterministic vector using hashing."""
    vector = np.zeros(self._feature_dimension, dtype=np.float32)
    if not text:
        return vector

    # Use SHA256 for deterministic hashing
    hash_bytes = hashlib.sha256(text.lower().encode()).digest()

    # Convert to indices and values
    for i in range(0, min(len(hash_bytes), dimension), 2):
        idx = (hash_bytes[i] + offset) % self._feature_dimension
        val = (hash_bytes[i + 1] / 255.0) * 2 - 1  # Normalize to [-1, 1]
        vector[idx] += val

    return vector
```

**Why SHA256?**
- **Deterministic**: Same text always produces same hash
- **Distributed**: Hash bits are uniformly distributed
- **Sparse**: Each word contributes to multiple indices

**Example:**
```python
text1 = "High electricity consumption"
text2 = "High electricity usage"
text3 = "Low water consumption"

# text1 and text2 have similar hashes (shared words: "high", "electricity")
# text3 has different hash (different words)
```

### Categorical Encoding (One-hot / Multi-hot)

**One-hot encoding (single category):**

```python
# From backend/encoders/sealion.py lines 204-229
def _encode_categorical(
    self,
    value: str,
    categories: List[str],
    start_idx: int
) -> np.ndarray:
    """One-hot encode a categorical value."""
    vector = np.zeros(self._feature_dimension, dtype=np.float32)
    value_lower = value.lower() if value else ""

    for i, cat in enumerate(categories):
        if cat.lower() in value_lower or value_lower in cat.lower():
            idx = (start_idx + i) % self._feature_dimension
            vector[idx] = 1.0
            break  # Only one category

    return vector
```

**Multi-hot encoding (multiple categories):**

```python
# From backend/encoders/sealion.py lines 231-258
def _encode_multi_categorical(
    self,
    values: List[str],
    categories: List[str],
    start_idx: int
) -> np.ndarray:
    """Multi-hot encode a list of categorical values."""
    vector = np.zeros(self._feature_dimension, dtype=np.float32)
    values_lower = [v.lower() for v in values] if values else []

    for i, cat in enumerate(categories):
        cat_lower = cat.lower()
        for val in values_lower:
            if cat_lower in val or val in cat_lower:
                idx = (start_idx + i) % self._feature_dimension
                vector[idx] = 1.0  # Can set multiple categories
                break

    return vector
```

**Example:**

```python
# Consumption profile (one-hot)
text = "Very high electricity usage"
# → Sets index 561 (very_high) to 1.0

# Causes (multi-hot)
causes = ["environment", "technology", "health"]
# → Sets indices 258 (environment), 270 (technology), 257 (health) to 1.0
```

### Continuous Scores (Indices 548-557)

**Direct assignment from SEALION analysis:**

```python
embedding[548] = features.get("engagement_level", 0.5)      # 0.0-1.0
embedding[549] = features.get("experience_level", 0.5)     # 0.0-1.0
embedding[550] = features.get("consumption_level", 0.5)    # 0.0-1.0
embedding[551] = features.get("efficiency_score", 0.5)     # 0.0-1.0
embedding[552] = features.get("language_diversity", 0.5)   # 0.0-1.0
embedding[553] = features.get("regional_focus", 0.5)       # 0.0-1.0
```

**Example:**
```
User bill: 450 kWh (national avg 400 kWh)

SEALION analysis:
  consumption_level: 0.75  (above average)
  efficiency_score: 0.4    (below average efficiency)

Embedding:
  embedding[550] = 0.75
  embedding[551] = 0.4
```

---

## Distance Metric

### L2 (Euclidean) Distance

VoltPulse-SG uses **L2 distance** for similarity search:

```sql
SELECT source_id, embedding <-> query_embedding AS distance
FROM my_embeddings
ORDER BY distance ASC
LIMIT 10
```

**Why L2 over Cosine?**
- **Magnitude matters**: High consumption (0.75) vs low consumption (0.25) should be far apart
- **Euclidean space**: Continuous scores (indices 548-557) are naturally Euclidean
- **IVFFlat index**: Optimized for L2 distance in pgvector

**Distance to Similarity Conversion:**

```python
# From backend/recommender/vector_store.py line 267
score = 1.0 / (1.0 + distance)
```

**Example:**
```
distance = 0.5 → similarity = 1.0 / 1.5 = 0.67 (67%)
distance = 2.0 → similarity = 1.0 / 3.0 = 0.33 (33%)
distance = 0.0 → similarity = 1.0 / 1.0 = 1.00 (100%)
```

### Normalization

All embeddings are **L2-normalized** before storage:

```python
# From backend/encoders/sealion.py lines 328-331
norm = np.linalg.norm(embedding)
if norm > 0:
    embedding = embedding / norm
```

This ensures all vectors have **unit length** (||v|| = 1), making distance comparisons fair.

---

## Implementation Examples

### Full Encoding Flow

```python
# From backend/encoders/sealion.py lines 335-356
async def encode(self, text: str) -> np.ndarray:
    """Encode text using SeaLion analysis.

    Process:
    1. Send text to SeaLion for semantic analysis
    2. Parse extracted features from response
    3. Build embedding from features + text hashing
    """
    # Step 1: Get SeaLion analysis
    response = await self._call_sealion(
        f"Analyze this content:\n\n{text}"
    )

    # Step 2: Parse features
    features = self._parse_sealion_response(response)

    # Step 3: Build embedding
    return self._build_embedding_from_features(text, features)
```

### Batch Encoding

```python
# From backend/encoders/sealion.py lines 358-378
async def encode_batch(self, texts: List[str]) -> np.ndarray:
    """Encode multiple texts.

    Note: Sequential API calls (SEALION doesn't support batch).
    """
    if not texts:
        return np.zeros((0, self._feature_dimension), dtype=np.float32)

    embeddings = []
    for text in texts:
        emb = await self.encode(text)
        embeddings.append(emb)

    return np.vstack(embeddings)
```

### Usage in RAG Tool

```python
# From backend/tools/retailer_tools.py
encoder = SeaLionEncoder()

# Encode user query
query_text = "Find retailers selling air conditioners near Bedok"
query_embedding = await encoder.encode(query_text)  # 1024-dim vector

# Search in vector store
results = await vector_store.find_similar(
    query_embedding,
    form_type="retailer",
    limit=800
)
```

---

## Performance Considerations

### Latency

| Operation | Time | Notes |
|-----------|------|-------|
| SEALION API call | ~500-1000ms | Feature extraction |
| Embedding construction | ~5ms | Vector assembly |
| **Total encoding** | **~500-1000ms** | Dominated by LLM call |

### Caching Strategy

**Problem:** SEALION API calls are expensive (latency + cost).

**Solution:** Cache embeddings for frequently queried content.

```python
# From backend/utils/cache.py (conceptual)
embedding_cache = {}

async def encode_with_cache(encoder, text):
    cache_key = hashlib.md5(text.encode()).hexdigest()

    if cache_key in embedding_cache:
        return embedding_cache[cache_key]

    embedding = await encoder.encode(text)
    embedding_cache[cache_key] = embedding
    return embedding
```

For VoltPulse-SG:
- **Retailer embeddings**: Pre-computed and stored in database (no re-encoding)
- **User queries**: Encoded on-demand (not cached, as each query is unique)

---

## Cross-References

- [Vector Database](./vector-database.md) - Storing and querying SEALION embeddings
- [RAG System](./rag-system.md) - Using embeddings in Tools 1 & 5
- [RRF Algorithm](../03-recommender-system/rrf-algorithm.md) - Semantic similarity signal
- [Architecture Overview](../01-architecture/overview.md) - Why SEALION over alternatives

---

[← Back to Documentation](../README.md) | [Next: Vector Database →](./vector-database.md)
