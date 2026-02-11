# Pydantic Schemas Reference

Complete specification for all Pydantic data models used in VoltPulse-SG.

---

## Table of Contents

1. [Overview](#overview)
2. [OCR & Extraction](#ocr--extraction)
3. [Bill Diagnosis](#bill-diagnosis)
4. [Retailer & RRF](#retailer--rrf)
5. [ROI Calculation](#roi-calculation)
6. [Analytics](#analytics)
7. [Enums & Constants](#enums--constants)

---

## Overview

VoltPulse uses **Pydantic v2** for data validation, serialization, and API schema generation. All models are strictly typed with validation rules.

**Key Features:**
- Automatic JSON serialization/deserialization
- Field-level validation with constraints
- OpenAPI schema generation for FastAPI
- Type hints for IDE autocomplete
- Default values and optional fields

---

## OCR & Extraction

### ElectricityBillExtraction

Complete extraction schema for Singapore utility bills.

**Location:** `backend/models/utility_bill.py`

```python
class ElectricityBillExtraction(BaseModel):
    # Customer Information
    customer_name: Optional[str] = None
    account_number: Optional[str] = None
    premise_address: Optional[str] = None

    # Provider Details
    provider_name: Optional[str] = None
    customer_service_number: Optional[str] = None

    # Billing Period
    billing_period_start: Optional[str] = None  # ISO date
    billing_period_end: Optional[str] = None    # ISO date
    billing_days: Optional[int] = None

    # Consumption (Primary)
    consumption_kwh: Optional[float] = None          # Electricity
    daily_average_kwh: Optional[float] = None
    gas_usage_kwh: Optional[float] = None            # Gas
    water_usage_cu_m: Optional[float] = None         # Water

    # Financial
    total_amount: Optional[float] = None             # Total bill (SGD)
    energy_charges: Optional[float] = None           # Energy-only charges
    gst_amount: Optional[float] = None               # GST (9%)

    # Consumption Trends
    consumption_trends: List[ConsumptionTrend] = []  # Multi-month data

    # Metadata
    extraction_confidence: float = 0.0               # 0.0-1.0
    raw_ocr_text: Optional[str] = None               # Full OCR text
```

**Example:**
```json
{
  "customer_name": "JOHN TAN",
  "account_number": "8012345678",
  "premise_address": "BLK 123 BEDOK NORTH ST 2 #05-123 Singapore 460123",
  "provider_name": "SP Services",
  "billing_period_start": "2024-01-01",
  "billing_period_end": "2024-01-31",
  "billing_days": 31,
  "consumption_kwh": 350.5,
  "daily_average_kwh": 11.3,
  "total_amount": 105.20,
  "energy_charges": 93.50,
  "gst_amount": 7.93,
  "extraction_confidence": 0.92,
  "consumption_trends": [
    {
      "service_type": "Electricity",
      "unit": "kWh",
      "monthly_data": [
        {"month": "Jan", "value": 320.0},
        {"month": "Feb", "value": 340.0},
        {"month": "Mar", "value": 350.5}
      ]
    }
  ]
}
```

---

### ConsumptionTrend

Multi-month consumption trend data extracted from bar charts.

```python
class ConsumptionTrend(BaseModel):
    service_type: str                            # "Electricity", "Gas", "Water"
    unit: Optional[str] = None                   # "kWh", "Cu M"
    monthly_data: List[MonthlyConsumption] = []  # Time series

class MonthlyConsumption(BaseModel):
    month: str                                   # "Jan", "Feb", "Mar", etc.
    value: float                                 # Consumption value
```

**Example:**
```json
{
  "service_type": "Electricity",
  "unit": "kWh",
  "monthly_data": [
    {"month": "Nov", "value": 310.0},
    {"month": "Dec", "value": 325.0},
    {"month": "Jan", "value": 350.5}
  ]
}
```

---

## Bill Diagnosis

### DiagnosisResult

Complete bill diagnosis with anomalies, efficiency analysis, and recommendations.

**Location:** `backend/models/diagnosis.py`

```python
class DiagnosisResult(BaseModel):
    # Health Scoring
    overall_health_score: int                    # 0-100
    health_grade: str                            # "A", "B", "C", "D", "F"

    # Issues Detected
    anomalies: List[AnomalyFlag] = []            # Consumption spikes, outliers
    efficiency_issues: List[EfficiencyIssue] = [] # Above-average consumption
    trend_warnings: List[TrendWarning] = []      # Increasing trends

    # Recommendations
    recommendations: List[Recommendation] = []    # Prioritized actions

    # Metadata
    diagnosis_date: str                          # ISO datetime
    billing_period_analyzed: Optional[str] = None
```

**Example:**
```json
{
  "overall_health_score": 75,
  "health_grade": "C",
  "anomalies": [
    {
      "type": "spike",
      "severity": "medium",
      "description": "Consumption increased 32% compared to previous month",
      "affected_utility": "electricity",
      "value": 462.0,
      "threshold": 350.0,
      "deviation_percent": 32.0
    }
  ],
  "efficiency_issues": [
    {
      "utility_type": "electricity",
      "current_value": 350.5,
      "national_average": 270.0,
      "deviation_percent": 29.8,
      "severity": "medium",
      "potential_monthly_savings_sgd": 24.15,
      "potential_annual_savings_sgd": 289.80
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "category": "appliance",
      "title": "Upgrade to 4-tick air conditioner",
      "description": "Your aircon usage is high. Upgrading to a 4-tick model could save 450 kWh/year.",
      "potential_savings_percent": 25.0,
      "estimated_implementation_cost": 1200.00,
      "climate_voucher_eligible": true
    }
  ],
  "diagnosis_date": "2024-06-15T10:30:00Z"
}
```

---

### AnomalyFlag

Detected consumption anomaly with severity.

```python
class AnomalyFlag(BaseModel):
    type: AnomalyType                            # spike, high_consumption, unusual_pattern
    severity: Severity                           # low, medium, high
    description: str
    affected_utility: str                        # electricity, gas, water
    value: float
    threshold: float
    deviation_percent: Optional[float] = None
```

---

### EfficiencyIssue

Efficiency comparison against benchmarks.

```python
class EfficiencyIssue(BaseModel):
    utility_type: str
    current_value: float
    national_average: float
    neighbour_average: Optional[float] = None
    deviation_percent: float
    severity: Severity
    potential_monthly_savings_sgd: float
    potential_annual_savings_sgd: float
```

---

### Recommendation

Actionable recommendation for energy reduction.

```python
class Recommendation(BaseModel):
    priority: int                                # 1-5 (1 = highest)
    category: str                                # appliance, behavior, monitoring, maintenance
    title: str
    description: str
    potential_savings_percent: Optional[float] = None
    estimated_implementation_cost: Optional[float] = None
    climate_voucher_eligible: bool = False
```

---

## Retailer & RRF

### ScoredRetailer

Retailer with RRF component scores.

**Location:** `backend/recommender/rrf_scorer.py`

```python
class ScoredRetailer(BaseModel):
    retailer: SimilarityResult                   # Base retailer data

    # RRF Component Scores (0.0-1.0)
    semantic_score: float                        # Semantic similarity
    product_score: float                         # Product match (Jaccard)
    location_score: float                        # Location relevance
    breadth_score: float                         # Retailer breadth
    intent_score: float                          # Query intent match

    # Final Score
    final_rrf_score: float                       # Weighted RRF combination

    # Ranking
    rank: int                                    # Position in result list
```

**Example:**
```json
{
  "retailer": {
    "id": "retailer_abc123",
    "form_type": "retailer",
    "form_data": {
      "retail_outlet": "Gain City",
      "outlet_address": "Megastore 1, 21 Ang Mo Kio Ave 9, Singapore 569777",
      "postal_code": "569777",
      "planning_area": "Ang Mo Kio",
      "website": "https://www.gaincity.com",
      "eligible_products": ["refrigerators", "air_conditioners"]
    },
    "score": 0.8524
  },
  "semantic_score": 0.92,
  "product_score": 0.95,
  "location_score": 0.70,
  "breadth_score": 0.85,
  "intent_score": 0.88,
  "final_rrf_score": 0.8734,
  "rank": 1
}
```

---

### SimilarityResult

Vector search result with metadata.

**Location:** `backend/recommender/vector_store.py`

```python
class SimilarityResult(BaseModel):
    id: str                                      # Source ID
    form_type: str                               # ocr, vision, retailer, consumption
    form_data: Dict[str, Any]                    # JSON metadata
    score: float                                 # Similarity score (0.0-1.0)
    distance: Optional[float] = None             # L2 distance
```

---

## ROI Calculation

### ROIResult

Complete ROI analysis for appliance upgrade.

**Location:** `backend/services/roi_calculator.py`

```python
class ROIResult(BaseModel):
    # Product Details
    product_type: str
    current_rating: int                          # 0-5
    new_rating: int                              # 1-5
    product_price: float                         # SGD

    # Climate Voucher
    voucher_applied: bool
    voucher_amount: float                        # $300 or custom
    net_cost: float                              # After voucher
    is_voucher_eligible: bool

    # Energy Savings
    annual_kwh_savings: float
    annual_savings_sgd: float                    # At $0.30/kWh

    # ROI Metrics
    payback_years: float                         # Break-even point
    five_year_benefit_sgd: float                 # Net benefit at 5 years
    ten_year_benefit_sgd: float                  # Net benefit at 10 years

    # Recommendation
    recommendation: str                          # Human-readable analysis
```

**Example:**
```json
{
  "product_type": "air_conditioners",
  "current_rating": 2,
  "new_rating": 4,
  "product_price": 1200.00,
  "voucher_applied": true,
  "voucher_amount": 300.00,
  "net_cost": 900.00,
  "is_voucher_eligible": true,
  "annual_kwh_savings": 450.5,
  "annual_savings_sgd": 135.15,
  "payback_years": 6.7,
  "five_year_benefit_sgd": -224.25,
  "ten_year_benefit_sgd": 451.50,
  "recommendation": "Good investment. Payback in 6.7 years with positive 10-year returns."
}
```

---

## Analytics

### DistrictConsumption

Aggregated consumption statistics by postal district.

**Location:** `backend/analytics/models.py`

```python
class DistrictConsumption(BaseModel):
    postal_district: str                         # 2-digit code (01-83)
    district_name: Optional[str] = None          # "Bedok", "Tampines", etc.
    total_consumption_kwh: float
    average_consumption_kwh: float
    median_consumption_kwh: Optional[float] = None
    household_count: int
```

**Example:**
```json
{
  "postal_district": "46",
  "district_name": "Bedok",
  "total_consumption_kwh": 15000.0,
  "average_consumption_kwh": 375.0,
  "median_consumption_kwh": 350.0,
  "household_count": 40
}
```

---

### CohortStatistics

Statistical summary for housing type cohort.

```python
class CohortStatistics(BaseModel):
    housing_type: str                            # hdb_4_room, condo, etc.
    sample_size: int
    mean_kwh: float
    std_dev_kwh: float
    median_kwh: float
    min_kwh: float
    max_kwh: float
    ci_lower: float                              # 95% CI lower bound
    ci_upper: float                              # 95% CI upper bound
    standard_error: float                        # SEM
```

**Example:**
```json
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
```

---

### AnomalyRecord

Statistical anomaly detection record.

```python
class AnomalyRecord(BaseModel):
    account_number: str
    postal_code: Optional[str] = None
    housing_type: str
    consumption_kwh: float
    billing_period: Optional[str] = None

    # Cohort Comparison
    cohort_mean: float
    cohort_std: float

    # Statistical Measures
    z_score: float                               # Standard deviations from mean
    p_value: float                               # Two-tailed probability
    anomaly_type: str                            # "HIGH" or "LOW"
    confidence_level: float                      # 0.95, 0.99, etc.

    # Deviation
    deviation_kwh: float
    deviation_percent: float
```

**Example:**
```json
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
```

---

### InterventionSummary

Energy efficiency intervention tracking.

```python
class InterventionSummary(BaseModel):
    intervention_id: str
    account_number: str
    intervention_type: str                       # cool_paint, led_retrofit, solar_panel, etc.
    intervention_date: str                       # ISO date
    housing_type: Optional[str] = None

    # Before/After
    pre_consumption_kwh: Optional[float] = None
    post_consumption_kwh: Optional[float] = None
    savings_kwh: Optional[float] = None          # Negative = improvement
    savings_percent: Optional[float] = None
```

**Example:**
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

---

## Enums & Constants

### Severity

```python
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

---

### AnomalyType

```python
class AnomalyType(str, Enum):
    SPIKE = "spike"
    HIGH_CONSUMPTION = "high_consumption"
    UNUSUAL_PATTERN = "unusual_pattern"
    BILLING_DISCREPANCY = "billing_discrepancy"
```

---

### HousingType

```python
class HousingType(str, Enum):
    HDB_1_ROOM = "hdb_1_room"
    HDB_2_ROOM = "hdb_2_room"
    HDB_3_ROOM = "hdb_3_room"
    HDB_4_ROOM = "hdb_4_room"
    HDB_5_ROOM = "hdb_5_room"
    HDB_EXECUTIVE = "hdb_executive"
    CONDO = "condo"
    LANDED = "landed"
    COMMERCIAL = "commercial"
    UNKNOWN = "unknown"
```

---

### InterventionType

```python
class InterventionType(str, Enum):
    COOL_PAINT = "cool_paint"
    LED_RETROFIT = "led_retrofit"
    SOLAR_PANEL = "solar_panel"
    AIRCON_UPGRADE = "aircon_upgrade"
    INSULATION = "insulation"
    SMART_METER = "smart_meter"
```

---

## Validation Rules

### Field Constraints

Common validation patterns used across models:

```python
from pydantic import BaseModel, Field, field_validator

class ExampleModel(BaseModel):
    # Numeric ranges
    rating: int = Field(ge=1, le=5, description="Tick rating 1-5")

    # Positive values
    price: float = Field(gt=0, description="Must be positive")

    # Optional with default
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # String patterns
    postal_code: str = Field(pattern=r"^\d{6}$", description="6-digit postal code")

    # Custom validation
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

---

### JSON Serialization

All models support `.model_dump()` for JSON serialization:

```python
result = DiagnosisResult(
    overall_health_score=75,
    health_grade="C",
    anomalies=[],
    efficiency_issues=[],
    trend_warnings=[],
    recommendations=[],
    diagnosis_date="2024-06-15T10:30:00Z"
)

# Convert to dict
data = result.model_dump()

# Convert to JSON string
json_str = result.model_dump_json(indent=2)

# Exclude fields
data = result.model_dump(exclude={"raw_ocr_text"})
```

---

## Related Documentation

- [Endpoints Reference](./endpoints.md) - API request/response schemas
- [OCR Extraction](../04-services/ocr-extraction.md) - ElectricityBillExtraction usage
- [Bill Diagnosis](../04-services/bill-diagnosis.md) - DiagnosisResult generation
- [RRF Algorithm](../03-recommender-system/rrf-algorithm.md) - ScoredRetailer scoring
- [ROI Calculator](../04-services/roi-calculator.md) - ROIResult calculation

---

**Generated:** 2024-06-15
**Pydantic Version:** 2.x
**Models Location:** [backend/models/](../../backend/models/)
