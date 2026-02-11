# Encoder Customization Guide

Guide for customizing the SEALION embedding encoder.

---

## Overview

The SEALION encoder creates **1024-dimensional embeddings** with segmented feature spaces:

- **Indices 0-255**: Text Hash (SHA256-based)
- **Indices 256-511**: Cause Categories (15 causes)
- **Indices 512-527**: Cause Scores (continuous 0-1)
- **Indices 528-537**: Country Codes (10 ASEAN countries)
- **Indices 538-547**: Languages (10 languages)
- **Indices 548-557**: Continuous Scores (engagement, efficiency, etc.)
- **Indices 558-600**: Profile Types (consumption levels, availability)
- **Indices 600-1023**: Motivation Themes (hashed text)

---

## Customization Options

### 1. Add New Features

Edit `backend/encoders/sealion.py`:

```python
def _construct_embedding(self, features: dict) -> List[float]:
    """Construct 1024-dimensional embedding."""
    embedding = [0.0] * 1024

    # Existing features...

    # Add custom feature: Time-of-day preference
    time_preference = features.get("time_preference", "any")
    time_map = {"morning": 0.0, "afternoon": 0.33, "evening": 0.67, "night": 1.0, "any": 0.5}
    embedding[558] = time_map.get(time_preference, 0.5)

    # Add custom feature: Price sensitivity (0-1)
    price_sensitivity = features.get("price_sensitivity", 0.5)
    embedding[559] = max(0.0, min(1.0, price_sensitivity))

    return embedding
```

### 2. Adjust Feature Extraction

Modify the LLM analysis prompt:

```python
system_prompt = f"""You are analyzing text for semantic embedding generation...

Extract these features:
1. Cause Categories (1-15):...
2. Time Preference (morning/afternoon/evening/night/any)
3. Price Sensitivity (0.0-1.0 scale)

Return JSON:
{{
  "causes": [...],
  "time_preference": "evening",
  "price_sensitivity": 0.7
}}
"""
```

### 3. Change Distance Metric

The default is L2 (Euclidean) distance. To use cosine similarity:

```python
# In vector_store.py
query = """
    SELECT id, form_type, form_data,
           1 - (embedding <=> %s::vector) as similarity
    FROM my_embeddings
    WHERE form_type = %s
    ORDER BY embedding <=> %s::vector
    LIMIT %s
"""
```

---

## Re-encoding Existing Data

After modifying the encoder, re-encode all stored embeddings:

```python
# scripts/re_encode_embeddings.py

import asyncio
from encoders.sealion import SeaLionEncoder
from recommender.vector_store import VectorStore
from graph.builder import create_async_pool

async def re_encode_all():
    """Re-encode all embeddings with updated encoder."""
    pool = create_async_pool()
    await pool.open()

    encoder = SeaLionEncoder()
    vector_store = VectorStore(pool)

    # Get all documents
    results = await vector_store.find_by_form_type("retailer", limit=1000)

    for result in results:
        form_data = result.form_data or {}
        combined_text = form_data.get("combined_text", "")

        if not combined_text:
            continue

        # Re-encode
        new_embedding = await encoder.encode(combined_text)

        # Update in database
        await vector_store.update_embedding(result.id, new_embedding)

        print(f"Re-encoded: {result.id}")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(re_encode_all())
```

Run:
```bash
python scripts/re_encode_embeddings.py
```

---

## Performance Considerations

- **Encoding Time**: ~500ms per document with SEALION API
- **Batch Encoding**: Process 10 documents in parallel to speed up
- **Caching**: Cache encodings for identical text
- **Index Rebuilding**: Rebuild IVFFlat index after bulk re-encoding

---

## Related Documentation

- [SEALION Integration](../02-core-systems/sealion-integration.md)
- [Vector Database](../02-core-systems/vector-database.md)

---

**Generated:** 2024-06-15
