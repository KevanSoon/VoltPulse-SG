"""Bill diagnosis service for analyzing utility bill consumption patterns.

Analyzes extracted bill data to detect:
- Consumption anomalies (spikes, unusual patterns)
- Efficiency issues (comparison to national averages)
- Trend warnings (increasing consumption patterns)
- Personalized recommendations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from models.diagnosis import (
    DiagnosisResult,
    AnomalyFlag,
    AnomalyType,
    EfficiencyIssue,
    TrendWarning,
    Recommendation,
    RecommendationCategory,
    Severity,
)
from models.utility_bill import ElectricityBillExtraction, ConsumptionTrend
from analytics.services.statistical import StatisticalAnalyzer


# Singapore electricity rate (SGD per kWh)
ELECTRICITY_RATE_SGD = 0.36
GAS_RATE_SGD = 0.25  # Approximate
WATER_RATE_SGD = 2.74  # Per cubic meter (includes waterborne fee)

# National averages for Singapore households (approximate monthly values)
NATIONAL_AVERAGES = {
    "electricity": 400.0,  # kWh per month for 4-room HDB
    "gas": 50.0,  # kWh per month
    "water": 15.0,  # Cubic meters per month
}

# Thresholds for severity classification
DEVIATION_THRESHOLDS = {
    "low": 10.0,  # 10% above average
    "medium": 25.0,  # 25% above average
    "high": 50.0,  # 50% above average
}

# Spike detection threshold (month-over-month increase)
SPIKE_THRESHOLD_PERCENT = 20.0


class BillDiagnosisService:
    """Service for diagnosing utility bill consumption patterns."""

    def __init__(self):
        self.stats_analyzer = StatisticalAnalyzer()

    async def diagnose(
        self,
        extraction: ElectricityBillExtraction
    ) -> DiagnosisResult:
        """Perform comprehensive diagnosis on extracted bill data.

        Args:
            extraction: The extracted bill data from OCR

        Returns:
            DiagnosisResult with anomalies, efficiency issues, and recommendations
        """
        anomalies: List[AnomalyFlag] = []
        efficiency_issues: List[EfficiencyIssue] = []
        trend_warnings: List[TrendWarning] = []
        recommendations: List[Recommendation] = []
        utilities_analyzed: List[str] = []

        # Analyze electricity
        if extraction.consumption_kwh is not None:
            utilities_analyzed.append("electricity")
            elec_trend = self._find_trend(extraction.consumption_trends, "Electricity")

            elec_anomalies = self._detect_anomalies(
                current_value=extraction.consumption_kwh,
                monthly_data=elec_trend.monthly_data if elec_trend else [],
                utility_type="electricity"
            )
            anomalies.extend(elec_anomalies)

            elec_efficiency = self._check_efficiency(
                current_value=extraction.consumption_kwh,
                national_avg=elec_trend.national_average if elec_trend else NATIONAL_AVERAGES["electricity"],
                neighbour_avg=elec_trend.neighbour_average if elec_trend else None,
                utility_type="electricity",
                rate=ELECTRICITY_RATE_SGD
            )
            if elec_efficiency:
                efficiency_issues.append(elec_efficiency)

            if elec_trend:
                elec_trend_warning = self._analyze_trend(elec_trend, "electricity")
                if elec_trend_warning:
                    trend_warnings.append(elec_trend_warning)

        # Analyze gas
        if extraction.gas_usage_kwh is not None:
            utilities_analyzed.append("gas")
            gas_trend = self._find_trend(extraction.consumption_trends, "Gas")

            gas_efficiency = self._check_efficiency(
                current_value=extraction.gas_usage_kwh,
                national_avg=gas_trend.national_average if gas_trend else NATIONAL_AVERAGES["gas"],
                neighbour_avg=gas_trend.neighbour_average if gas_trend else None,
                utility_type="gas",
                rate=GAS_RATE_SGD
            )
            if gas_efficiency:
                efficiency_issues.append(gas_efficiency)

            if gas_trend:
                gas_trend_warning = self._analyze_trend(gas_trend, "gas")
                if gas_trend_warning:
                    trend_warnings.append(gas_trend_warning)

        # Analyze water
        if extraction.water_usage_cu_m is not None:
            utilities_analyzed.append("water")
            water_trend = self._find_trend(extraction.consumption_trends, "Water")

            water_efficiency = self._check_efficiency(
                current_value=extraction.water_usage_cu_m,
                national_avg=water_trend.national_average if water_trend else NATIONAL_AVERAGES["water"],
                neighbour_avg=water_trend.neighbour_average if water_trend else None,
                utility_type="water",
                rate=WATER_RATE_SGD
            )
            if water_efficiency:
                efficiency_issues.append(water_efficiency)

            if water_trend:
                water_trend_warning = self._analyze_trend(water_trend, "water")
                if water_trend_warning:
                    trend_warnings.append(water_trend_warning)

        # Generate recommendations based on issues found
        recommendations = self._generate_recommendations(
            anomalies, efficiency_issues, trend_warnings
        )

        # Calculate overall health score
        health_score = self._calculate_health_score(
            anomalies, efficiency_issues, trend_warnings
        )
        health_grade = self._score_to_grade(health_score)

        # Calculate total potential savings
        total_monthly_savings = sum(
            issue.potential_monthly_savings_sgd for issue in efficiency_issues
        )
        total_annual_savings = total_monthly_savings * 12

        # Generate summary
        summary = self._generate_summary(
            anomalies, efficiency_issues, trend_warnings, health_grade
        )

        return DiagnosisResult(
            anomalies=anomalies,
            efficiency_issues=efficiency_issues,
            trend_warnings=trend_warnings,
            overall_health_score=health_score,
            health_grade=health_grade,
            recommendations=recommendations,
            summary=summary,
            utilities_analyzed=utilities_analyzed,
            total_potential_monthly_savings_sgd=round(total_monthly_savings, 2),
            total_potential_annual_savings_sgd=round(total_annual_savings, 2),
        )

    def _find_trend(
        self,
        trends: List[ConsumptionTrend],
        service_type: str
    ) -> Optional[ConsumptionTrend]:
        """Find the consumption trend for a specific service type."""
        for trend in trends:
            if trend.service_type and trend.service_type.lower() == service_type.lower():
                return trend
        return None

    def _detect_anomalies(
        self,
        current_value: float,
        monthly_data: List[Any],
        utility_type: str
    ) -> List[AnomalyFlag]:
        """Detect consumption anomalies from monthly data."""
        anomalies = []

        if not monthly_data or len(monthly_data) < 2:
            return anomalies

        # Extract values from monthly data
        values = []
        for data in monthly_data:
            if hasattr(data, 'value') and data.value is not None:
                values.append(data.value)

        if len(values) < 2:
            return anomalies

        # Check for month-over-month spike
        if len(values) >= 2:
            prev_value = values[-2] if len(values) >= 2 else values[0]
            current = values[-1]

            if prev_value > 0:
                change_percent = ((current - prev_value) / prev_value) * 100

                if change_percent >= SPIKE_THRESHOLD_PERCENT:
                    severity = Severity.LOW
                    if change_percent >= 40:
                        severity = Severity.HIGH
                    elif change_percent >= 30:
                        severity = Severity.MEDIUM

                    anomalies.append(AnomalyFlag(
                        type=AnomalyType.SPIKE,
                        severity=severity,
                        description=f"{utility_type.capitalize()} consumption spiked {change_percent:.1f}% compared to previous month",
                        affected_utility=utility_type,
                        value=current,
                        threshold=prev_value * (1 + SPIKE_THRESHOLD_PERCENT / 100),
                        deviation_percent=change_percent
                    ))

        # Check for high consumption using statistical analysis
        if len(values) >= 3:
            try:
                stats = self.stats_analyzer.calculate_cohort_statistics(values[:-1])
                is_anomaly, anomaly_type, z_score, p_value = self.stats_analyzer.is_anomaly(
                    values[-1], stats.mean, stats.std
                )

                if is_anomaly and anomaly_type == "HIGH":
                    deviation = ((values[-1] - stats.mean) / stats.mean) * 100 if stats.mean > 0 else 0

                    anomalies.append(AnomalyFlag(
                        type=AnomalyType.HIGH_CONSUMPTION,
                        severity=Severity.MEDIUM if abs(z_score) < 2.5 else Severity.HIGH,
                        description=f"{utility_type.capitalize()} consumption is {deviation:.1f}% above your typical usage (z-score: {z_score:.2f})",
                        affected_utility=utility_type,
                        value=values[-1],
                        threshold=stats.ci_upper,
                        deviation_percent=deviation
                    ))
            except ValueError:
                pass  # Not enough data points

        return anomalies

    def _check_efficiency(
        self,
        current_value: float,
        national_avg: float,
        neighbour_avg: Optional[float],
        utility_type: str,
        rate: float
    ) -> Optional[EfficiencyIssue]:
        """Check efficiency compared to national and neighbour averages."""
        if national_avg <= 0:
            return None

        deviation_percent = ((current_value - national_avg) / national_avg) * 100

        # Only flag if above average
        if deviation_percent <= 0:
            return None

        # Determine severity
        severity = Severity.LOW
        if deviation_percent >= DEVIATION_THRESHOLDS["high"]:
            severity = Severity.HIGH
        elif deviation_percent >= DEVIATION_THRESHOLDS["medium"]:
            severity = Severity.MEDIUM

        # Calculate potential savings if reduced to national average
        excess_consumption = current_value - national_avg
        monthly_savings = excess_consumption * rate

        return EfficiencyIssue(
            utility_type=utility_type,
            current_value=current_value,
            national_average=national_avg,
            neighbour_average=neighbour_avg,
            deviation_percent=round(deviation_percent, 1),
            severity=severity,
            potential_monthly_savings_sgd=round(monthly_savings, 2),
            potential_annual_savings_sgd=round(monthly_savings * 12, 2)
        )

    def _analyze_trend(
        self,
        trend: ConsumptionTrend,
        utility_type: str
    ) -> Optional[TrendWarning]:
        """Analyze consumption trend for warnings."""
        if not trend.monthly_data or len(trend.monthly_data) < 3:
            return None

        values = [d.value for d in trend.monthly_data if d.value is not None]
        if len(values) < 3:
            return None

        # Count increasing months
        increasing_months = 0
        total_change = 0
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increasing_months += 1
                total_change += ((values[i] - values[i-1]) / values[i-1]) * 100 if values[i-1] > 0 else 0

        # Check if trend is consistently increasing
        if increasing_months >= 3:
            avg_change = total_change / increasing_months if increasing_months > 0 else 0
            severity = Severity.LOW
            if avg_change >= 10:
                severity = Severity.HIGH
            elif avg_change >= 5:
                severity = Severity.MEDIUM

            return TrendWarning(
                utility_type=utility_type,
                trend_direction="increasing",
                months_affected=increasing_months,
                average_monthly_change_percent=round(avg_change, 1),
                description=f"{utility_type.capitalize()} usage has been increasing for the past {increasing_months} months with an average increase of {avg_change:.1f}% per month",
                severity=severity
            )

        # Also check for reported trend direction from bill
        if trend.trend_direction == "increasing":
            return TrendWarning(
                utility_type=utility_type,
                trend_direction="increasing",
                months_affected=len(values),
                average_monthly_change_percent=None,
                description=f"{utility_type.capitalize()} usage shows an increasing trend according to bill analysis",
                severity=Severity.MEDIUM
            )

        return None

    def _generate_recommendations(
        self,
        anomalies: List[AnomalyFlag],
        efficiency_issues: List[EfficiencyIssue],
        trend_warnings: List[TrendWarning]
    ) -> List[Recommendation]:
        """Generate personalized recommendations based on identified issues."""
        recommendations = []
        priority = 1

        # High severity anomalies get top priority
        high_anomalies = [a for a in anomalies if a.severity == Severity.HIGH]
        for anomaly in high_anomalies:
            if anomaly.affected_utility == "electricity":
                recommendations.append(Recommendation(
                    category=RecommendationCategory.MONITORING,
                    title="Investigate sudden spike",
                    description=f"Your electricity usage spiked significantly. Check for: (1) New appliances, (2) AC running longer hours, (3) Faulty equipment drawing excess power, (4) Meter reading errors.",
                    potential_savings_percent=15.0,
                    priority=priority
                ))
                priority += 1

        # Efficiency issues - recommend appliance upgrades
        for issue in efficiency_issues:
            if issue.utility_type == "electricity" and issue.deviation_percent >= 20:
                recommendations.append(Recommendation(
                    category=RecommendationCategory.APPLIANCE,
                    title="Upgrade to energy-efficient air conditioner",
                    description=f"Your electricity usage is {issue.deviation_percent:.0f}% above average. Upgrading to a 5-tick air conditioner could save up to 35% on cooling costs. Use your $300 Climate Voucher!",
                    potential_savings_percent=20.0,
                    priority=priority
                ))
                priority += 1

                recommendations.append(Recommendation(
                    category=RecommendationCategory.BEHAVIOR,
                    title="Optimize AC usage",
                    description="Set AC temperature to 25°C instead of lower temperatures. Each degree lower increases energy use by 3-5%. Use a fan alongside AC to feel cooler.",
                    potential_savings_percent=10.0,
                    priority=priority
                ))
                priority += 1

            if issue.utility_type == "electricity" and issue.deviation_percent >= 10:
                recommendations.append(Recommendation(
                    category=RecommendationCategory.APPLIANCE,
                    title="Switch to LED lighting",
                    description="Replace incandescent and CFL bulbs with LED lights. LEDs use 80% less energy and last much longer. Eligible for Climate Voucher!",
                    potential_savings_percent=5.0,
                    priority=priority
                ))
                priority += 1

            if issue.utility_type == "water" and issue.deviation_percent >= 15:
                recommendations.append(Recommendation(
                    category=RecommendationCategory.APPLIANCE,
                    title="Install water-efficient fixtures",
                    description=f"Your water usage is {issue.deviation_percent:.0f}% above average. Install 3-tick water taps and showerheads. Eligible for Climate Voucher!",
                    potential_savings_percent=15.0,
                    priority=priority
                ))
                priority += 1

        # Trend warnings
        for warning in trend_warnings:
            if warning.severity in [Severity.MEDIUM, Severity.HIGH]:
                recommendations.append(Recommendation(
                    category=RecommendationCategory.MONITORING,
                    title=f"Monitor {warning.utility_type} usage closely",
                    description=f"Your {warning.utility_type} usage has been increasing. Track daily usage to identify the cause. Consider a smart meter or energy monitoring device.",
                    potential_savings_percent=5.0,
                    priority=priority
                ))
                priority += 1

        # General recommendations if few issues found
        if len(recommendations) < 2:
            recommendations.append(Recommendation(
                category=RecommendationCategory.MAINTENANCE,
                title="Regular appliance maintenance",
                description="Clean AC filters monthly, defrost refrigerator regularly, and service appliances annually to maintain efficiency.",
                potential_savings_percent=5.0,
                priority=priority
            ))

        return recommendations[:5]  # Limit to top 5 recommendations

    def _calculate_health_score(
        self,
        anomalies: List[AnomalyFlag],
        efficiency_issues: List[EfficiencyIssue],
        trend_warnings: List[TrendWarning]
    ) -> float:
        """Calculate overall bill health score (0-100)."""
        score = 100.0

        # Deduct for anomalies
        for anomaly in anomalies:
            if anomaly.severity == Severity.HIGH:
                score -= 20
            elif anomaly.severity == Severity.MEDIUM:
                score -= 10
            else:
                score -= 5

        # Deduct for efficiency issues
        for issue in efficiency_issues:
            if issue.severity == Severity.HIGH:
                score -= 15
            elif issue.severity == Severity.MEDIUM:
                score -= 8
            else:
                score -= 3

        # Deduct for trend warnings
        for warning in trend_warnings:
            if warning.severity == Severity.HIGH:
                score -= 10
            elif warning.severity == Severity.MEDIUM:
                score -= 5
            else:
                score -= 2

        return max(0.0, min(100.0, score))

    def _score_to_grade(self, score: float) -> str:
        """Convert health score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_summary(
        self,
        anomalies: List[AnomalyFlag],
        efficiency_issues: List[EfficiencyIssue],
        trend_warnings: List[TrendWarning],
        grade: str
    ) -> str:
        """Generate a brief summary of the diagnosis."""
        parts = []

        if grade in ["A", "B"]:
            parts.append("Your energy consumption is within a healthy range.")
        elif grade == "C":
            parts.append("Your energy consumption has some areas for improvement.")
        else:
            parts.append("Your energy consumption needs attention.")

        # Summarize efficiency issues
        high_issues = [i for i in efficiency_issues if i.deviation_percent >= 20]
        if high_issues:
            utilities = [i.utility_type for i in high_issues]
            parts.append(f"Your {', '.join(utilities)} usage is significantly above average.")

        # Summarize anomalies
        if any(a.severity == Severity.HIGH for a in anomalies):
            parts.append("Unusual consumption patterns detected that need investigation.")

        # Summarize trends
        increasing = [w for w in trend_warnings if w.trend_direction == "increasing"]
        if increasing:
            utilities = [w.utility_type for w in increasing]
            parts.append(f"Your {', '.join(utilities)} usage has been trending upward.")

        # Add savings potential
        total_savings = sum(i.potential_monthly_savings_sgd for i in efficiency_issues)
        if total_savings > 0:
            parts.append(f"Potential monthly savings: ${total_savings:.2f}.")

        return " ".join(parts)
