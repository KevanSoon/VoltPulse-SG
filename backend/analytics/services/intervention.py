"""Intervention tracking service for before/after analysis.

Manages energy efficiency interventions and calculates their effectiveness
using paired t-tests and consumption comparisons.
"""

import uuid
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict
import numpy as np

from models.intervention import Intervention, InterventionType, HousingType
from .statistical import StatisticalAnalyzer
from .district import extract_postal_code, classify_housing_type


# Estimated Singapore electricity rate (SGD per kWh)
# Rates vary by provider and market conditions
ESTIMATED_RATE_PER_KWH = 0.30


class InterventionService:
    """Service for managing interventions and calculating effectiveness."""

    def __init__(self, vector_store=None, statistical_analyzer: StatisticalAnalyzer = None):
        """Initialize the service.

        Args:
            vector_store: VectorStore instance for data access
            statistical_analyzer: StatisticalAnalyzer for statistical calculations
        """
        self.vector_store = vector_store
        self.stats = statistical_analyzer or StatisticalAnalyzer()
        # In-memory storage for interventions (would use DB in production)
        self._interventions: Dict[str, Intervention] = {}

    async def create_intervention(
        self,
        account_number: str,
        intervention_type: str,
        intervention_date: date,
        postal_code: Optional[str] = None,
        housing_type: Optional[str] = None,
        description: Optional[str] = None,
        cost_sgd: Optional[float] = None,
    ) -> Intervention:
        """Create a new intervention record.

        Args:
            account_number: Electricity account number
            intervention_type: Type of intervention (from InterventionType enum)
            intervention_date: Date of the intervention
            postal_code: Optional postal code (will try to extract from records if not provided)
            housing_type: Optional housing type (will try to classify if not provided)
            description: Optional description of the intervention
            cost_sgd: Optional cost of the intervention in SGD

        Returns:
            Created Intervention object
        """
        # Generate unique ID
        intervention_id = f"int_{uuid.uuid4().hex[:12]}"

        # Parse intervention type
        try:
            int_type = InterventionType(intervention_type.lower())
        except ValueError:
            int_type = InterventionType.OTHER

        # Parse housing type
        if housing_type:
            try:
                h_type = HousingType(housing_type.lower())
            except ValueError:
                h_type = HousingType.UNKNOWN
        else:
            h_type = HousingType.UNKNOWN

        intervention = Intervention(
            id=intervention_id,
            account_number=account_number,
            postal_code=postal_code or "",
            housing_type=h_type,
            intervention_type=int_type,
            intervention_date=intervention_date,
            description=description,
            cost_sgd=cost_sgd,
            created_at=date.today(),
            updated_at=date.today(),
        )

        # Store intervention
        self._interventions[intervention_id] = intervention

        return intervention

    async def get_intervention(self, intervention_id: str) -> Optional[Intervention]:
        """Get an intervention by ID.

        Args:
            intervention_id: Unique intervention ID

        Returns:
            Intervention object or None if not found
        """
        return self._interventions.get(intervention_id)

    async def list_interventions(
        self,
        account_number: Optional[str] = None,
        intervention_type: Optional[str] = None,
        postal_district: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List interventions with optional filters.

        Args:
            account_number: Filter by account
            intervention_type: Filter by type
            postal_district: Filter by 2-digit postal district
            start_date: Filter by date range start
            end_date: Filter by date range end
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dict with interventions list and pagination info
        """
        filtered = list(self._interventions.values())

        # Apply filters
        if account_number:
            filtered = [i for i in filtered if i.account_number == account_number]

        if intervention_type:
            filtered = [i for i in filtered if i.intervention_type.value == intervention_type.lower()]

        if postal_district:
            filtered = [i for i in filtered if i.postal_code.startswith(postal_district)]

        if start_date:
            filtered = [i for i in filtered if i.intervention_date >= start_date]

        if end_date:
            filtered = [i for i in filtered if i.intervention_date <= end_date]

        # Sort by date descending
        filtered.sort(key=lambda x: x.intervention_date, reverse=True)

        # Paginate
        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        return {
            "interventions": paginated,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
        }

    async def analyze_intervention(
        self,
        account_number: str,
        intervention_date: date,
        intervention_type: str,
        consumption_records: List[Dict],
        months_before: int = 3,
        months_after: int = 3,
    ) -> Dict[str, Any]:
        """Perform before/after statistical analysis for an intervention.

        Uses paired t-test to determine if consumption change is significant.

        Args:
            account_number: Electricity account number
            intervention_date: Date of the intervention
            intervention_type: Type of intervention
            consumption_records: List of consumption records with billing periods
            months_before: Number of months to analyze before intervention
            months_after: Number of months to analyze after intervention

        Returns:
            Dict with analysis results including t-statistic, p-value, and savings
        """
        # Separate records into before and after periods
        before_records = []
        after_records = []

        for record in consumption_records:
            if record.get("account_number") != account_number:
                continue

            period_end = record.get("billing_period_end")
            if not period_end:
                continue

            # Convert to date if string
            if isinstance(period_end, str):
                period_end = datetime.fromisoformat(period_end).date()

            consumption = record.get("consumption_kwh", 0)
            if not consumption or consumption <= 0:
                continue

            if period_end < intervention_date:
                before_records.append({
                    "date": period_end,
                    "consumption_kwh": consumption,
                })
            else:
                after_records.append({
                    "date": period_end,
                    "consumption_kwh": consumption,
                })

        # Sort by date
        before_records.sort(key=lambda x: x["date"], reverse=True)
        after_records.sort(key=lambda x: x["date"])

        # Take the most recent 'months_before' and earliest 'months_after'
        before_values = [r["consumption_kwh"] for r in before_records[:months_before]]
        after_values = [r["consumption_kwh"] for r in after_records[:months_after]]

        # Build monthly data for visualization
        monthly_data = []
        for r in reversed(before_records[:months_before]):
            monthly_data.append({
                "month": r["date"].strftime("%Y-%m"),
                "consumption_kwh": r["consumption_kwh"],
                "is_after_intervention": False,
            })
        for r in after_records[:months_after]:
            monthly_data.append({
                "month": r["date"].strftime("%Y-%m"),
                "consumption_kwh": r["consumption_kwh"],
                "is_after_intervention": True,
            })

        # Calculate basic stats
        before_avg = np.mean(before_values) if before_values else 0
        before_std = np.std(before_values, ddof=1) if len(before_values) > 1 else 0
        after_avg = np.mean(after_values) if after_values else 0
        after_std = np.std(after_values, ddof=1) if len(after_values) > 1 else 0

        # Calculate change
        consumption_change = before_avg - after_avg  # Positive = savings
        consumption_change_percent = (consumption_change / before_avg * 100) if before_avg > 0 else 0

        # Perform paired t-test if we have enough data
        t_statistic = 0.0
        p_value = 1.0
        is_significant = False
        ci_lower = 0.0
        ci_upper = 0.0

        if len(before_values) >= 2 and len(after_values) >= 2:
            # For paired t-test, we need equal sample sizes
            min_len = min(len(before_values), len(after_values))
            before_paired = before_values[:min_len]
            after_paired = after_values[:min_len]

            try:
                result = self.stats.paired_t_test(before_paired, after_paired)
                t_statistic = result["t_statistic"]
                p_value = result["p_value"]
                is_significant = result["is_significant"]
                ci_lower = result["ci_lower"]
                ci_upper = result["ci_upper"]
            except Exception:
                pass

        # Calculate projections
        monthly_savings = consumption_change
        annual_savings_kwh = monthly_savings * 12
        annual_savings_sgd = annual_savings_kwh * ESTIMATED_RATE_PER_KWH

        return {
            "account_number": account_number,
            "intervention_type": intervention_type,
            "intervention_date": intervention_date.isoformat(),
            "before_period": {
                "start": before_records[-1]["date"].isoformat() if before_records else None,
                "end": before_records[0]["date"].isoformat() if before_records else None,
            },
            "before_avg_kwh": float(before_avg),
            "before_std_kwh": float(before_std),
            "before_data_points": len(before_values),
            "after_period": {
                "start": after_records[0]["date"].isoformat() if after_records else None,
                "end": after_records[-1]["date"].isoformat() if len(after_records) > 1 else after_records[0]["date"].isoformat() if after_records else None,
            },
            "after_avg_kwh": float(after_avg),
            "after_std_kwh": float(after_std),
            "after_data_points": len(after_values),
            "monthly_data": monthly_data,
            "consumption_change_kwh": float(consumption_change),
            "consumption_change_percent": float(consumption_change_percent),
            "t_statistic": float(t_statistic),
            "p_value": float(p_value),
            "is_significant": is_significant,
            "confidence_interval_95": {
                "lower": float(ci_lower),
                "upper": float(ci_upper),
            },
            "projected_annual_savings_kwh": float(annual_savings_kwh) if annual_savings_kwh > 0 else None,
            "projected_annual_savings_sgd": float(annual_savings_sgd) if annual_savings_sgd > 0 else None,
        }

    async def get_intervention_effectiveness(
        self,
        intervention_type: Optional[str] = None,
        housing_type: Optional[str] = None,
        min_sample_size: int = 5,
    ) -> Dict[str, Any]:
        """Get aggregate effectiveness statistics for interventions.

        Args:
            intervention_type: Filter by intervention type
            housing_type: Filter by housing type
            min_sample_size: Minimum number of interventions for statistics

        Returns:
            Dict with aggregate effectiveness statistics
        """
        # Filter interventions
        filtered = list(self._interventions.values())

        if intervention_type:
            filtered = [i for i in filtered if i.intervention_type.value == intervention_type.lower()]

        if housing_type:
            filtered = [i for i in filtered if i.housing_type.value == housing_type.lower()]

        # Filter to those with calculated savings
        with_savings = [i for i in filtered if i.consumption_delta_kwh is not None]

        if len(with_savings) < min_sample_size:
            return {
                "intervention_type": intervention_type,
                "housing_type": housing_type,
                "sample_size": len(with_savings),
                "message": f"Insufficient data. Need at least {min_sample_size} interventions with savings data.",
            }

        savings = [i.consumption_delta_kwh for i in with_savings]
        savings_pct = [i.consumption_delta_percent for i in with_savings if i.consumption_delta_percent is not None]

        arr = np.array(savings)
        mean_savings = float(np.mean(arr))
        std_savings = float(np.std(arr, ddof=1))
        sem = std_savings / np.sqrt(len(arr))

        # Count significant improvements (positive savings with some threshold)
        significant_count = sum(1 for s in savings if s > 10)  # > 10 kWh savings

        return {
            "intervention_type": intervention_type,
            "housing_type": housing_type,
            "sample_size": len(with_savings),
            "avg_savings_kwh": mean_savings,
            "avg_savings_percent": float(np.mean(savings_pct)) if savings_pct else 0,
            "median_savings_kwh": float(np.median(arr)),
            "std_savings_kwh": std_savings,
            "ci_lower": mean_savings - 1.96 * sem,
            "ci_upper": mean_savings + 1.96 * sem,
            "significant_improvements_count": significant_count,
            "significant_improvements_percent": (significant_count / len(with_savings)) * 100,
        }
