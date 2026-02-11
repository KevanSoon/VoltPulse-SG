# API Endpoints Reference

Complete reference for all VoltPulse-SG REST API endpoints.

---

## Table of Contents

1. [Base Configuration](#base-configuration)
2. [Health & Status](#health--status)
3. [Chat & Conversation](#chat--conversation)
4. [Agentic RAG](#agentic-rag)
5. [Singpass Mock Data](#singpass-mock-data)
6. [OCR Processing](#ocr-processing)
7. [Consumption Extraction](#consumption-extraction)
8. [Retailer Search](#retailer-search)
9. [ROI Calculator](#roi-calculator)
10. [Analytics Dashboard](#analytics-dashboard)

---

## Base Configuration

**Base URL:** `http://localhost:7860` (development) or `https://api.voltpulse.sg` (production)

**Authentication:** Currently none required (add Bearer tokens for production)

**Content-Type:** `application/json` for all POST/PUT requests

**CORS:** Configured to allow all origins (development only)

---

## Health & Status

### GET `/`

Root endpoint with service health status.

**Response:**
```json
{
  "status": "healthy",
  "message": "VoltPulse API is running",
  "services": {
    "langgraph_chat": true,
    "encoder": true,
    "database": true
  }
}
```

**Example:**
```bash
curl http://localhost:7860/
```

---

### GET `/health`

Simple health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Chat & Conversation

### POST `/chat`

Chat with LangGraph-powered AI assistant with persistent memory.

**Request Body:**
```json
{
  "message": "Can you recommend energy-efficient refrigerators?",
  "user_id": "user_123",
  "thread_id": "conv_456",
  "stream": false
}
```

**Parameters:**
- `message` (string, required): User's message
- `user_id` (string, optional): User identifier for memory (default: "default_user")
- `thread_id` (string, optional): Conversation thread ID (default: "default_thread")
- `stream` (boolean, optional): Enable streaming response (default: false)

**Response (Non-streaming):**
```json
{
  "response": "I can help you find energy-efficient refrigerators. Let me search for Climate Voucher eligible options..."
}
```

**Response (Streaming):**
Server-Sent Events with text/event-stream content type.

**Example:**
```bash
curl -X POST http://localhost:7860/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are my electricity consumption patterns?",
    "user_id": "john_doe",
    "thread_id": "session_001"
  }'
```

**Implementation:** [backend/app.py:231-279](../../backend/app.py#L231-L279)

---

## Agentic RAG

### POST `/rag/search`

Agentic RAG search with autonomous tool use and reasoning.

**Request Body:**
```json
{
  "query": "Find me retailers near Bedok selling 4-tick aircons",
  "max_iterations": 10
}
```

**Parameters:**
- `query` (string, required): Natural language search query
- `max_iterations` (integer, optional): Max tool call iterations (default: 10, range: 1-20)

**Response:**
```json
{
  "response": "I found 5 retailers near Bedok selling 4-tick air conditioners:\n\n1. **Gain City**...",
  "tool_calls": [
    {
      "tool": "find_retailers_by_product",
      "args": {"product": "air conditioners", "limit": 800},
      "result": "..."
    }
  ],
  "message_count": 4
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the best LED lights for HDB flats?",
    "max_iterations": 15
  }'
```

**Implementation:** [backend/app.py:337-372](../../backend/app.py#L337-L372)

---

### GET `/rag/tools`

List available agent tools.

**Response:**
```json
{
  "tools": [
    {
      "name": "get_user_consumption_info",
      "description": "Get user's consumption data from their uploaded utility bills"
    },
    {
      "name": "find_retailers_by_product",
      "description": "Find Climate Voucher retailers selling specific products"
    }
  ],
  "total": 5
}
```

**Implementation:** [backend/app.py:375-392](../../backend/app.py#L375-L392)

---

## Singpass Mock Data

### GET `/singpass/mock/{profile_id}`

Get mock Singpass data for autofill demonstration.

**Path Parameters:**
- `profile_id` (string): Profile ID (org_001, org_002, org_003)

**Response:**
```json
{
  "name": "Sarah Tan Wei Ling",
  "nric_masked": "S****567A",
  "email": "sarah.tan@example.org",
  "mobile": "+65 9123 4567",
  "registered_address": "123 Orchard Road, #12-01, Singapore 238867",
  "planning_area": "orchard",
  "organization_name": "Hearts of Hope Foundation",
  "organization_uen": "201912345K",
  "organization_type": "charity"
}
```

**Example:**
```bash
curl http://localhost:7860/singpass/mock/org_001
```

---

### GET `/singpass/mock`

List all available mock Singpass profiles.

**Response:**
```json
{
  "org_001": {...},
  "org_002": {...},
  "org_003": {...}
}
```

---

## OCR Processing

### POST `/ocr/process`

Upload and process utility bill image using OpenAI Vision API.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Binary file upload

**Parameters:**
- `file` (file, required): Image file (PNG, JPEG, JPG, GIF, BMP, WEBP)

**Response:**
```json
{
  "extracted_texts": [
    "Customer: JOHN TAN",
    "Address: BLK 123 BEDOK NORTH ST 2 #05-123 Singapore 460123",
    "Provider: SP Services",
    "Electricity: 350.5 kWh",
    "Total: S$105.20",
    "Electricity trend: Jan:320, Feb:340, Mar:350"
  ],
  "embedding_stored": true,
  "source_id": "vision_a3f9e2b1c4d5",
  "extraction_confidence": 0.92,
  "extraction_data": {
    "customer_name": "JOHN TAN",
    "account_number": "8012345678",
    "premise_address": "BLK 123 BEDOK NORTH ST 2 #05-123 Singapore 460123",
    "consumption_kwh": 350.5,
    "total_amount": 105.20,
    "billing_period_start": "2024-01-01",
    "billing_period_end": "2024-01-31",
    "provider_name": "SP Services",
    "consumption_trends": [
      {
        "service_type": "Electricity",
        "monthly_data": [
          {"month": "Jan", "value": 320},
          {"month": "Feb", "value": 340},
          {"month": "Mar", "value": 350}
        ]
      }
    ]
  },
  "diagnosis": {
    "overall_health_score": 75,
    "health_grade": "C",
    "anomalies": [...],
    "efficiency_issues": [...],
    "recommendations": [...]
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/ocr/process \
  -F "file=@/path/to/utility_bill.jpg"
```

**Implementation:** [backend/app.py:461-592](../../backend/app.py#L461-L592)

---

### GET `/ocr/results/{source_id}`

Retrieve a stored OCR result by source ID.

**Path Parameters:**
- `source_id` (string): OCR document source ID (e.g., "vision_a3f9e2b1c4d5")

**Response:**
```json
{
  "id": "vision_a3f9e2b1c4d5",
  "form_type": "utility_bill",
  "form_data": {
    "source_type": "vision",
    "original_filename": "bill_jan_2024.jpg",
    "extracted_texts": [...],
    "extraction_data": {...},
    "diagnosis": {...}
  }
}
```

**Example:**
```bash
curl http://localhost:7860/ocr/results/vision_a3f9e2b1c4d5
```

**Implementation:** [backend/app.py:595-611](../../backend/app.py#L595-L611)

---

## Consumption Extraction

### POST `/consumption/extract`

Extract structured consumption data from a stored OCR document.

**Request Body:**
```json
{
  "source_id": "vision_a3f9e2b1c4d5"
}
```

**Response:**
```json
{
  "source_id": "vision_a3f9e2b1c4d5",
  "original_filename": "bill_jan_2024.jpg",
  "extraction_successful": true,
  "consumption_data": {
    "consumption_kwh": 350.5,
    "gas_usage_kwh": 45.2,
    "water_usage_cu_m": 12.5,
    "total_amount": 105.20,
    "extraction_confidence": 0.92
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/consumption/extract \
  -H "Content-Type: application/json" \
  -d '{"source_id": "vision_a3f9e2b1c4d5"}'
```

**Implementation:** [backend/app.py:632-723](../../backend/app.py#L632-L723)

---

## Retailer Search

### POST `/retailers/search`

Search for Climate Voucher retailers using natural language.

**Request Body:**
```json
{
  "query": "aircon near Bedok",
  "product_category": "air_conditioners",
  "planning_area": "bedok",
  "limit": 10
}
```

**Parameters:**
- `query` (string, required): Natural language search query
- `product_category` (string, optional): Product filter (refrigerators, air_conditioners, etc.)
- `planning_area` (string, optional): Singapore planning area
- `limit` (integer, optional): Max results (default: 10, range: 1-50)

**Response:**
```json
{
  "query": "aircon near Bedok",
  "retailers": [
    {
      "name": "Gain City",
      "products": ["air_conditioners", "refrigerators"],
      "address": "Megastore 1, 21 Ang Mo Kio Ave 9, Singapore 569777",
      "postal_code": "569777",
      "contact": "6552-8888",
      "website": "https://www.gaincity.com",
      "rrf_score": 0.87,
      "component_scores": {
        "semantic_similarity": 0.92,
        "product_match": 0.95,
        "location_relevance": 0.70,
        "retailer_breadth": 0.85,
        "query_intent": 0.88
      }
    }
  ],
  "total_results": 15,
  "returned_count": 10
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/retailers/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "LED lights with good reviews",
    "limit": 5
  }'
```

**Implementation:** [backend/app.py:900-931](../../backend/app.py#L900-L931)

---

### GET `/retailers/products/{product}`

Find all retailers selling a specific Climate Voucher product.

**Path Parameters:**
- `product` (string): Product type (refrigerators, air_conditioners, dc_fans, led_lights, etc.)

**Query Parameters:**
- `limit` (integer, optional): Max results (default: 800)

**Product Options:**
- `refrigerators` (aliases: fridge, refrigerator)
- `air_conditioners` (aliases: aircon, ac, air_con)
- `dc_fans` (aliases: fan, fans)
- `led_lights` (aliases: led, light, lights)
- `washing_machines` (aliases: washer, washing_machine)
- `water_closets` (aliases: toilet, wc)
- `sink_bib_taps_mixers`, `basin_taps_mixers`, `shower_taps_mixers` (aliases: tap, taps)
- `heat_pump_water_heaters` (aliases: water_heater, heat_pump)

**Response:**
```json
{
  "product": "air_conditioners",
  "retailers": [
    {
      "name": "Courts",
      "products": ["air_conditioners", "refrigerators"],
      "rrf_score": 0.89
    }
  ],
  "total_results": 150
}
```

**Example:**
```bash
curl http://localhost:7860/retailers/products/refrigerators?limit=20
```

**Implementation:** [backend/app.py:934-967](../../backend/app.py#L934-L967)

---

### GET `/retailers/energy-ratings/{product_type}`

Get information about energy efficiency ratings for a product type.

**Path Parameters:**
- `product_type` (string): Product type (refrigerators, air_conditioners, etc.)

**Response:**
```json
{
  "product_type": "air_conditioners",
  "rating_system": "Singapore Energy Label",
  "tick_ratings": {
    "1_tick": "Minimum efficiency",
    "2_tick": "Better efficiency",
    "3_tick": "Good efficiency",
    "4_tick": "Very efficient (recommended)",
    "5_tick": "Most efficient (premium)"
  },
  "climate_voucher_eligible": true,
  "voucher_amount": 300,
  "typical_savings": {
    "2_to_4_tick": "25-30% energy reduction",
    "1_to_5_tick": "40-50% energy reduction"
  }
}
```

**Example:**
```bash
curl http://localhost:7860/retailers/energy-ratings/refrigerators
```

**Implementation:** [backend/app.py:970-993](../../backend/app.py#L970-L993)

---

## ROI Calculator

### POST `/retailers/roi/calculate`

Calculate ROI for an appliance upgrade with Climate Voucher.

**Request Body:**
```json
{
  "product_type": "air_conditioners",
  "current_rating": 2,
  "new_rating": 4,
  "product_price": 1200.00,
  "apply_voucher": true,
  "custom_voucher_amount": null
}
```

**Parameters:**
- `product_type` (string, required): Appliance type
- `current_rating` (integer, required): Current tick rating (0-5, 0 for unknown/old)
- `new_rating` (integer, required): New appliance tick rating (1-5)
- `product_price` (float, required): Price in SGD
- `apply_voucher` (boolean, optional): Apply Climate Voucher (default: true)
- `custom_voucher_amount` (float, optional): Custom voucher amount

**Response:**
```json
{
  "product_type": "air_conditioners",
  "current_rating": 2,
  "new_rating": 4,
  "product_price": 1200.00,
  "voucher_applied": true,
  "voucher_amount": 300.00,
  "net_cost": 900.00,
  "annual_kwh_savings": 450.5,
  "annual_savings_sgd": 135.15,
  "payback_years": 6.7,
  "five_year_benefit_sgd": -224.25,
  "ten_year_benefit_sgd": 451.50,
  "recommendation": "Good investment. Payback in 6.7 years with positive 10-year returns.",
  "is_voucher_eligible": true
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/retailers/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "refrigerators",
    "current_rating": 1,
    "new_rating": 5,
    "product_price": 800.00
  }'
```

**Implementation:** [backend/app.py:1029-1059](../../backend/app.py#L1029-L1059)

---

### GET `/retailers/roi/products`

List all product types supported by the ROI calculator.

**Response:**
```json
{
  "products": [
    {
      "product_type": "air_conditioners",
      "min_rating": 1,
      "max_rating": 5,
      "typical_price_range": [800, 3000],
      "annual_usage_hours": 2920
    },
    {
      "product_type": "refrigerators",
      "min_rating": 1,
      "max_rating": 5,
      "typical_price_range": [500, 2500],
      "annual_usage_hours": 8760
    }
  ],
  "voucher_value": 300.00,
  "electricity_rate": 0.30
}
```

**Example:**
```bash
curl http://localhost:7860/retailers/roi/products
```

**Implementation:** [backend/app.py:1062-1077](../../backend/app.py#L1062-L1077)

---

### GET `/retailers/roi/product/{product_type}`

Get detailed information about a specific product for ROI calculation.

**Path Parameters:**
- `product_type` (string): Product type

**Response:**
```json
{
  "product_type": "air_conditioners",
  "ratings": {
    "1": {"consumption_kwh": 1200, "label": "1 tick"},
    "2": {"consumption_kwh": 1050, "label": "2 ticks"},
    "3": {"consumption_kwh": 900, "label": "3 ticks"},
    "4": {"consumption_kwh": 750, "label": "4 ticks"},
    "5": {"consumption_kwh": 600, "label": "5 ticks"}
  },
  "typical_price_range": [800, 3000],
  "annual_usage_hours": 2920,
  "climate_voucher_eligible": true
}
```

**Example:**
```bash
curl http://localhost:7860/retailers/roi/product/washing_machines
```

**Implementation:** [backend/app.py:1080-1093](../../backend/app.py#L1080-L1093)

---

### GET `/retailers/roi/recommendations/{source_id}`

Get personalized appliance upgrade recommendations based on bill diagnosis.

**Path Parameters:**
- `source_id` (string): OCR document source ID

**Query Parameters:**
- `budget_max` (float, optional): Maximum budget in SGD (default: 2000.00)

**Response:**
```json
{
  "source_id": "vision_a3f9e2b1c4d5",
  "budget_max": 2000.00,
  "recommendations": [
    {
      "rank": 1,
      "product_type": "air_conditioners",
      "current_rating": 2,
      "recommended_rating": 4,
      "estimated_price": 1200.00,
      "annual_savings_sgd": 135.15,
      "payback_years": 6.7,
      "priority": "high",
      "reason": "High AC usage detected. Upgrading to 4-tick saves 450 kWh/year."
    }
  ],
  "total_recommendations": 3
}
```

**Example:**
```bash
curl http://localhost:7860/retailers/roi/recommendations/vision_a3f9e2b1c4d5?budget_max=1500
```

**Implementation:** [backend/app.py:1096-1137](../../backend/app.py#L1096-L1137)

---

## Analytics Dashboard

### GET `/analytics/summary`

Get summary statistics for the analytics dashboard.

**Response:**
```json
{
  "total_households": 1250,
  "total_consumption_kwh": 437500.0,
  "average_consumption_kwh": 350.0,
  "anomalies_detected": 45,
  "anomaly_rate_percent": 3.6,
  "active_interventions": 12,
  "total_savings_kwh": 2450.5,
  "generated_at": "2024-06-15T10:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:7860/analytics/summary
```

**Implementation:** [backend/analytics/router.py:180-241](../../backend/analytics/router.py#L180-L241)

---

### GET `/analytics/districts/heatmap`

Get aggregated consumption data by postal district for heatmap visualization.

**Query Parameters:**
- `start_date` (date, optional): Filter by billing period start (YYYY-MM-DD)
- `end_date` (date, optional): Filter by billing period end (YYYY-MM-DD)

**Response:**
```json
{
  "districts": [
    {
      "postal_district": "46",
      "district_name": "Bedok",
      "total_consumption_kwh": 15000.0,
      "average_consumption_kwh": 375.0,
      "median_consumption_kwh": 350.0,
      "household_count": 40
    }
  ],
  "heatmap_points": [
    {
      "postal_district": "46",
      "latitude": 1.3236,
      "longitude": 103.9273,
      "consumption_kwh": 15000.0,
      "intensity": 0.85,
      "household_count": 40
    }
  ],
  "total_households": 1250,
  "total_consumption_kwh": 437500.0,
  "average_consumption_kwh": 350.0,
  "generated_at": "2024-06-15T10:30:00Z"
}
```

**Example:**
```bash
curl "http://localhost:7860/analytics/districts/heatmap?start_date=2024-01-01&end_date=2024-06-30"
```

**Implementation:** [backend/analytics/router.py:248-313](../../backend/analytics/router.py#L248-L313)

---

### GET `/analytics/districts/{district_code}`

Get detailed consumption statistics for a specific postal district.

**Path Parameters:**
- `district_code` (string): 2-digit postal district code (01-83)

**Query Parameters:**
- `include_records` (boolean, optional): Include individual consumption records (default: false)

**Response:**
```json
{
  "postal_district": "46",
  "district_name": "Bedok",
  "statistics": {
    "total_consumption_kwh": 15000.0,
    "average_consumption_kwh": 375.0,
    "median_consumption_kwh": 350.0,
    "household_count": 40
  },
  "records": null
}
```

**Example:**
```bash
curl "http://localhost:7860/analytics/districts/46?include_records=true"
```

**Implementation:** [backend/analytics/router.py:316-351](../../backend/analytics/router.py#L316-L351)

---

### GET `/analytics/anomalies`

Detect consumption anomalies using statistical confidence intervals.

**Query Parameters:**
- `housing_type` (string, optional): Filter by housing type
- `confidence_level` (float, optional): Confidence level (default: 0.95, range: 0.90-0.99)
- `start_date` (date, optional): Filter start date
- `end_date` (date, optional): Filter end date

**Response:**
```json
{
  "cohort_statistics": [
    {
      "housing_type": "hdb_4_room",
      "sample_size": 450,
      "mean_kwh": 320.5,
      "std_dev_kwh": 85.2,
      "median_kwh": 315.0,
      "min_kwh": 150.0,
      "max_kwh": 650.0,
      "ci_lower": 242.1,
      "ci_upper": 398.9,
      "standard_error": 4.02
    }
  ],
  "anomalies": [
    {
      "account_number": "8012345678",
      "postal_code": "460123",
      "housing_type": "hdb_4_room",
      "consumption_kwh": 620.0,
      "billing_period": "2024-05-31",
      "cohort_mean": 320.5,
      "cohort_std": 85.2,
      "z_score": 3.51,
      "p_value": 0.0004,
      "anomaly_type": "HIGH",
      "confidence_level": 0.95,
      "deviation_kwh": 299.5,
      "deviation_percent": 93.4
    }
  ],
  "total_records_analyzed": 1250,
  "anomaly_count": 45,
  "anomaly_rate_percent": 3.6,
  "methodology": "95% Confidence Interval (z-score > 1.96)"
}
```

**Example:**
```bash
curl "http://localhost:7860/analytics/anomalies?housing_type=hdb_4_room&confidence_level=0.99"
```

**Implementation:** [backend/analytics/router.py:358-458](../../backend/analytics/router.py#L358-L458)

---

### POST `/analytics/interventions`

Record a new energy efficiency intervention.

**Request Body:**
```json
{
  "account_number": "8012345678",
  "intervention_type": "led_retrofit",
  "intervention_date": "2024-03-15",
  "postal_code": "460123",
  "housing_type": "hdb_4_room",
  "description": "Replaced all lights with 5-tick LED bulbs",
  "cost_sgd": 250.00
}
```

**Intervention Types:**
- `cool_paint`: Cool roof/wall paint
- `led_retrofit`: LED lighting upgrade
- `solar_panel`: Solar PV installation
- `aircon_upgrade`: Air conditioning upgrade
- `insulation`: Thermal insulation
- `smart_meter`: Smart meter/monitoring system

**Response:**
```json
{
  "intervention_id": "int_a1b2c3d4",
  "account_number": "8012345678",
  "intervention_type": "led_retrofit",
  "intervention_date": "2024-03-15",
  "housing_type": "hdb_4_room",
  "pre_consumption_kwh": 380.5,
  "post_consumption_kwh": 320.2,
  "savings_kwh": -60.3,
  "savings_percent": -15.8
}
```

**Example:**
```bash
curl -X POST http://localhost:7860/analytics/interventions \
  -H "Content-Type: application/json" \
  -d '{
    "account_number": "8012345678",
    "intervention_type": "aircon_upgrade",
    "intervention_date": "2024-04-01",
    "cost_sgd": 1200.00
  }'
```

**Implementation:** [backend/analytics/router.py:574-607](../../backend/analytics/router.py#L574-L607)

---

## Related Documentation

- [Graph API](./graph-api.md) - LangGraph invocation patterns
- [Tools Reference](./tools.md) - Agent tool specifications
- [Schemas](./schemas.md) - Pydantic model definitions
- [Data Flow](../01-architecture/data-flow.md) - Request/response flows
- [Deployment](../01-architecture/deployment.md) - API hosting configuration

---

**Generated:** 2024-06-15
**API Version:** 1.0.0
**Base Implementation:** [backend/app.py](../../backend/app.py)
