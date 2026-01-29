"""ROI Calculator service for appliance upgrade decisions.

Calculates return on investment for energy-efficient appliance upgrades,
factoring in Climate Voucher benefits and projected energy savings.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from models.diagnosis import DiagnosisResult, EfficiencyIssue


class ProductType(str, Enum):
    """Supported product types for ROI calculation."""
    AIR_CONDITIONERS = "air_conditioners"
    REFRIGERATORS = "refrigerators"
    WASHING_MACHINES = "washing_machines"
    LED_LIGHTS = "led_lights"
    WATER_CLOSETS = "water_closets"
    DC_FANS = "dc_fans"


class ROIResult(BaseModel):
    """Result of ROI calculation for an appliance upgrade."""

    product_type: str = Field(..., description="Type of appliance")
    product_display_name: str = Field(..., description="Human-readable product name")

    # Rating info
    current_rating: int = Field(..., description="Current appliance tick rating")
    new_rating: int = Field(..., description="New appliance tick rating")
    tick_improvement: int = Field(..., description="Number of ticks improved")

    # Cost breakdown
    product_price: float = Field(..., description="Price of new appliance in SGD")
    voucher_amount: float = Field(..., description="Climate Voucher value applied")
    net_cost: float = Field(..., description="Net cost after voucher (SGD)")

    # Savings projections
    annual_energy_savings_kwh: float = Field(..., description="Estimated annual kWh savings")
    annual_savings_sgd: float = Field(..., description="Estimated annual savings in SGD")
    monthly_savings_sgd: float = Field(..., description="Estimated monthly savings in SGD")

    # ROI metrics
    payback_period_months: int = Field(..., description="Months to recover investment")
    payback_period_years: float = Field(..., description="Years to recover investment")
    net_benefit_5_years: float = Field(..., description="Net benefit over 5 years")
    net_benefit_10_years: float = Field(..., description="Net benefit over 10 years")
    roi_percent_annual: float = Field(..., description="Annual ROI percentage")

    # Additional info
    is_voucher_eligible: bool = Field(..., description="Whether product meets voucher requirements")
    minimum_rating_for_voucher: int = Field(..., description="Minimum tick rating for voucher")
    notes: List[str] = Field(default_factory=list, description="Additional notes and tips")


class UpgradeRecommendation(BaseModel):
    """Recommended appliance upgrade based on diagnosis."""

    product_type: str
    product_display_name: str
    reason: str
    estimated_annual_savings: float
    priority: int
    roi_if_upgraded: Optional[ROIResult] = None


# Energy savings data based on Singapore's NEA energy label information
# Values are approximate annual consumption (kWh) by tick rating
ENERGY_CONSUMPTION_DATA = {
    "air_conditioners": {
        "name": "Air-conditioner",
        "min_voucher_tick": 3,
        "max_ticks": 5,
        # Annual kWh consumption by tick rating (for typical 9000 BTU unit, 8hrs/day)
        "consumption_by_tick": {
            0: 1400,  # No rating / old unit
            1: 1200,
            2: 1050,
            3: 920,
            4: 800,
            5: 700,  # 5-tick uses ~35% less than 1-tick
        },
        "typical_price_range": (599, 2500),
    },
    "refrigerators": {
        "name": "Refrigerator",
        "min_voucher_tick": 3,
        "max_ticks": 4,
        # Annual kWh consumption by tick rating (typical 300-400L fridge)
        "consumption_by_tick": {
            1: 500,
            2: 420,
            3: 350,
            4: 290,  # 4-tick saves ~$100/year vs 1-tick
        },
        "typical_price_range": (399, 2000),
    },
    "washing_machines": {
        "name": "Washing Machine",
        "min_voucher_tick": 4,
        "max_ticks": 4,
        # Annual kWh consumption (assuming 4 washes/week)
        "consumption_by_tick": {
            1: 200,
            2: 165,
            3: 135,
            4: 110,
        },
        "typical_price_range": (299, 1500),
    },
    "led_lights": {
        "name": "LED Light",
        "min_voucher_tick": 1,  # Just needs to be LED
        "max_ticks": 1,
        # Annual kWh consumption (per bulb, 5hrs/day vs incandescent)
        "consumption_by_tick": {
            0: 73,  # 40W incandescent
            1: 15,  # 9W LED equivalent
        },
        "typical_price_range": (5, 30),
    },
    "dc_fans": {
        "name": "DC Fan",
        "min_voucher_tick": 1,
        "max_ticks": 1,
        # Annual kWh consumption (8hrs/day)
        "consumption_by_tick": {
            0: 175,  # AC motor fan (60W)
            1: 70,   # DC motor fan (25W)
        },
        "typical_price_range": (80, 300),
    },
}

# Singapore electricity rate
ELECTRICITY_RATE_SGD = 0.36

# Climate Voucher value
CLIMATE_VOUCHER_VALUE = 300.0


class ROICalculator:
    """Calculator for appliance upgrade ROI with Climate Voucher integration."""

    def __init__(
        self,
        electricity_rate: float = ELECTRICITY_RATE_SGD,
        voucher_value: float = CLIMATE_VOUCHER_VALUE
    ):
        self.electricity_rate = electricity_rate
        self.voucher_value = voucher_value

    def calculate(
        self,
        product_type: str,
        current_rating: int,
        new_rating: int,
        product_price: float,
        apply_voucher: bool = True,
        custom_voucher_amount: Optional[float] = None
    ) -> ROIResult:
        """Calculate ROI for an appliance upgrade.

        Args:
            product_type: Type of appliance (e.g., "air_conditioners", "refrigerators")
            current_rating: Current appliance tick rating (0 for unknown/old)
            new_rating: New appliance tick rating
            product_price: Price of new appliance in SGD
            apply_voucher: Whether to apply Climate Voucher
            custom_voucher_amount: Custom voucher amount (if different from default)

        Returns:
            ROIResult with comprehensive ROI analysis
        """
        # Normalize product type
        normalized_type = self._normalize_product_type(product_type)

        if normalized_type not in ENERGY_CONSUMPTION_DATA:
            raise ValueError(f"Unknown product type: {product_type}")

        product_data = ENERGY_CONSUMPTION_DATA[normalized_type]
        consumption_by_tick = product_data["consumption_by_tick"]

        # Validate ratings
        max_ticks = product_data["max_ticks"]
        min_voucher_tick = product_data["min_voucher_tick"]

        if new_rating > max_ticks:
            new_rating = max_ticks
        if current_rating not in consumption_by_tick:
            current_rating = min(consumption_by_tick.keys())

        # Calculate energy savings
        current_consumption = consumption_by_tick.get(current_rating, consumption_by_tick[min(consumption_by_tick.keys())])
        new_consumption = consumption_by_tick.get(new_rating, consumption_by_tick[max(consumption_by_tick.keys())])

        annual_kwh_savings = max(0, current_consumption - new_consumption)
        annual_savings_sgd = annual_kwh_savings * self.electricity_rate
        monthly_savings_sgd = annual_savings_sgd / 12

        # Determine voucher eligibility
        is_voucher_eligible = new_rating >= min_voucher_tick

        # Calculate net cost
        voucher_amount = 0.0
        if apply_voucher and is_voucher_eligible:
            voucher_amount = custom_voucher_amount if custom_voucher_amount else self.voucher_value
            voucher_amount = min(voucher_amount, product_price)  # Can't exceed product price

        net_cost = product_price - voucher_amount

        # Calculate payback period
        if annual_savings_sgd > 0:
            payback_months = int((net_cost / annual_savings_sgd) * 12)
            payback_years = net_cost / annual_savings_sgd
        else:
            payback_months = 999  # No savings
            payback_years = 999.0

        # Calculate long-term benefits
        net_benefit_5_years = (annual_savings_sgd * 5) - net_cost
        net_benefit_10_years = (annual_savings_sgd * 10) - net_cost

        # Calculate ROI percentage
        roi_percent = (annual_savings_sgd / net_cost * 100) if net_cost > 0 else 0

        # Generate notes
        notes = self._generate_notes(
            product_data, current_rating, new_rating, is_voucher_eligible,
            payback_years, annual_savings_sgd
        )

        return ROIResult(
            product_type=normalized_type,
            product_display_name=product_data["name"],
            current_rating=current_rating,
            new_rating=new_rating,
            tick_improvement=new_rating - current_rating,
            product_price=round(product_price, 2),
            voucher_amount=round(voucher_amount, 2),
            net_cost=round(net_cost, 2),
            annual_energy_savings_kwh=round(annual_kwh_savings, 1),
            annual_savings_sgd=round(annual_savings_sgd, 2),
            monthly_savings_sgd=round(monthly_savings_sgd, 2),
            payback_period_months=payback_months,
            payback_period_years=round(payback_years, 1),
            net_benefit_5_years=round(net_benefit_5_years, 2),
            net_benefit_10_years=round(net_benefit_10_years, 2),
            roi_percent_annual=round(roi_percent, 1),
            is_voucher_eligible=is_voucher_eligible,
            minimum_rating_for_voucher=min_voucher_tick,
            notes=notes
        )

    def recommend_from_diagnosis(
        self,
        diagnosis: DiagnosisResult,
        budget_max: float = 2000.0
    ) -> List[UpgradeRecommendation]:
        """Generate appliance upgrade recommendations based on bill diagnosis.

        Args:
            diagnosis: The diagnosis result from bill analysis
            budget_max: Maximum budget for recommendations

        Returns:
            List of recommended upgrades sorted by priority
        """
        recommendations = []
        priority = 1

        # Check for electricity efficiency issues
        elec_issues = [i for i in diagnosis.efficiency_issues if i.utility_type == "electricity"]

        for issue in elec_issues:
            if issue.deviation_percent >= 20:
                # Recommend AC upgrade for high electricity users
                recommendations.append(UpgradeRecommendation(
                    product_type="air_conditioners",
                    product_display_name="Energy-efficient Air-conditioner",
                    reason=f"Your electricity usage is {issue.deviation_percent:.0f}% above average. Air conditioning typically accounts for 30-40% of household electricity.",
                    estimated_annual_savings=issue.potential_annual_savings_sgd * 0.4,  # 40% from AC
                    priority=priority
                ))
                priority += 1

            if issue.deviation_percent >= 10:
                # Recommend refrigerator upgrade
                recommendations.append(UpgradeRecommendation(
                    product_type="refrigerators",
                    product_display_name="Energy-efficient Refrigerator",
                    reason="Refrigerators run 24/7. A 4-tick model can save up to $100 annually compared to older models.",
                    estimated_annual_savings=100.0,
                    priority=priority
                ))
                priority += 1

                # Recommend LED lights
                recommendations.append(UpgradeRecommendation(
                    product_type="led_lights",
                    product_display_name="LED Lights",
                    reason="Switching from incandescent to LED bulbs saves 80% on lighting costs with minimal investment.",
                    estimated_annual_savings=50.0,
                    priority=priority
                ))
                priority += 1

        # Check for water efficiency issues
        water_issues = [i for i in diagnosis.efficiency_issues if i.utility_type == "water"]
        for issue in water_issues:
            if issue.deviation_percent >= 15:
                recommendations.append(UpgradeRecommendation(
                    product_type="water_closets",
                    product_display_name="Water-efficient Toilet/Taps",
                    reason=f"Your water usage is {issue.deviation_percent:.0f}% above average. Water-efficient fixtures can reduce consumption significantly.",
                    estimated_annual_savings=issue.potential_annual_savings_sgd,
                    priority=priority
                ))
                priority += 1

        # Calculate ROI for top recommendations within budget
        for rec in recommendations[:3]:  # Top 3
            try:
                typical_price = self._get_typical_price(rec.product_type)
                if typical_price <= budget_max:
                    roi = self.calculate(
                        product_type=rec.product_type,
                        current_rating=1,  # Assume old/inefficient
                        new_rating=self._get_max_rating(rec.product_type),
                        product_price=typical_price,
                        apply_voucher=True
                    )
                    rec.roi_if_upgraded = roi
            except Exception:
                pass  # Skip if calculation fails

        return sorted(recommendations, key=lambda x: x.priority)

    def get_product_info(self, product_type: str) -> Dict[str, Any]:
        """Get information about a product type for the calculator UI."""
        normalized = self._normalize_product_type(product_type)

        if normalized not in ENERGY_CONSUMPTION_DATA:
            return {"error": f"Unknown product type: {product_type}"}

        data = ENERGY_CONSUMPTION_DATA[normalized]
        return {
            "product_type": normalized,
            "display_name": data["name"],
            "min_voucher_tick": data["min_voucher_tick"],
            "max_ticks": data["max_ticks"],
            "available_ratings": list(data["consumption_by_tick"].keys()),
            "typical_price_range": data["typical_price_range"],
            "voucher_value": self.voucher_value,
            "electricity_rate": self.electricity_rate,
        }

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get information about all supported product types."""
        products = []
        for product_type, data in ENERGY_CONSUMPTION_DATA.items():
            products.append({
                "product_type": product_type,
                "display_name": data["name"],
                "min_voucher_tick": data["min_voucher_tick"],
                "max_ticks": data["max_ticks"],
                "typical_price_range": data["typical_price_range"],
            })
        return products

    def _normalize_product_type(self, product_type: str) -> str:
        """Normalize product type string."""
        normalized = product_type.lower().strip()

        # Common aliases
        aliases = {
            "aircon": "air_conditioners",
            "air conditioner": "air_conditioners",
            "ac": "air_conditioners",
            "fridge": "refrigerators",
            "refrigerator": "refrigerators",
            "washer": "washing_machines",
            "washing machine": "washing_machines",
            "led": "led_lights",
            "light": "led_lights",
            "lights": "led_lights",
            "bulb": "led_lights",
            "fan": "dc_fans",
            "dc fan": "dc_fans",
            "toilet": "water_closets",
        }

        return aliases.get(normalized, normalized)

    def _get_typical_price(self, product_type: str) -> float:
        """Get typical mid-range price for a product type."""
        normalized = self._normalize_product_type(product_type)
        if normalized in ENERGY_CONSUMPTION_DATA:
            price_range = ENERGY_CONSUMPTION_DATA[normalized]["typical_price_range"]
            return (price_range[0] + price_range[1]) / 2
        return 500.0  # Default

    def _get_max_rating(self, product_type: str) -> int:
        """Get maximum tick rating for a product type."""
        normalized = self._normalize_product_type(product_type)
        if normalized in ENERGY_CONSUMPTION_DATA:
            return ENERGY_CONSUMPTION_DATA[normalized]["max_ticks"]
        return 4

    def _generate_notes(
        self,
        product_data: Dict,
        current_rating: int,
        new_rating: int,
        is_voucher_eligible: bool,
        payback_years: float,
        annual_savings: float
    ) -> List[str]:
        """Generate helpful notes for the ROI result."""
        notes = []

        if is_voucher_eligible:
            notes.append(f"This {product_data['name'].lower()} qualifies for the $300 Climate Voucher!")
        else:
            notes.append(f"Note: Minimum {product_data['min_voucher_tick']}-tick rating required for Climate Voucher eligibility.")

        if payback_years <= 2:
            notes.append("Excellent investment - payback within 2 years!")
        elif payback_years <= 5:
            notes.append("Good investment - typical appliance lifespan is 10-15 years.")

        if annual_savings >= 100:
            notes.append(f"Significant savings of ${annual_savings:.0f}/year on electricity bills.")

        # Product-specific tips
        if product_data["name"] == "Air-conditioner":
            notes.append("Tip: Set temperature to 25°C and use fan mode when possible for additional savings.")
        elif product_data["name"] == "Refrigerator":
            notes.append("Tip: Keep coils clean and ensure door seals are tight for optimal efficiency.")

        return notes
