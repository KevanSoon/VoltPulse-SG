"""Pydantic models for Singapore electricity bill data extraction."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


# Singapore Open Electricity Market (OEM) retailers
SG_ELECTRICITY_PROVIDERS = [
    "SP Services",
    "Geneco",
    "Keppel Electric",
    "Senoko Energy",
    "Tuas Power",
    "PacificLight",
    "Union Power",
    "Ohm Energy",
    "iSwitch",
    "Best Electricity",
    "Diamond Electric",
    "Sunseap",
]


class MonthlyConsumption(BaseModel):
    """Monthly consumption data point extracted from trend charts."""

    month: Optional[str] = Field(
        None,
        description="Month abbreviation (e.g., 'JAN', 'FEB', 'MAR')"
    )
    value: Optional[float] = Field(
        None,
        description="Consumption value for that month"
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement (e.g., 'kWh', 'Cu M')"
    )


class ConsumptionTrend(BaseModel):
    """Consumption trend data extracted from bar charts on utility bills."""

    service_type: Optional[str] = Field(
        None,
        description="Type of service (Electricity, Gas, Water)"
    )
    monthly_data: List[MonthlyConsumption] = Field(
        default_factory=list,
        description="Monthly consumption values from bar chart"
    )
    neighbour_average: Optional[float] = Field(
        None,
        description="Neighbour average consumption if shown"
    )
    national_average: Optional[float] = Field(
        None,
        description="National average consumption if shown"
    )
    trend_direction: Optional[str] = Field(
        None,
        description="Overall trend: 'increasing', 'decreasing', or 'stable'"
    )


class TariffTier(BaseModel):
    """Tiered electricity tariff rate structure."""

    tier_name: Optional[str] = Field(
        None,
        description="Name of the tariff tier (e.g., 'First 500 kWh', 'Above 500 kWh')"
    )
    min_kwh: Optional[float] = Field(
        None,
        description="Minimum kWh for this tier"
    )
    max_kwh: Optional[float] = Field(
        None,
        description="Maximum kWh for this tier (null if unlimited)"
    )
    rate_per_kwh: Optional[float] = Field(
        None,
        description="Rate in SGD per kWh for this tier"
    )
    kwh_used: Optional[float] = Field(
        None,
        description="kWh consumed in this tier"
    )
    amount: Optional[float] = Field(
        None,
        description="Total amount for this tier in SGD"
    )


class ElectricityBillExtraction(BaseModel):
    """Structured extraction from Singapore electricity bill OCR text.

    Designed for Singapore Open Electricity Market (OEM) bills from
    providers like SP Services, Geneco, Keppel, Senoko, Tuas Power, etc.
    """

    # Account Information
    account_number: Optional[str] = Field(
        None,
        description="Electricity account number"
    )
    customer_name: Optional[str] = Field(
        None,
        description="Account holder name"
    )
    premise_address: Optional[str] = Field(
        None,
        description="Service/premise address"
    )

    # Billing Period
    billing_period_start: Optional[date] = Field(
        None,
        description="Start date of billing period"
    )
    billing_period_end: Optional[date] = Field(
        None,
        description="End date of billing period"
    )
    bill_date: Optional[date] = Field(
        None,
        description="Date bill was issued"
    )
    due_date: Optional[date] = Field(
        None,
        description="Payment due date"
    )
    billing_days: Optional[int] = Field(
        None,
        description="Number of days in billing period"
    )

    # Consumption Data
    consumption_kwh: Optional[float] = Field(
        None,
        description="Total electricity consumed in kWh"
    )
    previous_reading: Optional[float] = Field(
        None,
        description="Previous meter reading"
    )
    current_reading: Optional[float] = Field(
        None,
        description="Current meter reading"
    )
    meter_number: Optional[str] = Field(
        None,
        description="Electricity meter identifier"
    )
    daily_average_kwh: Optional[float] = Field(
        None,
        description="Average daily consumption in kWh"
    )

    # Gas Services (for SP combined bills)
    gas_usage_kwh: Optional[float] = Field(
        None,
        description="Gas consumption in kWh"
    )
    gas_charges: Optional[float] = Field(
        None,
        description="Gas charges in SGD"
    )
    gas_provider: Optional[str] = Field(
        None,
        description="Gas provider name (e.g., City Gas Pte Ltd)"
    )

    # Water Services (for SP combined bills)
    water_usage_cu_m: Optional[float] = Field(
        None,
        description="Water consumption in cubic meters (Cu M)"
    )
    water_charges: Optional[float] = Field(
        None,
        description="Water charges in SGD"
    )
    water_provider: Optional[str] = Field(
        None,
        description="Water provider name (e.g., Public Utilities Board)"
    )

    # Consumption Trends (extracted from bar charts)
    consumption_trends: List[ConsumptionTrend] = Field(
        default_factory=list,
        description="Historical consumption trends from bar charts for each service"
    )

    # Cost Breakdown (all amounts in SGD)
    total_amount: Optional[float] = Field(
        None,
        description="Total bill amount in SGD"
    )
    energy_charges: Optional[float] = Field(
        None,
        description="Base energy/consumption charges before GST"
    )
    tariff_tiers: List[TariffTier] = Field(
        default_factory=list,
        description="Tiered tariff breakdown if available"
    )
    gst_amount: Optional[float] = Field(
        None,
        description="GST amount (9% as of 2024)"
    )
    other_charges: Optional[float] = Field(
        None,
        description="Miscellaneous fees, adjustments, rebates"
    )
    previous_balance: Optional[float] = Field(
        None,
        description="Outstanding balance from previous bill"
    )

    # Provider Information
    provider_name: Optional[str] = Field(
        None,
        description="Electricity retailer name (SP Services, Geneco, etc.)"
    )
    plan_name: Optional[str] = Field(
        None,
        description="Electricity plan name if specified"
    )

    # Extraction Metadata
    extraction_confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="LLM confidence score for extraction quality"
    )
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Parsing issues or ambiguities encountered"
    )
    raw_ocr_text: Optional[str] = Field(
        None,
        description="Original OCR text used for extraction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "account_number": "1234567890",
                "customer_name": "John Tan",
                "premise_address": "123 Orchard Road #12-34 Singapore 238888",
                "billing_period_start": "2024-01-01",
                "billing_period_end": "2024-01-31",
                "bill_date": "2024-02-01",
                "due_date": "2024-02-15",
                "billing_days": 31,
                "consumption_kwh": 350.5,
                "previous_reading": 12500,
                "current_reading": 12850.5,
                "meter_number": "M12345678",
                "daily_average_kwh": 11.3,
                "total_amount": 95.50,
                "energy_charges": 87.63,
                "gst_amount": 7.87,
                "provider_name": "SP Services",
                "extraction_confidence": 0.92,
            }
        }
