# VoltPulse-SG Technical Documentation

Welcome to the comprehensive technical documentation for **VoltPulse-SG**, an AI-powered utility bill analysis platform for Singapore households.

## Overview

VoltPulse-SG helps Singapore households:
- Understand their energy consumption patterns through AI-powered analysis
- Compare consumption against national benchmarks
- Find energy-efficient appliances and retailers
- Maximize government Climate Voucher benefits ($300 per household)

**Key Technologies:** FastAPI · Next.js · LangGraph · SEALION Embeddings · Supabase · PostgreSQL with pgvector

---

## Documentation Structure

### 1. Architecture

Understand the system design and technology choices.

- [**System Overview**](./01-architecture/overview.md) - High-level architecture, component interactions, and design decisions
- [**Tech Stack**](./01-architecture/tech-stack.md) - Complete technology inventory with rationale
- [**Data Flow**](./01-architecture/data-flow.md) - End-to-end data flow diagrams and pipelines
- [**Deployment**](./01-architecture/deployment.md) - Infrastructure and deployment architecture

### 2. Core Systems

Deep-dive into the foundational AI and data systems.

- [**RAG System**](./02-core-systems/rag-system.md) - Agentic RAG with ReAct loop and 5 specialized tools
- [**SEALION Integration**](./02-core-systems/sealion-integration.md) - 1024-dimensional embeddings for semantic search
- [**Vector Database**](./02-core-systems/vector-database.md) - Supabase pgvector implementation and similarity search
- [**LangGraph Orchestration**](./02-core-systems/langgraph-orchestration.md) - Graph state machine and conversation management
- [**Cost Optimization**](./02-core-systems/cost-optimization.md) - 7 strategies reducing costs from $0.08 to $0.02 per query

### 3. Recommender System

Learn about the multi-signal retailer ranking algorithm.

- [**RRF Algorithm**](./03-recommender-system/rrf-algorithm.md) - Reciprocal Rank Fusion mathematical formulation
- [**Multi-Signal Ranking**](./03-recommender-system/multi-signal-ranking.md) - Deep-dive into all 5 ranking signals
- [**Retailer Matching**](./03-recommender-system/retailer-matching.md) - 700+ retailers matching logic
- [**Performance Tuning**](./03-recommender-system/performance-tuning.md) - Quick mode and scalability optimizations

### 4. Services

Documentation for business logic and analysis services.

- [**OCR Extraction**](./04-services/ocr-extraction.md) - OpenAI Vision API for bill parsing
- [**Bill Diagnosis**](./04-services/bill-diagnosis.md) - Anomaly detection and health scoring
- [**ROI Calculator**](./04-services/roi-calculator.md) - Appliance upgrade ROI calculations
- [**Heatmap Analytics**](./04-services/heatmap-analytics.md) - District-level consumption visualization
- [**Statistical Analysis**](./04-services/statistical-analysis.md) - SciPy-based statistical methods

### 5. API Reference

Complete REST API and data model documentation.

- [**Endpoints**](./05-api-reference/endpoints.md) - FastAPI endpoint specifications
- [**Graph API**](./05-api-reference/graph-api.md) - LangGraph invocation patterns
- [**Tools**](./05-api-reference/tools.md) - Agent tool specifications
- [**Schemas**](./05-api-reference/schemas.md) - Pydantic model reference

### 6. Implementation Guides

Step-by-step guides for extending the system.

- [**Adding New Tools**](./06-implementation-guides/adding-new-tools.md) - Extend the agentic RAG agent
- [**Custom Signals**](./06-implementation-guides/custom-signals.md) - Add new signals to RRF scorer
- [**Encoder Customization**](./06-implementation-guides/encoder-customization.md) - Modify SEALION embeddings
- [**Analytics Extension**](./06-implementation-guides/analytics-extension.md) - Add new analytics features

### 7. Appendices

Reference materials and troubleshooting.

- [**Environment Variables**](./07-appendices/environment-variables.md) - Complete .env configuration reference
- [**Database Schema**](./07-appendices/database-schema.md) - PostgreSQL table schemas
- [**Troubleshooting**](./07-appendices/troubleshooting.md) - Common issues and solutions
- [**Performance Benchmarks**](./07-appendices/performance-benchmarks.md) - System performance metrics

---

## Quick Links

### For Developers
- [Setting up the development environment](./07-appendices/environment-variables.md)
- [Understanding the RAG system](./02-core-systems/rag-system.md)
- [Adding new agent tools](./06-implementation-guides/adding-new-tools.md)
- [API endpoint reference](./05-api-reference/endpoints.md)

### For Data Scientists
- [SEALION 1024-dimensional embeddings](./02-core-systems/sealion-integration.md)
- [RRF multi-signal ranking algorithm](./03-recommender-system/rrf-algorithm.md)
- [Bill diagnosis and anomaly detection](./04-services/bill-diagnosis.md)
- [Statistical analysis methods](./04-services/statistical-analysis.md)

### For System Architects
- [System architecture overview](./01-architecture/overview.md)
- [Tech stack and design decisions](./01-architecture/tech-stack.md)
- [Cost optimization strategies](./02-core-systems/cost-optimization.md)
- [Deployment architecture](./01-architecture/deployment.md)

---

## Key Features Documented

### RAG System
- **Agentic RAG** with autonomous tool selection via ReAct loop
- **5 specialized tools**: consumption info, energy ratings, ROI calculator, web search, retailer finder
- **Memory management** with AsyncPostgresStore for cross-conversation context
- **Grounding rules** to prevent hallucinations

### SEALION Embeddings
- **1024-dimensional vector space** with segmented features
- **Hybrid encoding**: text hash + categorical features + continuous scores
- **ASEAN-focused** multilingual capabilities
- **L2 distance** similarity search with IVFFlat index

### Cost Optimization
- **5-category classifier** reducing tool calls by 52%
- **RRF quick mode** reducing ranking time by 60%
- **Search caching** with 90% hit rate
- **Pre-computed data** eliminating unnecessary API calls
- **Result:** 75% cost reduction ($0.08 → $0.02 per query)

### Recommender System
- **Reciprocal Rank Fusion** combining 5 ranking signals:
  - Semantic Similarity (40%) - L2 distance from vector search
  - Product Match (25%) - Jaccard similarity
  - Location Relevance (20%) - Planning area proximity
  - Retailer Breadth (10%) - Product diversity + website
  - Query Intent (5%) - Keyword-based detection
- **700+ Climate Voucher retailers** with multi-signal ranking
- **Quick mode optimization** for large result sets

---

## Documentation Philosophy

This documentation is designed to be:

1. **Implementation-Focused** - Code snippets with line numbers from actual implementation
2. **Architecturally Grounded** - Explains the "why" behind each decision
3. **Mathematically Rigorous** - Formulas, algorithms, and worked examples
4. **Practically Useful** - Testing instructions, troubleshooting, and common pitfalls

Every document includes:
- Problem statement (what does this solve?)
- Design rationale (why this approach?)
- Code walkthrough (how is it implemented?)
- Configuration (how to tune it?)
- Testing (how to verify it works?)

---

## Contributing to Documentation

When updating documentation:
1. Maintain technical depth with code examples
2. Update cross-references when restructuring
3. Validate all code snippets against implementation
4. Include performance metrics where applicable
5. Test all example curl commands

---

## Project Links

- **Main Repository:** [VoltPulse-SG GitHub](../../README.md)
- **Backend API:** [backend/](../../backend/)
- **Frontend:** [frontend/](../../frontend/)
- **Plan File:** [Documentation Plan](./.claude/plans/rosy-munching-moth.md)

---

**Last Updated:** February 2026
**Documentation Version:** 1.0.0
**Project Version:** See main README.md
