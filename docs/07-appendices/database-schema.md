# Database Schema Reference

Complete database schema for VoltPulse-SG PostgreSQL database.

---

## Overview

VoltPulse uses **PostgreSQL 15** with **pgvector** extension hosted on Supabase.

**Extensions:**
- `pgvector` - Vector similarity search
- `pg_trgm` - Trigram text search (optional)

---

## Core Tables

### my_embeddings

Main vector store for all documents (bills, retailers, consumption data).

```sql
CREATE TABLE my_embeddings (
    id TEXT PRIMARY KEY,
    form_type TEXT NOT NULL,
    form_data JSONB,
    metadata JSONB,
    embedding VECTOR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_form_type ON my_embeddings(form_type);
CREATE INDEX idx_metadata_gin ON my_embeddings USING gin(metadata);
CREATE INDEX idx_form_data_gin ON my_embeddings USING gin(form_data);

-- IVFFlat index for vector similarity (L2 distance)
CREATE INDEX my_embeddings_embedding_idx
    ON my_embeddings
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);
```

**Columns:**
- `id` (TEXT): Unique source ID (e.g., `vision_a3f9e2b1`, `retailer_abc123`)
- `form_type` (TEXT): Document type (`ocr`, `vision`, `retailer`, `utility_bill`, `consumption`)
- `form_data` (JSONB): Document-specific data (extraction results, retailer info, etc.)
- `metadata` (JSONB): Additional metadata (timestamps, confidence scores, etc.)
- `embedding` (VECTOR(1024)): SEALION 1024-dimensional embedding
- `created_at` (TIMESTAMP): Creation timestamp
- `updated_at` (TIMESTAMP): Last update timestamp

**Form Types:**
- `ocr` - Legacy OCR documents
- `vision` - OpenAI Vision extracted bills
- `retailer` - Climate Voucher retailers
- `utility_bill` - Processed utility bills
- `consumption` - Consumption patterns

**Example Row:**
```sql
INSERT INTO my_embeddings (id, form_type, form_data, embedding) VALUES (
    'vision_a3f9e2b1c4d5',
    'utility_bill',
    '{
        "source_type": "vision",
        "original_filename": "bill_jan_2024.jpg",
        "extraction_data": {
            "customer_name": "JOHN TAN",
            "consumption_kwh": 350.5,
            "total_amount": 105.20
        },
        "diagnosis": {...}
    }'::jsonb,
    '[0.123, 0.456, ...]'::vector(1024)
);
```

---

## LangGraph Tables

### checkpoints

Stores conversation state snapshots.

```sql
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX checkpoints_parent_id
    ON checkpoints(thread_id, checkpoint_ns, parent_checkpoint_id);
```

**Purpose:** Enables conversation history and resume capability

---

### checkpoint_writes

Incremental state updates between checkpoints.

```sql
CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

---

### store

Agent long-term memory storage.

```sql
CREATE TABLE store (
    prefix TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (prefix, key)
);

CREATE INDEX store_prefix_idx ON store(prefix);
CREATE INDEX store_updated_at_idx ON store(updated_at);

-- Full-text search on value
CREATE INDEX store_value_gin ON store USING gin(to_tsvector('english', value::text));
```

**Purpose:** Semantic memory for personalization
**Namespace Format:** `("user_memories", user_id)`

---

## Analytics Tables (Optional)

### interventions

Energy efficiency intervention tracking.

```sql
CREATE TABLE interventions (
    id TEXT PRIMARY KEY,
    account_number TEXT NOT NULL,
    intervention_type TEXT NOT NULL,
    intervention_date DATE NOT NULL,
    postal_code TEXT,
    housing_type TEXT,
    description TEXT,
    cost_sgd FLOAT,
    pre_intervention_kwh_avg FLOAT,
    post_intervention_kwh_avg FLOAT,
    consumption_delta_kwh FLOAT,
    consumption_delta_percent FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX interventions_account_idx ON interventions(account_number);
CREATE INDEX interventions_date_idx ON interventions(intervention_date);
CREATE INDEX interventions_type_idx ON interventions(intervention_type);
```

**Intervention Types:**
- `cool_paint` - Cool roof/wall paint
- `led_retrofit` - LED lighting upgrade
- `solar_panel` - Solar PV installation
- `aircon_upgrade` - Air conditioning upgrade
- `insulation` - Thermal insulation
- `smart_meter` - Smart meter installation

---

## Queries

### Vector Similarity Search

```sql
-- Find similar documents (L2 distance)
SELECT
    id,
    form_type,
    form_data,
    1.0 / (1.0 + (embedding <-> $1::vector)) AS similarity,
    embedding <-> $1::vector AS distance
FROM my_embeddings
WHERE form_type = $2
ORDER BY embedding <-> $1::vector
LIMIT $3;
```

**Parameters:**
- `$1`: Query embedding (vector(1024))
- `$2`: Form type filter
- `$3`: Result limit

---

### Filtered Search

```sql
-- Search with metadata filter
SELECT *
FROM my_embeddings
WHERE form_type = 'retailer'
    AND form_data->>'planning_area' = 'Bedok'
    AND form_data->'eligible_products' @> '["air_conditioners"]'::jsonb
ORDER BY embedding <-> $1::vector
LIMIT 20;
```

---

### Conversation History

```sql
-- Get conversation checkpoints
SELECT checkpoint, metadata
FROM checkpoints
WHERE thread_id = $1
ORDER BY checkpoint_id DESC
LIMIT 10;
```

---

## Maintenance

### Vacuum & Analyze

```sql
-- Regular maintenance for vector index
VACUUM ANALYZE my_embeddings;
```

### Rebuild Vector Index

```sql
-- Rebuild IVFFlat index after bulk inserts
DROP INDEX IF EXISTS my_embeddings_embedding_idx;
CREATE INDEX my_embeddings_embedding_idx
    ON my_embeddings
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);
```

**When to Rebuild:**
- After inserting 100+ new documents
- After re-encoding embeddings
- When query performance degrades

---

### Size Monitoring

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Backup & Restore

### Backup

```bash
# Full database backup
pg_dump -h db.supabase.co -U postgres.project -d postgres > voltpulse_backup.sql

# Table-specific backup
pg_dump -h db.supabase.co -U postgres.project -t my_embeddings > embeddings_backup.sql
```

### Restore

```bash
# Restore database
psql -h db.supabase.co -U postgres.project -d postgres < voltpulse_backup.sql

# Restore specific table
psql -h db.supabase.co -U postgres.project -d postgres < embeddings_backup.sql
```

---

## Related Documentation

- [Vector Database](../02-core-systems/vector-database.md) - pgvector operations
- [LangGraph Orchestration](../02-core-systems/langgraph-orchestration.md) - Checkpoint usage
- [Environment Variables](./environment-variables.md) - Database connection config

---

**Generated:** 2024-06-15
**PostgreSQL Version:** 15
**pgvector Version:** 0.5.x
