"""Pydantic models for analytics API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ============================================================================
# District Heatmap Models
# ============================================================================

class DistrictConsumption(BaseModel):
    """Aggregated consumption data for a postal district."""
    postal_district: str = Field(..., description="2-digit postal district (01-83)")
    district_name: Optional[str] = Field(None, description="District area name")
    postal_sector: Optional[str] = Field(None, description="4-digit postal sector")
    total_consumption_kwh: float
    average_consumption_kwh: float
    median_consumption_kwh: Optional[float] = None
    household_count: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class HeatmapDataPoint(BaseModel):
    """Single point on the heatmap."""
    postal_district: str
    latitude: float
    longitude: float
    consumption_kwh: float
    intensity: float = Field(..., ge=0, le=1, description="Normalized intensity 0-1")
    household_count: int


class DistrictHeatmapResponse(BaseModel):
    """Response for district heatmap endpoint."""
    districts: List[DistrictConsumption]
    heatmap_points: List[HeatmapDataPoint]
    total_households: int
    total_consumption_kwh: float
    average_consumption_kwh: float
    generated_at: str


class DistrictDetailResponse(BaseModel):
    """Detailed response for a specific district."""
    postal_district: str
    district_name: str
    statistics: DistrictConsumption
    records: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Anomaly Detection Models
# ============================================================================

class CohortStatistics(BaseModel):
    """Statistical measures for a housing type cohort."""
    housing_type: str
    sample_size: int
    mean_kwh: float
    std_dev_kwh: float
    median_kwh: float
    min_kwh: float
    max_kwh: float

    # 95% Confidence Interval (1.96 * sigma)
    ci_lower: float = Field(..., description="Lower bound of 95% CI")
    ci_upper: float = Field(..., description="Upper bound of 95% CI")

    # For z-test/t-test significance
    standard_error: float


class AnomalyRecord(BaseModel):
    """A flagged anomaly with statistical evidence."""
    account_number: str
    postal_code: Optional[str] = None
    housing_type: str
    consumption_kwh: float
    billing_period: Optional[str] = None

    # Statistical measures
    cohort_mean: float
    cohort_std: float
    z_score: float = Field(..., description="Standard deviations from mean")
    p_value: float = Field(..., description="Two-tailed p-value")

    # Classification
    anomaly_type: str = Field(..., description="HIGH or LOW consumption outlier")
    confidence_level: float = Field(
        default=0.95, description="95% = outside 1.96 sigma"
    )

    # Contextual
    deviation_kwh: float = Field(..., description="Absolute deviation from cohort mean")
    deviation_percent: float


class AnomalyDetectionRequest(BaseModel):
    """Request parameters for anomaly detection."""
    housing_type: Optional[str] = Field(None, description="Filter by housing type")
    confidence_level: float = Field(
        default=0.95, ge=0.90, le=0.99, description="Confidence level (default 95%)"
    )
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection endpoint."""
    cohort_statistics: List[CohortStatistics]
    anomalies: List[AnomalyRecord]
    total_records_analyzed: int
    anomaly_count: int
    anomaly_rate_percent: float
    analysis_period: Optional[str] = None
    methodology: str = "95% Confidence Interval (z-score > 1.96)"


class AccountAnomalyResponse(BaseModel):
    """Response for checking if a specific account is anomalous."""
    account_number: str
    is_anomaly: bool
    housing_type: str
    consumption_kwh: float
    cohort_statistics: CohortStatistics
    z_score: float
    p_value: float
    anomaly_type: Optional[str] = None
    recommendation: Optional[str] = None


# ============================================================================
# Intervention Tracking Models
# ============================================================================

class InterventionCreateRequest(BaseModel):
    """Request for creating a new intervention."""
    account_number: str
    intervention_type: str
    intervention_date: date
    postal_code: Optional[str] = None
    housing_type: Optional[str] = None
    description: Optional[str] = None
    cost_sgd: Optional[float] = None


class InterventionSummary(BaseModel):
    """Summary of an intervention's impact."""
    intervention_id: str
    account_number: str
    intervention_type: str
    intervention_date: str
    housing_type: Optional[str] = None

    pre_consumption_kwh: Optional[float] = None
    post_consumption_kwh: Optional[float] = None
    savings_kwh: Optional[float] = None
    savings_percent: Optional[float] = None
    savings_sgd_estimated: Optional[float] = None

    statistical_significance: Optional[bool] = None
    p_value: Optional[float] = None


class InterventionListResponse(BaseModel):
    """Response for listing interventions."""
    interventions: List[InterventionSummary]
    total_count: int
    page: int = 1
    page_size: int = 20


class InterventionAnalysisRequest(BaseModel):
    """Request for before/after analysis."""
    account_number: str
    intervention_date: date
    intervention_type: str
    months_before: int = Field(default=3, ge=1, le=12)
    months_after: int = Field(default=3, ge=1, le=12)


class MonthlyDataPoint(BaseModel):
    """Monthly consumption data point for charts."""
    month: str
    consumption_kwh: float
    is_after_intervention: bool


class InterventionAnalysisResponse(BaseModel):
    """Detailed before/after analysis."""
    account_number: str
    intervention_type: str
    intervention_date: str

    # Before period
    before_period: Dict[str, str]
    before_avg_kwh: float
    before_std_kwh: float
    before_data_points: int

    # After period
    after_period: Dict[str, str]
    after_avg_kwh: float
    after_std_kwh: float
    after_data_points: int

    # Monthly data for visualization
    monthly_data: List[MonthlyDataPoint]

    # Statistical analysis
    consumption_change_kwh: float
    consumption_change_percent: float
    t_statistic: float
    p_value: float
    is_significant: bool = Field(..., description="p < 0.05")
    confidence_interval_95: Dict[str, float]

    # Projections
    projected_annual_savings_kwh: Optional[float] = None
    projected_annual_savings_sgd: Optional[float] = None


class InterventionEffectivenessResponse(BaseModel):
    """Aggregate effectiveness statistics for interventions."""
    intervention_type: Optional[str] = None
    housing_type: Optional[str] = None
    sample_size: int
    avg_savings_kwh: float
    avg_savings_percent: float
    median_savings_kwh: float
    std_savings_kwh: float
    ci_lower: float
    ci_upper: float
    significant_improvements_count: int
    significant_improvements_percent: float


# ============================================================================
# Dashboard Summary Models
# ============================================================================

class AnalyticsSummary(BaseModel):
    """Summary statistics for analytics dashboard."""
    total_households: int
    total_consumption_kwh: float
    average_consumption_kwh: float
    anomalies_detected: int
    anomaly_rate_percent: float
    active_interventions: int
    total_savings_kwh: float
    generated_at: str
