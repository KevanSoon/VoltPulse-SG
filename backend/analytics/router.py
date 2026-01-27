"""FastAPI router for /analytics endpoints.

Provides Urban Planner analytics capabilities:
- District heatmap visualization
- Anomaly detection with statistical rigor (95% CI)
- Intervention tracking with before/after analysis
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import date, datetime

from .models import (
    DistrictConsumption,
    DistrictHeatmapResponse,
    DistrictDetailResponse,
    HeatmapDataPoint,
    AnomalyDetectionResponse,
    AnomalyRecord,
    CohortStatistics,
    AccountAnomalyResponse,
    InterventionCreateRequest,
    InterventionSummary,
    InterventionListResponse,
    InterventionAnalysisRequest,
    InterventionAnalysisResponse,
    InterventionEffectivenessResponse,
    AnalyticsSummary,
)
from .services.statistical import StatisticalAnalyzer
from .services.district import (
    DistrictAggregator,
    extract_postal_code,
    classify_housing_type,
    SG_POSTAL_DISTRICTS,
)
from .services.intervention import InterventionService


router = APIRouter(prefix="/analytics", tags=["Urban Planner Analytics"])

# Initialize services
stats_analyzer = StatisticalAnalyzer()
district_aggregator = DistrictAggregator(stats_analyzer)
intervention_service = InterventionService(statistical_analyzer=stats_analyzer)

# Global reference for vector_store (set from app.py)
_vector_store = None


def set_vector_store(vs):
    """Set the vector store reference for data access."""
    global _vector_store
    _vector_store = vs


async def get_consumption_records(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    form_type: str = "utility_bill"
) -> List[dict]:
    """Fetch consumption records from vector store.

    Args:
        start_date: Filter by billing period start
        end_date: Filter by billing period end
        form_type: Type of form to fetch

    Returns:
        List of consumption records
    """
    if not _vector_store:
        # Return mock data if no vector store
        return get_mock_consumption_data()

    try:
        # Fetch all utility bills from vector store
        results = await _vector_store.find_by_form_type(form_type, limit=1000)

        records = []
        for result in results:
            form_data = result.form_data or {}
            extraction_data = form_data.get("extraction_data", {})

            if extraction_data:
                record = {
                    "source_id": result.id,
                    "account_number": extraction_data.get("account_number"),
                    "premise_address": extraction_data.get("premise_address"),
                    "consumption_kwh": extraction_data.get("consumption_kwh"),
                    "total_amount": extraction_data.get("total_amount"),
                    "billing_period_start": extraction_data.get("billing_period_start"),
                    "billing_period_end": extraction_data.get("billing_period_end"),
                    "provider_name": extraction_data.get("provider_name"),
                }

                # Apply date filters
                if start_date and record.get("billing_period_start"):
                    period_start = record["billing_period_start"]
                    if isinstance(period_start, str):
                        period_start = datetime.fromisoformat(period_start).date()
                    if period_start < start_date:
                        continue

                if end_date and record.get("billing_period_end"):
                    period_end = record["billing_period_end"]
                    if isinstance(period_end, str):
                        period_end = datetime.fromisoformat(period_end).date()
                    if period_end > end_date:
                        continue

                if record.get("consumption_kwh"):
                    records.append(record)

        return records

    except Exception as e:
        print(f"[WARN] Failed to fetch consumption records: {e}")
        return get_mock_consumption_data()


def get_mock_consumption_data() -> List[dict]:
    """Generate mock consumption data for testing/demo.

    Returns realistic Singapore consumption patterns.
    """
    import random

    housing_types = [
        ("BLK 123 TOA PAYOH LORONG 1 #08-22 Singapore 310123", "hdb_4_room", 300, 450),
        ("BLK 456 ANG MO KIO AVE 3 #12-34 Singapore 560456", "hdb_4_room", 280, 420),
        ("BLK 789 BEDOK NORTH AVE 2 #05-12 Singapore 460789", "hdb_3_room", 200, 350),
        ("BLK 234 TAMPINES ST 21 #08-56 Singapore 520234", "hdb_5_room", 350, 550),
        ("BLK 567 JURONG WEST ST 42 #03-78 Singapore 640567", "hdb_3_room", 180, 320),
        ("BLK 890 WOODLANDS DR 14 #11-22 Singapore 730890", "hdb_4_room", 290, 440),
        ("BLK 111 YISHUN RING RD #06-33 Singapore 760111", "hdb_4_room", 270, 410),
        ("BLK 222 SENGKANG EAST WAY #09-44 Singapore 540222", "hdb_4_room", 310, 470),
        ("BLK 333 PUNGGOL FIELD #07-55 Singapore 820333", "hdb_5_room", 380, 580),
        ("123 ORCHARD ROAD #12-01 THE RESIDENCES Singapore 238867", "condo", 400, 650),
        ("45 NASSIM ROAD Singapore 258431", "landed", 800, 1500),
        ("78 HOLLAND ROAD THE CONDO Singapore 278618", "condo", 450, 700),
        ("BLK 444 BUKIT BATOK WEST AVE 6 #04-66 Singapore 650444", "hdb_3_room", 190, 340),
        ("BLK 555 CLEMENTI AVE 3 #10-77 Singapore 120555", "hdb_4_room", 285, 430),
        ("BLK 666 QUEENSTOWN RD #08-88 Singapore 030666", "hdb_5_room", 360, 540),
        # Add some anomalies
        ("BLK 999 BISHAN ST 22 #15-99 Singapore 570999", "hdb_4_room", 600, 800),  # High consumption anomaly
        ("BLK 888 HOUGANG AVE 10 #02-11 Singapore 530888", "hdb_4_room", 100, 150),  # Low consumption anomaly
    ]

    records = []
    base_date = date(2024, 1, 1)

    for i, (address, h_type, min_kwh, max_kwh) in enumerate(housing_types):
        account_num = f"{1000000000 + i}"

        # Generate 6 months of data
        for month in range(6):
            month_date = date(2024, 1 + month, 1)
            consumption = random.uniform(min_kwh, max_kwh)
            billing_days = 30

            records.append({
                "source_id": f"mock_{account_num}_{month}",
                "account_number": account_num,
                "premise_address": address,
                "consumption_kwh": round(consumption, 1),
                "total_amount": round(consumption * 0.30, 2),
                "billing_period_start": month_date.isoformat(),
                "billing_period_end": date(2024, 1 + month, billing_days).isoformat(),
                "provider_name": "SP Services",
            })

    return records


# ============================================================================
# Dashboard Summary Endpoint
# ============================================================================

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary():
    """
    Get summary statistics for the analytics dashboard.

    Returns key metrics including total households, consumption,
    anomalies detected, and active interventions.
    """
    records = await get_consumption_records()

    if not records:
        return AnalyticsSummary(
            total_households=0,
            total_consumption_kwh=0,
            average_consumption_kwh=0,
            anomalies_detected=0,
            anomaly_rate_percent=0,
            active_interventions=0,
            total_savings_kwh=0,
            generated_at=datetime.now().isoformat(),
        )

    # Calculate unique households
    unique_accounts = set(r.get("account_number") for r in records if r.get("account_number"))
    total_consumption = sum(r.get("consumption_kwh", 0) for r in records)
    avg_consumption = total_consumption / len(records) if records else 0

    # Calculate anomalies
    cohort_data = await district_aggregator.aggregate_by_housing_type(records)
    anomaly_count = 0

    for record in records:
        address = record.get("premise_address", "")
        housing_type = classify_housing_type(address).value
        consumption = record.get("consumption_kwh", 0)

        if housing_type in cohort_data and consumption:
            stats = cohort_data[housing_type]
            is_anomaly, _, _, _ = stats_analyzer.is_anomaly(
                consumption, stats["mean_kwh"], stats["std_dev_kwh"]
            )
            if is_anomaly:
                anomaly_count += 1

    # Get interventions
    interventions = await intervention_service.list_interventions()
    total_savings = sum(
        i.consumption_delta_kwh or 0
        for i in interventions.get("interventions", [])
        if i.consumption_delta_kwh and i.consumption_delta_kwh < 0
    )

    return AnalyticsSummary(
        total_households=len(unique_accounts),
        total_consumption_kwh=round(total_consumption, 1),
        average_consumption_kwh=round(avg_consumption, 1),
        anomalies_detected=anomaly_count,
        anomaly_rate_percent=round((anomaly_count / len(records)) * 100, 1) if records else 0,
        active_interventions=interventions.get("total_count", 0),
        total_savings_kwh=round(abs(total_savings), 1),
        generated_at=datetime.now().isoformat(),
    )


# ============================================================================
# District Heatmap Endpoints
# ============================================================================

@router.get("/districts/heatmap", response_model=DistrictHeatmapResponse)
async def get_district_heatmap(
    start_date: Optional[date] = Query(None, description="Filter by billing period start"),
    end_date: Optional[date] = Query(None, description="Filter by billing period end"),
):
    """
    Get aggregated consumption data by postal district for heatmap visualization.

    Returns consumption intensity data suitable for rendering on a Singapore map.
    Districts are based on the first 2 digits of Singapore 6-digit postal codes.
    """
    records = await get_consumption_records(start_date, end_date)

    if not records:
        return DistrictHeatmapResponse(
            districts=[],
            heatmap_points=[],
            total_households=0,
            total_consumption_kwh=0,
            average_consumption_kwh=0,
            generated_at=datetime.now().isoformat(),
        )

    # Aggregate by district
    district_data = await district_aggregator.aggregate_by_district(records)

    # Generate heatmap points
    heatmap_points = await district_aggregator.generate_heatmap_data(district_data)

    # Build district consumption list
    districts = [
        DistrictConsumption(
            postal_district=d["postal_district"],
            district_name=d.get("district_name"),
            total_consumption_kwh=d["total_consumption_kwh"],
            average_consumption_kwh=d["average_consumption_kwh"],
            median_consumption_kwh=d.get("median_consumption_kwh"),
            household_count=d["household_count"],
        )
        for d in district_data.values()
    ]

    # Sort by average consumption descending
    districts.sort(key=lambda x: x.average_consumption_kwh, reverse=True)

    total_households = sum(d.household_count for d in districts)
    total_consumption = sum(d.total_consumption_kwh for d in districts)

    return DistrictHeatmapResponse(
        districts=districts,
        heatmap_points=[
            HeatmapDataPoint(
                postal_district=p["postal_district"],
                latitude=p["latitude"],
                longitude=p["longitude"],
                consumption_kwh=p["consumption_kwh"],
                intensity=p["intensity"],
                household_count=p["household_count"],
            )
            for p in heatmap_points
        ],
        total_households=total_households,
        total_consumption_kwh=round(total_consumption, 1),
        average_consumption_kwh=round(total_consumption / total_households, 1) if total_households else 0,
        generated_at=datetime.now().isoformat(),
    )


@router.get("/districts/{district_code}", response_model=DistrictDetailResponse)
async def get_district_details(
    district_code: str,
    include_records: bool = Query(False, description="Include individual records"),
):
    """
    Get detailed consumption statistics for a specific postal district.

    Args:
        district_code: 2-digit postal district code (01-83)
        include_records: Whether to include individual consumption records
    """
    records = await get_consumption_records()
    district_data = await district_aggregator.aggregate_by_district(records)

    if district_code not in district_data:
        raise HTTPException(
            status_code=404,
            detail=f"District {district_code} not found or has no data"
        )

    data = district_data[district_code]

    return DistrictDetailResponse(
        postal_district=district_code,
        district_name=data.get("district_name", SG_POSTAL_DISTRICTS.get(district_code, {}).get("name", "Unknown")),
        statistics=DistrictConsumption(
            postal_district=district_code,
            district_name=data.get("district_name"),
            total_consumption_kwh=data["total_consumption_kwh"],
            average_consumption_kwh=data["average_consumption_kwh"],
            median_consumption_kwh=data.get("median_consumption_kwh"),
            household_count=data["household_count"],
        ),
        records=data.get("records") if include_records else None,
    )


# ============================================================================
# Anomaly Detection Endpoints
# ============================================================================

@router.get("/anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    housing_type: Optional[str] = Query(None, description="Filter by housing type"),
    confidence_level: float = Query(0.95, ge=0.90, le=0.99, description="Confidence level"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Detect consumption anomalies using statistical confidence intervals.

    Groups data by housing type cohort and flags outliers that fall outside
    the specified confidence interval (default: 95% = 1.96 standard deviations).

    Returns cohort statistics (mean, std, CI) and flagged anomalies with z-scores and p-values.
    """
    records = await get_consumption_records(start_date, end_date)

    if not records:
        return AnomalyDetectionResponse(
            cohort_statistics=[],
            anomalies=[],
            total_records_analyzed=0,
            anomaly_count=0,
            anomaly_rate_percent=0,
            methodology=f"{int(confidence_level * 100)}% Confidence Interval",
        )

    # Get z-critical for the confidence level
    z_critical = stats_analyzer.get_z_critical_for_confidence(confidence_level)

    # Aggregate by housing type
    cohort_data = await district_aggregator.aggregate_by_housing_type(records)

    # Build cohort statistics
    cohort_stats = []
    for h_type, stats in cohort_data.items():
        cohort_stats.append(CohortStatistics(
            housing_type=h_type,
            sample_size=stats["sample_size"],
            mean_kwh=round(stats["mean_kwh"], 1),
            std_dev_kwh=round(stats["std_dev_kwh"], 1),
            median_kwh=round(stats["median_kwh"], 1),
            min_kwh=round(stats["min_kwh"], 1),
            max_kwh=round(stats["max_kwh"], 1),
            ci_lower=round(stats["ci_lower"], 1),
            ci_upper=round(stats["ci_upper"], 1),
            standard_error=round(stats["standard_error"], 2),
        ))

    # Detect anomalies
    anomalies = []
    for record in records:
        address = record.get("premise_address", "")
        h_type = classify_housing_type(address).value
        consumption = record.get("consumption_kwh", 0)

        # Filter by housing type if specified
        if housing_type and h_type != housing_type.lower():
            continue

        if h_type not in cohort_data or not consumption:
            continue

        stats = cohort_data[h_type]
        is_anomaly, anomaly_type, z_score, p_value = stats_analyzer.is_anomaly(
            consumption, stats["mean_kwh"], stats["std_dev_kwh"], z_critical
        )

        if is_anomaly:
            postal_code = extract_postal_code(address)
            deviation = consumption - stats["mean_kwh"]
            deviation_pct = (deviation / stats["mean_kwh"]) * 100 if stats["mean_kwh"] > 0 else 0

            anomalies.append(AnomalyRecord(
                account_number=record.get("account_number", "unknown"),
                postal_code=postal_code,
                housing_type=h_type,
                consumption_kwh=round(consumption, 1),
                billing_period=record.get("billing_period_end"),
                cohort_mean=round(stats["mean_kwh"], 1),
                cohort_std=round(stats["std_dev_kwh"], 1),
                z_score=round(z_score, 2),
                p_value=round(p_value, 4),
                anomaly_type=anomaly_type,
                confidence_level=confidence_level,
                deviation_kwh=round(deviation, 1),
                deviation_percent=round(deviation_pct, 1),
            ))

    # Sort by absolute z-score descending
    anomalies.sort(key=lambda x: abs(x.z_score), reverse=True)

    return AnomalyDetectionResponse(
        cohort_statistics=cohort_stats,
        anomalies=anomalies,
        total_records_analyzed=len(records),
        anomaly_count=len(anomalies),
        anomaly_rate_percent=round((len(anomalies) / len(records)) * 100, 1) if records else 0,
        analysis_period=f"{start_date} to {end_date}" if start_date or end_date else "All available data",
        methodology=f"{int(confidence_level * 100)}% Confidence Interval (z-score > {z_critical:.2f})",
    )


@router.get("/anomalies/cohorts", response_model=List[CohortStatistics])
async def get_cohort_statistics(
    period_months: int = Query(6, ge=1, le=24, description="Analysis period in months"),
):
    """
    Get statistical summary for each housing type cohort.

    Returns mean, standard deviation, and 95% confidence intervals
    for consumption by housing type (HDB types, condo, landed, commercial).
    """
    records = await get_consumption_records()
    cohort_data = await district_aggregator.aggregate_by_housing_type(records)

    cohort_stats = []
    for h_type, stats in cohort_data.items():
        cohort_stats.append(CohortStatistics(
            housing_type=h_type,
            sample_size=stats["sample_size"],
            mean_kwh=round(stats["mean_kwh"], 1),
            std_dev_kwh=round(stats["std_dev_kwh"], 1),
            median_kwh=round(stats["median_kwh"], 1),
            min_kwh=round(stats["min_kwh"], 1),
            max_kwh=round(stats["max_kwh"], 1),
            ci_lower=round(stats["ci_lower"], 1),
            ci_upper=round(stats["ci_upper"], 1),
            standard_error=round(stats["standard_error"], 2),
        ))

    # Sort by sample size descending
    cohort_stats.sort(key=lambda x: x.sample_size, reverse=True)

    return cohort_stats


@router.get("/anomalies/by-account/{account_number}", response_model=AccountAnomalyResponse)
async def check_account_anomaly(
    account_number: str,
    housing_type: Optional[str] = Query(None, description="Override housing type classification"),
):
    """
    Check if a specific account's consumption is anomalous.

    Compares the account's consumption against its housing type cohort
    and returns statistical significance measures.
    """
    records = await get_consumption_records()

    # Find the account's records
    account_records = [r for r in records if r.get("account_number") == account_number]

    if not account_records:
        raise HTTPException(status_code=404, detail=f"Account {account_number} not found")

    # Get latest record
    latest = max(account_records, key=lambda x: x.get("billing_period_end", ""))
    consumption = latest.get("consumption_kwh", 0)
    address = latest.get("premise_address", "")

    # Determine housing type
    if housing_type:
        h_type = housing_type.lower()
    else:
        h_type = classify_housing_type(address).value

    # Get cohort statistics
    cohort_data = await district_aggregator.aggregate_by_housing_type(records)

    if h_type not in cohort_data:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient data for housing type: {h_type}"
        )

    stats = cohort_data[h_type]
    is_anomaly, anomaly_type, z_score, p_value = stats_analyzer.is_anomaly(
        consumption, stats["mean_kwh"], stats["std_dev_kwh"]
    )

    recommendation = None
    if is_anomaly:
        if anomaly_type == "HIGH":
            recommendation = "High consumption detected. Consider energy audit and efficiency interventions."
        else:
            recommendation = "Unusually low consumption. Verify meter accuracy and occupancy."

    return AccountAnomalyResponse(
        account_number=account_number,
        is_anomaly=is_anomaly,
        housing_type=h_type,
        consumption_kwh=round(consumption, 1),
        cohort_statistics=CohortStatistics(
            housing_type=h_type,
            sample_size=stats["sample_size"],
            mean_kwh=round(stats["mean_kwh"], 1),
            std_dev_kwh=round(stats["std_dev_kwh"], 1),
            median_kwh=round(stats["median_kwh"], 1),
            min_kwh=round(stats["min_kwh"], 1),
            max_kwh=round(stats["max_kwh"], 1),
            ci_lower=round(stats["ci_lower"], 1),
            ci_upper=round(stats["ci_upper"], 1),
            standard_error=round(stats["standard_error"], 2),
        ),
        z_score=round(z_score, 2),
        p_value=round(p_value, 4),
        anomaly_type=anomaly_type if is_anomaly else None,
        recommendation=recommendation,
    )


# ============================================================================
# Intervention Tracking Endpoints
# ============================================================================

@router.post("/interventions", response_model=InterventionSummary)
async def create_intervention(request: InterventionCreateRequest):
    """
    Record a new energy efficiency intervention.

    Interventions include:
    - cool_paint: Cool roof/wall paint
    - led_retrofit: LED lighting upgrade
    - solar_panel: Solar PV installation
    - aircon_upgrade: Air conditioning upgrade
    - insulation: Thermal insulation
    - smart_meter: Smart meter/monitoring system
    """
    intervention = await intervention_service.create_intervention(
        account_number=request.account_number,
        intervention_type=request.intervention_type,
        intervention_date=request.intervention_date,
        postal_code=request.postal_code,
        housing_type=request.housing_type,
        description=request.description,
        cost_sgd=request.cost_sgd,
    )

    return InterventionSummary(
        intervention_id=intervention.id,
        account_number=intervention.account_number,
        intervention_type=intervention.intervention_type.value,
        intervention_date=intervention.intervention_date.isoformat(),
        housing_type=intervention.housing_type.value if intervention.housing_type else None,
        pre_consumption_kwh=intervention.pre_intervention_kwh_avg,
        post_consumption_kwh=intervention.post_intervention_kwh_avg,
        savings_kwh=intervention.consumption_delta_kwh,
        savings_percent=intervention.consumption_delta_percent,
    )


@router.get("/interventions", response_model=InterventionListResponse)
async def list_interventions(
    account_number: Optional[str] = None,
    intervention_type: Optional[str] = None,
    postal_district: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List recorded interventions with optional filters.
    """
    result = await intervention_service.list_interventions(
        account_number=account_number,
        intervention_type=intervention_type,
        postal_district=postal_district,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    return InterventionListResponse(
        interventions=[
            InterventionSummary(
                intervention_id=i.id,
                account_number=i.account_number,
                intervention_type=i.intervention_type.value,
                intervention_date=i.intervention_date.isoformat(),
                housing_type=i.housing_type.value if i.housing_type else None,
                pre_consumption_kwh=i.pre_intervention_kwh_avg,
                post_consumption_kwh=i.post_intervention_kwh_avg,
                savings_kwh=i.consumption_delta_kwh,
                savings_percent=i.consumption_delta_percent,
            )
            for i in result.get("interventions", [])
        ],
        total_count=result.get("total_count", 0),
        page=result.get("page", 1),
        page_size=result.get("page_size", 20),
    )


@router.post("/interventions/analyze", response_model=InterventionAnalysisResponse)
async def analyze_intervention(request: InterventionAnalysisRequest):
    """
    Perform before/after analysis for an intervention.

    Uses paired t-test to determine if the consumption change
    is statistically significant. Calculates:
    - Mean consumption before and after
    - Consumption change (kWh and %)
    - T-statistic and p-value
    - 95% confidence interval for the change
    - Projected annual savings
    """
    records = await get_consumption_records()

    result = await intervention_service.analyze_intervention(
        account_number=request.account_number,
        intervention_date=request.intervention_date,
        intervention_type=request.intervention_type,
        consumption_records=records,
        months_before=request.months_before,
        months_after=request.months_after,
    )

    return InterventionAnalysisResponse(
        account_number=result["account_number"],
        intervention_type=result["intervention_type"],
        intervention_date=result["intervention_date"],
        before_period=result["before_period"],
        before_avg_kwh=result["before_avg_kwh"],
        before_std_kwh=result["before_std_kwh"],
        before_data_points=result["before_data_points"],
        after_period=result["after_period"],
        after_avg_kwh=result["after_avg_kwh"],
        after_std_kwh=result["after_std_kwh"],
        after_data_points=result["after_data_points"],
        monthly_data=result["monthly_data"],
        consumption_change_kwh=result["consumption_change_kwh"],
        consumption_change_percent=result["consumption_change_percent"],
        t_statistic=result["t_statistic"],
        p_value=result["p_value"],
        is_significant=result["is_significant"],
        confidence_interval_95=result["confidence_interval_95"],
        projected_annual_savings_kwh=result.get("projected_annual_savings_kwh"),
        projected_annual_savings_sgd=result.get("projected_annual_savings_sgd"),
    )


@router.get("/interventions/effectiveness", response_model=InterventionEffectivenessResponse)
async def get_intervention_effectiveness(
    intervention_type: Optional[str] = None,
    housing_type: Optional[str] = None,
    min_sample_size: int = Query(5, ge=3, description="Minimum interventions for aggregate stats"),
):
    """
    Get aggregate effectiveness statistics for interventions.

    Returns average savings by intervention type across all recorded
    interventions, with statistical confidence measures.
    """
    result = await intervention_service.get_intervention_effectiveness(
        intervention_type=intervention_type,
        housing_type=housing_type,
        min_sample_size=min_sample_size,
    )

    if "message" in result:
        # Not enough data
        return InterventionEffectivenessResponse(
            intervention_type=intervention_type,
            housing_type=housing_type,
            sample_size=result.get("sample_size", 0),
            avg_savings_kwh=0,
            avg_savings_percent=0,
            median_savings_kwh=0,
            std_savings_kwh=0,
            ci_lower=0,
            ci_upper=0,
            significant_improvements_count=0,
            significant_improvements_percent=0,
        )

    return InterventionEffectivenessResponse(
        intervention_type=result.get("intervention_type"),
        housing_type=result.get("housing_type"),
        sample_size=result["sample_size"],
        avg_savings_kwh=round(result["avg_savings_kwh"], 1),
        avg_savings_percent=round(result["avg_savings_percent"], 1),
        median_savings_kwh=round(result["median_savings_kwh"], 1),
        std_savings_kwh=round(result["std_savings_kwh"], 1),
        ci_lower=round(result["ci_lower"], 1),
        ci_upper=round(result["ci_upper"], 1),
        significant_improvements_count=result["significant_improvements_count"],
        significant_improvements_percent=round(result["significant_improvements_percent"], 1),
    )


@router.get("/interventions/{intervention_id}")
async def get_intervention_details(intervention_id: str):
    """
    Get detailed information about a specific intervention including
    before/after analysis if sufficient data is available.
    """
    intervention = await intervention_service.get_intervention(intervention_id)

    if not intervention:
        raise HTTPException(status_code=404, detail=f"Intervention {intervention_id} not found")

    return {
        "intervention": InterventionSummary(
            intervention_id=intervention.id,
            account_number=intervention.account_number,
            intervention_type=intervention.intervention_type.value,
            intervention_date=intervention.intervention_date.isoformat(),
            housing_type=intervention.housing_type.value if intervention.housing_type else None,
            pre_consumption_kwh=intervention.pre_intervention_kwh_avg,
            post_consumption_kwh=intervention.post_intervention_kwh_avg,
            savings_kwh=intervention.consumption_delta_kwh,
            savings_percent=intervention.consumption_delta_percent,
        ),
        "description": intervention.description,
        "cost_sgd": intervention.cost_sgd,
        "created_at": intervention.created_at.isoformat() if intervention.created_at else None,
    }
