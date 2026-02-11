# Environment Variables Reference

Complete `.env` configuration reference for VoltPulse-SG.

---

## Overview

VoltPulse uses environment variables for configuration. Create a `.env` file in the `backend/` directory.

**Template:** [backend/.env.example](../../backend/.env.example)

---

## Required Variables

### Database (Supabase PostgreSQL)

```env
# Supabase Database Connection
SUPABASE_DB_HOST=db.yourproject.supabase.co
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.yourproject
SUPABASE_DB_PASSWORD=your_secure_password_here
SUPABASE_DB_SSLMODE=require
```

**Required:** Yes
**Description:** PostgreSQL connection parameters for Supabase
**SSL Mode Options:** `require`, `verify-full`, `verify-ca`, `disable`
**Note:** Port 6543 is Supabase's pgBouncer pooling port (recommended)

---

### Ollama LLM

```env
# Ollama Cloud Configuration
OLLAMA_API_KEY=your_ollama_api_key_here
OLLAMA_BASE_URL=https://ollama.com
```

**Required:** Yes
**Description:** Ollama GPT-OSS 120B cloud access
**Fallback:** If not set, uses local Ollama at `http://localhost:11434`
**Model:** gpt-oss:120b

---

### SEALION Encoder

```env
# SEALION Embedding API
SEALION_ENDPOINT=https://your-sealion-endpoint.com/api/encode
```

**Required:** Yes
**Description:** SEALION 1024-dimensional embedding API
**Format:** Full URL including `/api/encode` endpoint
**Purpose:** Semantic search and retailer matching

---

### OpenAI (Vision OCR)

```env
# OpenAI API for Vision OCR
OPENAI_API_KEY=sk-proj-...your_openai_api_key_here
```

**Required:** Yes
**Description:** OpenAI API for GPT-4o Vision bill extraction
**Purpose:** OCR processing, chart reading, web search
**Models Used:** gpt-4o, gpt-5 (with web_search tool)

---

## Optional Variables

### RRF Configuration

```env
# RRF Scorer Configuration
RRF_K=60
RRF_SEMANTIC_WEIGHT=0.40
RRF_PRODUCT_WEIGHT=0.25
RRF_LOCATION_WEIGHT=0.20
RRF_BREADTH_WEIGHT=0.10
RRF_INTENT_WEIGHT=0.05
RRF_QUICK_MODE_THRESHOLD=30
```

**Description:**
- `RRF_K`: Scale constant for RRF formula (default: 60)
- `RRF_*_WEIGHT`: Signal weights (must sum to ~1.0)
- `RRF_QUICK_MODE_THRESHOLD`: Auto-enable quick mode when candidates > threshold

**Defaults:** See [backend/recommender/rrf_scorer.py](../../backend/recommender/rrf_scorer.py#L40-L57)

---

### Web Search (Tavily)

```env
# Tavily Web Search API (fallback)
TAVILY_API_KEY=tvly-...your_tavily_api_key_here
```

**Required:** No (uses OpenAI web_search by default)
**Description:** Alternative web search provider
**Purpose:** Appliance recommendations, product reviews

---

### ROI Calculator

```env
# ROI Calculator Configuration
CLIMATE_VOUCHER_AMOUNT=300.0
ELECTRICITY_RATE_SGD=0.30
```

**Defaults:**
- Climate Voucher: $300 SGD
- Electricity Rate: $0.30 per kWh

**Description:** Override default Climate Voucher amount and electricity rate

---

### Analytics

```env
# Analytics Configuration
ANOMALY_CONFIDENCE_LEVEL=0.95
STATISTICAL_MIN_SAMPLE_SIZE=30
```

**Defaults:**
- Confidence Level: 95% (Z-score threshold: 1.96)
- Min Sample Size: 30 households for statistical significance

---

## Production Configuration

### Security

```env
# Production Security
SECRET_KEY=your_secret_key_for_jwt_tokens
ALLOWED_ORIGINS=https://voltpulse.sg,https://www.voltpulse.sg
API_RATE_LIMIT=100
```

**Description:**
- `SECRET_KEY`: For JWT token signing (if implementing auth)
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)
- `API_RATE_LIMIT`: Requests per minute per IP

---

### Logging

```env
# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/voltpulse/app.log
SENTRY_DSN=https://...@sentry.io/...
```

**Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
**Sentry:** Optional error tracking

---

## Complete .env Template

```env
# =============================================================================
# VoltPulse-SG Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Database (Required)
# -----------------------------------------------------------------------------
SUPABASE_DB_HOST=db.yourproject.supabase.co
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.yourproject
SUPABASE_DB_PASSWORD=your_secure_password_here
SUPABASE_DB_SSLMODE=require

# -----------------------------------------------------------------------------
# LLM & AI Services (Required)
# -----------------------------------------------------------------------------
# Ollama GPT-OSS 120B
OLLAMA_API_KEY=your_ollama_api_key_here
OLLAMA_BASE_URL=https://ollama.com

# SEALION Embeddings
SEALION_ENDPOINT=https://your-sealion-endpoint.com/api/encode

# OpenAI (Vision OCR + Web Search)
OPENAI_API_KEY=sk-proj-...your_openai_api_key_here

# -----------------------------------------------------------------------------
# Optional: RRF Configuration
# -----------------------------------------------------------------------------
RRF_K=60
RRF_SEMANTIC_WEIGHT=0.40
RRF_PRODUCT_WEIGHT=0.25
RRF_LOCATION_WEIGHT=0.20
RRF_BREADTH_WEIGHT=0.10
RRF_INTENT_WEIGHT=0.05
RRF_QUICK_MODE_THRESHOLD=30

# -----------------------------------------------------------------------------
# Optional: ROI & Climate Voucher
# -----------------------------------------------------------------------------
CLIMATE_VOUCHER_AMOUNT=300.0
ELECTRICITY_RATE_SGD=0.30

# -----------------------------------------------------------------------------
# Optional: Analytics
# -----------------------------------------------------------------------------
ANOMALY_CONFIDENCE_LEVEL=0.95
STATISTICAL_MIN_SAMPLE_SIZE=30

# -----------------------------------------------------------------------------
# Optional: Production Settings
# -----------------------------------------------------------------------------
# SECRET_KEY=your_secret_key_here
# ALLOWED_ORIGINS=https://voltpulse.sg
# API_RATE_LIMIT=100
# LOG_LEVEL=INFO
# SENTRY_DSN=https://...@sentry.io/...
```

---

## Verification

Check environment variables are loaded:

```python
# backend/verify_env.py

import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_PASSWORD",
    "OLLAMA_API_KEY",
    "SEALION_ENDPOINT",
    "OPENAI_API_KEY",
]

print("Environment Variable Check:\n")
for var in required_vars:
    value = os.getenv(var)
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"✓ {var}: {masked}")
    else:
        print(f"✗ {var}: NOT SET")
```

Run:
```bash
python backend/verify_env.py
```

---

## Related Documentation

- [Deployment Guide](../01-architecture/deployment.md) - Production setup
- [Database Schema](./database-schema.md) - Database tables
- [Troubleshooting](./troubleshooting.md) - Common env issues

---

**Generated:** 2024-06-15
**Location:** `backend/.env`
