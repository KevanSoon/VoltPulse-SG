# Bill Diagnosis Service

[← Back to Documentation](../README.md)

## Table of Contents
- [Overview](#overview)
- [Diagnosis Pipeline](#diagnosis-pipeline)
- [Anomaly Detection](#anomaly-detection)
- [Efficiency Analysis](#efficiency-analysis)
- [Trend Warnings](#trend-warnings)
- [Recommendation Engine](#recommendation-engine)
- [Health Scoring](#health-scoring)
- [Implementation Details](#implementation-details)

---

## Overview

The **Bill Diagnosis Service** analyzes extracted utility bill data to identify consumption issues and provide personalized recommendations. It combines **statistical analysis**, **domain knowledge**, and **benchmarking** to generate actionable insights for Singapore households.

**Key Features:**
- **Anomaly Detection**: Identifies spikes and unusual consumption patterns using Z-score analysis
- **Efficiency Benchmarking**: Compares consumption against national and neighbor averages
- **Trend Analysis**: Detects increasing consumption patterns over time
- **Health Scoring**: Assigns 0-100 score with A-F grade
- **Personalized Recommendations**: Suggests specific actions to reduce consumption
- **Savings Estimation**: Calculates potential monthly/annual savings

**Implementation:** [`backend/services/bill_diagnosis.py`](../../backend/services/bill_diagnosis.py)

---

## Diagnosis Pipeline

### Complete Flow

```
Input: ElectricityBillExtraction (from OCR)
   ↓
┌─────────────────────────────────────────────────────────┐
│  Step 1: Anomaly Detection                              │
│  ├─ Method 1: Month-over-Month Spike (≥20% increase)   │
│  └─ Method 2: Statistical Outlier (Z-score ≥ 2.0)      │
└─────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: Efficiency Analysis                            │
│  ├─ Compare vs national average (400 kWh for 4-room)   │
│  ├─ Compare vs neighbour average (if available)        │
│  └─ Calculate potential savings                         │
└─────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: Trend Warnings                                 │
│  ├─ Detect increasing consumption (3+ months)          │
│  ├─ Calculate average monthly change                    │
│  └─ Assign severity (HIGH/MEDIUM/LOW)                   │
└─────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────┐
│  Step 4: Recommendation Generation                      │
│  ├─ Priority 1: Address HIGH severity issues           │
│  ├─ Priority 2: Suggest appliance upgrades             │
│  ├─ Priority 3: Behavior changes                       │
│  └─ Priority 4: Maintenance tips                        │
└─────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────┐
│  Step 5: Health Scoring                                 │
│  ├─ Start at 100 points                                │
│  ├─ Deduct for each issue (by severity)                │
│  └─ Assign grade: A (90+), B (80+), C (70+), D (60+)   │
└─────────────────────────────────────────────────────────┘
   ↓
Output: DiagnosisResult (anomalies, efficiency issues,
                        trends, recommendations, health score)
```

---

## Anomaly Detection

The service uses **two complementary methods** to detect consumption anomalies.

### Method 1: Month-over-Month Spike Detection

**Purpose:** Catch sudden consumption increases that may indicate problems.

**Algorithm:** [`backend/services/bill_diagnosis.py:190-235`](../../backend/services/bill_diagnosis.py#L190-L235)

```python
SPIKE_THRESHOLD_PERCENT = 20.0  # 20% increase triggers detection

def _detect_spike(current_value: float, previous_value: float) -> Optional[AnomalyFlag]:
    """Detect month-over-month consumption spikes."""
    if previous_value <= 0:
        return None

    change_percent = ((current_value - previous_value) / previous_value) * 100

    if change_percent >= SPIKE_THRESHOLD_PERCENT:
        # Classify severity
        if change_percent >= 40:
            severity = Severity.HIGH
        elif change_percent >= 30:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        return AnomalyFlag(
            type=AnomalyType.SPIKE,
            severity=severity,
            description=f"Electricity consumption spiked {change_percent:.1f}% compared to previous month",
            affected_utility="electricity",
            value=current_value,
            threshold=previous_value * (1 + SPIKE_THRESHOLD_PERCENT / 100),
            deviation_percent=change_percent
        )

    return None
```

**Severity Classification:**

| Change | Severity | Typical Causes |
|--------|----------|----------------|
| 20-29% | LOW | Seasonal changes, guests staying over |
| 30-39% | MEDIUM | New appliance, AC running more |
| 40%+ | HIGH | Faulty equipment, meter error, major lifestyle change |

**Example Detection:**

```
Month 1: 400 kWh
Month 2: 520 kWh

Change: (520 - 400) / 400 = 30% increase
Result: MEDIUM severity spike detected

Recommendation: "Investigate sudden spike. Check for:
(1) New appliances (2) AC running longer
(3) Faulty equipment (4) Meter reading errors"
```

---

### Method 2: Statistical Outlier Detection (Z-score)

**Purpose:** Identify consumption that deviates significantly from user's typical pattern.

**Algorithm:** [`backend/services/bill_diagnosis.py:237-258`](../../backend/services/bill_diagnosis.py#L237-L258)

```python
from scipy import stats
from analytics.services.statistical import StatisticalAnalyzer

def _detect_statistical_outlier(
    current_value: float,
    historical_values: List[float]
) -> Optional[AnomalyFlag]:
    """Detect outliers using Z-score (95% confidence interval)."""
    if len(historical_values) < 3:
        return None  # Need at least 3 data points

    stats_analyzer = StatisticalAnalyzer()
    cohort_stats = stats_analyzer.calculate_cohort_statistics(historical_values)

    # Check if current value is an outlier (Z-score ≥ 2.0)
    is_anomaly, anomaly_type, z_score, p_value = stats_analyzer.is_anomaly(
        current_value,
        cohort_stats.mean,
        cohort_stats.std
    )

    if is_anomaly and anomaly_type == "HIGH":
        deviation = ((current_value - cohort_stats.mean) / cohort_stats.mean) * 100

        return AnomalyFlag(
            type=AnomalyType.HIGH_CONSUMPTION,
            severity=Severity.HIGH if abs(z_score) >= 2.5 else Severity.MEDIUM,
            description=f"Electricity consumption is {deviation:.1f}% above your typical usage (z-score: {z_score:.2f})",
            affected_utility="electricity",
            value=current_value,
            threshold=cohort_stats.ci_upper,  # 95% confidence interval upper bound
            deviation_percent=deviation
        )

    return None
```

**Statistical Background:**

**Z-score formula:**
```
z = (x - μ) / σ

where:
  x = current consumption
  μ = mean of historical consumption
  σ = standard deviation of historical consumption
```

**Interpretation:**
- **|z| < 1.96**: Within 95% confidence interval (normal)
- **|z| ≥ 1.96**: Outside 95% CI (potential outlier)
- **|z| ≥ 2.5**: Strong outlier (HIGH severity)

**Example:**

```
Historical consumption: [380, 410, 395, 400, 390] kWh
Mean (μ): 395 kWh
Std Dev (σ): 10 kWh

Current month: 450 kWh
Z-score: (450 - 395) / 10 = 5.5

Interpretation: 5.5 standard deviations above mean
Result: HIGH severity outlier (z-score ≥ 2.5)
p-value: < 0.001 (highly unlikely by chance)

Recommendation: "Your consumption is unusually high.
This is 5.5 standard deviations above your typical usage.
Investigate immediately for faulty equipment."
```

---

### Why Two Methods?

**Spike Detection** catches sudden changes:
- Previous: 400 kWh → Current: 520 kWh (30% spike)
- ✅ Detected by Method 1

**Z-score** catches persistent high usage:
- Historical: [380, 390, 400, 395, 385]
- Current: 450 kWh (not a spike from previous month, but high overall)
- ✅ Detected by Method 2

**Both together** provide comprehensive anomaly detection.

---

## Efficiency Analysis

### National Average Comparison

**Algorithm:** [`backend/services/bill_diagnosis.py:261-299`](../../backend/services/bill_diagnosis.py#L261-L299)

```python
# National averages for Singapore households (kWh/month)
NATIONAL_AVERAGES = {
    "electricity": 400.0,  # 4-room HDB
    "gas": 50.0,
    "water": 15.0,  # cubic meters
}

# Electricity rate (SGD per kWh)
ELECTRICITY_RATE_SGD = 0.36

def _check_efficiency(
    current_value: float,
    national_avg: float,
    neighbour_avg: Optional[float],
    utility_type: str,
    rate: float
) -> Optional[EfficiencyIssue]:
    """Compare consumption against national and neighbour averages."""
    if national_avg is None or national_avg <= 0:
        return None

    deviation_percent = ((current_value - national_avg) / national_avg) * 100

    # Only flag if above average
    if deviation_percent <= 0:
        return None

    # Classify severity
    if deviation_percent >= 50:
        severity = Severity.HIGH      # 50%+ above average
    elif deviation_percent >= 25:
        severity = Severity.MEDIUM    # 25-50% above average
    else:
        severity = Severity.LOW       # 10-25% above average

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
```

**Severity Thresholds:**

| Deviation | Severity | Example (400 kWh baseline) |
|-----------|----------|----------------------------|
| 10-24% | LOW | 440-496 kWh |
| 25-49% | MEDIUM | 500-596 kWh |
| 50%+ | HIGH | 600+ kWh |

**Savings Calculation:**

```
Current consumption: 500 kWh
National average: 400 kWh
Excess: 500 - 400 = 100 kWh

Monthly savings if reduced to average:
  100 kWh × $0.36/kWh = $36/month

Annual savings:
  $36 × 12 = $432/year
```

---

### Neighbour Average Comparison

If available from bill's consumption trends, the service also compares against **neighbour average**:

```python
if neighbour_avg and current_value > neighbour_avg:
    neighbour_deviation = ((current_value - neighbour_avg) / neighbour_avg) * 100

    description += f"\nYou're also {neighbour_deviation:.1f}% above your neighbours' average of {neighbour_avg} kWh."
```

**Why both national and neighbour?**
- **National**: Standardized benchmark (4-room HDB)
- **Neighbour**: More relevant (same building, similar housing type)

---

## Trend Warnings

### Increasing Consumption Detection

**Algorithm:** [`backend/services/bill_diagnosis.py:301-351`](../../backend/services/bill_diagnosis.py#L301-L351)

```python
def _analyze_trend(
    trend: ConsumptionTrend,
    utility_type: str
) -> Optional[TrendWarning]:
    """Detect increasing consumption trends over time."""
    if not trend.monthly_data or len(trend.monthly_data) < 3:
        return None

    values = [d.value for d in trend.monthly_data if d.value is not None]
    if len(values) < 3:
        return None

    # Count consecutive increasing months
    increasing_months = 0
    total_change = 0

    for i in range(1, len(values)):
        if values[i] > values[i-1]:
            increasing_months += 1
            change_pct = ((values[i] - values[i-1]) / values[i-1]) * 100 if values[i-1] > 0 else 0
            total_change += change_pct

    # Trigger warning if 3+ months of increases
    if increasing_months >= 3:
        avg_change = total_change / increasing_months if increasing_months > 0 else 0

        # Classify severity by rate of increase
        if avg_change >= 10:
            severity = Severity.HIGH       # 10%+ per month
        elif avg_change >= 5:
            severity = Severity.MEDIUM     # 5-10% per month
        else:
            severity = Severity.LOW        # <5% per month

        return TrendWarning(
            utility_type=utility_type,
            trend_direction="increasing",
            months_affected=increasing_months,
            average_monthly_change_percent=round(avg_change, 1),
            description=f"{utility_type.capitalize()} usage has been increasing for the past {increasing_months} months with an average increase of {avg_change:.1f}% per month",
            severity=severity
        )

    return None
```

**Example Detection:**

```
Monthly consumption:
  Month 1: 400 kWh
  Month 2: 420 kWh (+5%)
  Month 3: 450 kWh (+7%)
  Month 4: 480 kWh (+7%)
  Month 5: 510 kWh (+6%)

Analysis:
  Increasing months: 4 consecutive
  Average change: (5% + 7% + 7% + 6%) / 4 = 6.25% per month
  Severity: MEDIUM (5-10% per month)

Result: TrendWarning(
  trend_direction="increasing",
  months_affected=4,
  average_monthly_change_percent=6.3,
  severity=MEDIUM
)

Recommendation: "Your electricity usage has been steadily increasing
for 4 months. Track daily usage to identify the cause.
Consider a smart meter or energy monitoring device."
```

---

## Recommendation Engine

### Recommendation Generation

**Algorithm:** [`backend/services/bill_diagnosis.py:353-439`](../../backend/services/bill_diagnosis.py#L353-L439)

```python
def _generate_recommendations(
    anomalies: List[AnomalyFlag],
    efficiency_issues: List[EfficiencyIssue],
    trend_warnings: List[TrendWarning]
) -> List[Recommendation]:
    """Generate personalized recommendations based on identified issues."""
    recommendations = []
    priority = 1

    # Priority 1: High severity anomalies
    high_anomalies = [a for a in anomalies if a.severity == Severity.HIGH]
    for anomaly in high_anomalies:
        if anomaly.affected_utility == "electricity":
            recommendations.append(Recommendation(
                category=RecommendationCategory.MONITORING,
                title="Investigate sudden spike",
                description="Your electricity usage spiked significantly. Check for: (1) New appliances, (2) AC running longer hours, (3) Faulty equipment drawing excess power, (4) Meter reading errors.",
                potential_savings_percent=15.0,
                priority=priority
            ))
            priority += 1

    # Priority 2: Efficiency issues → Appliance upgrades
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

        if issue.utility_type == "water" and issue.deviation_percent >= 15:
            recommendations.append(Recommendation(
                category=RecommendationCategory.APPLIANCE,
                title="Install water-efficient fixtures",
                description=f"Your water usage is {issue.deviation_percent:.0f}% above average. Install 3-tick water taps and showerheads. Eligible for Climate Voucher!",
                potential_savings_percent=15.0,
                priority=priority
            ))
            priority += 1

    # Priority 3: Trend warnings → Monitoring
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

    # Priority 4: General recommendations (if few issues)
    if len(recommendations) < 2:
        recommendations.append(Recommendation(
            category=RecommendationCategory.MAINTENANCE,
            title="Regular appliance maintenance",
            description="Clean AC filters monthly, defrost refrigerator regularly, and service appliances annually to maintain efficiency.",
            potential_savings_percent=5.0,
            priority=priority
        ))

    return recommendations[:5]  # Limit to top 5
```

### Recommendation Categories

```python
class RecommendationCategory(Enum):
    MONITORING = "monitoring"      # Track usage, identify patterns
    APPLIANCE = "appliance"        # Upgrade to efficient appliances
    BEHAVIOR = "behavior"          # Change consumption habits
    MAINTENANCE = "maintenance"    # Maintain existing appliances
```

**Priority System:**
1. **HIGH severity issues** get top priority
2. **Appliance upgrades** for efficiency issues ≥20% deviation
3. **Behavior changes** for moderate efficiency issues
4. **Monitoring** for trend warnings
5. **Maintenance** as general advice

---

## Health Scoring

### Scoring Algorithm

**Algorithm:** [`backend/services/bill_diagnosis.py:441-490`](../../backend/services/bill_diagnosis.py#L441-L490)

```python
def _calculate_health_score(
    anomalies: List[AnomalyFlag],
    efficiency_issues: List[EfficiencyIssue],
    trend_warnings: List[TrendWarning]
) -> float:
    """Calculate overall bill health score (0-100).

    Starts at 100, deducts points for each issue by severity.
    """
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
```

### Deduction Table

| Issue Type | HIGH | MEDIUM | LOW |
|------------|------|--------|-----|
| Anomaly | -20 | -10 | -5 |
| Efficiency Issue | -15 | -8 | -3 |
| Trend Warning | -10 | -5 | -2 |

### Grade Assignment

```python
def _score_to_grade(score: float) -> str:
    """Convert health score to letter grade."""
    if score >= 90:
        return "A"   # Excellent
    elif score >= 80:
        return "B"   # Good
    elif score >= 70:
        return "C"   # Fair
    elif score >= 60:
        return "D"   # Poor
    else:
        return "F"   # Critical

```

### Example Scoring

**Scenario 1: Healthy Consumption**
```
Issues:
  - 1 LOW efficiency issue (5% above average): -3 points

Score: 100 - 3 = 97
Grade: A
Summary: "Your energy consumption is within a healthy range."
```

**Scenario 2: Moderate Issues**
```
Issues:
  - 1 MEDIUM anomaly (30% spike): -10 points
  - 1 MEDIUM efficiency issue (30% above average): -8 points
  - 1 LOW trend warning (3 months increasing): -2 points

Score: 100 - 10 - 8 - 2 = 80
Grade: B
Summary: "Your energy consumption has some areas for improvement.
Your electricity usage spiked 30% compared to last month."
```

**Scenario 3: Critical Issues**
```
Issues:
  - 1 HIGH anomaly (50% spike): -20 points
  - 1 HIGH efficiency issue (60% above average): -15 points
  - 1 HIGH trend warning (10%/month increase): -10 points
  - 1 MEDIUM efficiency issue (water 30% above): -8 points

Score: 100 - 20 - 15 - 10 - 8 = 47
Grade: F
Summary: "Your energy consumption needs urgent attention.
Unusual consumption patterns detected. Your electricity usage
is significantly above average."
```

---

## Implementation Details

### Complete Diagnosis Method

```python
# From backend/services/bill_diagnosis.py lines 56-177
async def diagnose(
    self,
    extraction: ElectricityBillExtraction
) -> DiagnosisResult:
    """Perform comprehensive diagnosis on extracted bill data."""
    anomalies: List[AnomalyFlag] = []
    efficiency_issues: List[EfficiencyIssue] = []
    trend_warnings: List[TrendWarning] = []
    recommendations: List[Recommendation] = []
    utilities_analyzed: List[str] = []

    # Analyze electricity
    if extraction.consumption_kwh is not None:
        utilities_analyzed.append("electricity")
        elec_trend = self._find_trend(extraction.consumption_trends, "Electricity")

        # 1. Detect anomalies
        elec_anomalies = self._detect_anomalies(
            current_value=extraction.consumption_kwh,
            monthly_data=elec_trend.monthly_data if elec_trend else [],
            utility_type="electricity"
        )
        anomalies.extend(elec_anomalies)

        # 2. Check efficiency
        elec_efficiency = self._check_efficiency(
            current_value=extraction.consumption_kwh,
            national_avg=elec_trend.national_average if elec_trend else NATIONAL_AVERAGES["electricity"],
            neighbour_avg=elec_trend.neighbour_average if elec_trend else None,
            utility_type="electricity",
            rate=ELECTRICITY_RATE_SGD
        )
        if elec_efficiency:
            efficiency_issues.append(elec_efficiency)

        # 3. Analyze trends
        if elec_trend:
            elec_trend_warning = self._analyze_trend(elec_trend, "electricity")
            if elec_trend_warning:
                trend_warnings.append(elec_trend_warning)

    # Analyze gas (similar process)
    # Analyze water (similar process)

    # 4. Generate recommendations
    recommendations = self._generate_recommendations(
        anomalies, efficiency_issues, trend_warnings
    )

    # 5. Calculate health score
    health_score = self._calculate_health_score(
        anomalies, efficiency_issues, trend_warnings
    )
    health_grade = self._score_to_grade(health_score)

    # 6. Calculate total savings
    total_monthly_savings = sum(
        issue.potential_monthly_savings_sgd for issue in efficiency_issues
    )

    # 7. Generate summary
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
        total_potential_annual_savings_sgd=round(total_monthly_savings * 12, 2),
    )
```

---

## Cross-References

- [OCR Extraction](./ocr-extraction.md) - Input data from OpenAI Vision
- [Statistical Analysis](./statistical-analysis.md) - Z-score and cohort statistics
- [ROI Calculator](./roi-calculator.md) - Appliance upgrade calculations
- [Architecture Overview](../01-architecture/overview.md) - Integration with overall system

---

[← Back to Documentation](../README.md) | [Next: ROI Calculator →](./roi-calculator.md)
