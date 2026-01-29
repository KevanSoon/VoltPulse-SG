"""Pydantic models for bill diagnosis and analysis results."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    """Severity levels for issues and warnings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyType(str, Enum):
    """Types of consumption anomalies."""
    SPIKE = "spike"
    HIGH_CONSUMPTION = "high_consumption"
    UNUSUAL_PATTERN = "unusual_pattern"
    BILLING_DISCREPANCY = "billing_discrepancy"


class AnomalyFlag(BaseModel):
    """Represents a detected anomaly in consumption data."""

    type: AnomalyType = Field(
        ...,
        description="Type of anomaly detected"
    )
    severity: Severity = Field(
        ...,
        description="Severity level of the anomaly"
    )
    description: str = Field(
        ...,
        description="Human-readable description of the anomaly"
    )
    affected_utility: str = Field(
        ...,
        description="Utility type affected (electricity, gas, water)"
    )
    value: float = Field(
        ...,
        description="The anomalous value detected"
    )
    threshold: float = Field(
        ...,
        description="The threshold that was exceeded"
    )
    deviation_percent: Optional[float] = Field(
        None,
        description="Percentage deviation from expected value"
    )


class EfficiencyIssue(BaseModel):
    """Represents an efficiency issue compared to benchmarks."""

    utility_type: str = Field(
        ...,
        description="Type of utility (electricity, gas, water)"
    )
    current_value: float = Field(
        ...,
        description="User's current consumption value"
    )
    national_average: float = Field(
        ...,
        description="National average for comparison"
    )
    neighbour_average: Optional[float] = Field(
        None,
        description="Neighbour average if available"
    )
    deviation_percent: float = Field(
        ...,
        description="Percentage above/below national average"
    )
    severity: Severity = Field(
        ...,
        description="Severity based on deviation magnitude"
    )
    potential_monthly_savings_sgd: float = Field(
        ...,
        description="Estimated monthly savings if reduced to average"
    )
    potential_annual_savings_sgd: float = Field(
        ...,
        description="Estimated annual savings if reduced to average"
    )


class TrendWarning(BaseModel):
    """Represents a warning about consumption trends."""

    utility_type: str = Field(
        ...,
        description="Type of utility (electricity, gas, water)"
    )
    trend_direction: str = Field(
        ...,
        description="Direction of trend: 'increasing', 'decreasing', 'volatile'"
    )
    months_affected: int = Field(
        ...,
        description="Number of months showing this trend"
    )
    average_monthly_change_percent: Optional[float] = Field(
        None,
        description="Average month-over-month change percentage"
    )
    description: str = Field(
        ...,
        description="Human-readable description of the trend"
    )
    severity: Severity = Field(
        ...,
        description="Severity of the trend warning"
    )


class RecommendationCategory(str, Enum):
    """Categories of recommendations."""
    BEHAVIOR = "behavior"
    APPLIANCE = "appliance"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"


class Recommendation(BaseModel):
    """A specific actionable recommendation."""

    category: RecommendationCategory = Field(
        ...,
        description="Category of the recommendation"
    )
    title: str = Field(
        ...,
        description="Short title for the recommendation"
    )
    description: str = Field(
        ...,
        description="Detailed description of the recommendation"
    )
    potential_savings_percent: Optional[float] = Field(
        None,
        description="Estimated savings percentage if implemented"
    )
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority level (1=highest, 5=lowest)"
    )


class DiagnosisResult(BaseModel):
    """Complete diagnosis result for a utility bill."""

    # Analysis results
    anomalies: List[AnomalyFlag] = Field(
        default_factory=list,
        description="List of detected anomalies"
    )
    efficiency_issues: List[EfficiencyIssue] = Field(
        default_factory=list,
        description="List of efficiency issues found"
    )
    trend_warnings: List[TrendWarning] = Field(
        default_factory=list,
        description="List of trend warnings"
    )

    # Overall assessment
    overall_health_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall bill health score (0-100, higher is better)"
    )
    health_grade: str = Field(
        ...,
        description="Letter grade (A, B, C, D, F)"
    )

    # Recommendations
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="List of actionable recommendations"
    )

    # Summary
    summary: str = Field(
        ...,
        description="Brief summary of the diagnosis"
    )

    # Metadata
    diagnosis_timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When the diagnosis was performed"
    )
    utilities_analyzed: List[str] = Field(
        default_factory=list,
        description="List of utilities that were analyzed"
    )

    # Potential savings
    total_potential_monthly_savings_sgd: float = Field(
        0.0,
        description="Total potential monthly savings across all utilities"
    )
    total_potential_annual_savings_sgd: float = Field(
        0.0,
        description="Total potential annual savings across all utilities"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "anomalies": [
                    {
                        "type": "spike",
                        "severity": "high",
                        "description": "Electricity consumption spiked 45% compared to previous month",
                        "affected_utility": "electricity",
                        "value": 520.0,
                        "threshold": 400.0,
                        "deviation_percent": 45.0
                    }
                ],
                "efficiency_issues": [
                    {
                        "utility_type": "electricity",
                        "current_value": 450.0,
                        "national_average": 350.0,
                        "deviation_percent": 28.6,
                        "severity": "medium",
                        "potential_monthly_savings_sgd": 36.0,
                        "potential_annual_savings_sgd": 432.0
                    }
                ],
                "trend_warnings": [
                    {
                        "utility_type": "electricity",
                        "trend_direction": "increasing",
                        "months_affected": 3,
                        "average_monthly_change_percent": 8.5,
                        "description": "Electricity usage has been increasing for the past 3 months",
                        "severity": "medium"
                    }
                ],
                "overall_health_score": 65.0,
                "health_grade": "C",
                "recommendations": [
                    {
                        "category": "appliance",
                        "title": "Upgrade to 5-tick air conditioner",
                        "description": "Your high electricity usage suggests AC is a major contributor. A 5-tick AC could save up to 35% on cooling costs.",
                        "potential_savings_percent": 15.0,
                        "priority": 1
                    }
                ],
                "summary": "Your electricity consumption is 28.6% above the national average with an increasing trend. Consider upgrading appliances and adjusting usage habits.",
                "utilities_analyzed": ["electricity", "gas", "water"],
                "total_potential_monthly_savings_sgd": 42.0,
                "total_potential_annual_savings_sgd": 504.0
            }
        }
