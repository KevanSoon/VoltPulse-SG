"""Pydantic models for intervention tracking and housing type classification."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum


class InterventionType(str, Enum):
    """Types of energy efficiency interventions."""
    COOL_PAINT = "cool_paint"
    LED_RETROFIT = "led_retrofit"
    SOLAR_PANEL = "solar_panel"
    AIRCON_UPGRADE = "aircon_upgrade"
    INSULATION = "insulation"
    SMART_METER = "smart_meter"
    OTHER = "other"


class HousingType(str, Enum):
    """Singapore housing types for cohort analysis."""
    HDB_1_2_ROOM = "hdb_1_2_room"
    HDB_3_ROOM = "hdb_3_room"
    HDB_4_ROOM = "hdb_4_room"
    HDB_5_ROOM = "hdb_5_room"
    HDB_EXECUTIVE = "hdb_executive"
    CONDO = "condo"
    LANDED = "landed"
    COMMERCIAL = "commercial"
    UNKNOWN = "unknown"


class Intervention(BaseModel):
    """Model for tracking energy efficiency interventions."""

    id: Optional[str] = Field(None, description="Unique intervention ID")
    account_number: str = Field(..., description="Linked electricity account")
    postal_code: str = Field(..., description="6-digit Singapore postal code")
    housing_type: HousingType = Field(default=HousingType.UNKNOWN)

    intervention_type: InterventionType
    intervention_date: date
    description: Optional[str] = None
    cost_sgd: Optional[float] = None

    # Before/After consumption tracking
    pre_intervention_kwh_avg: Optional[float] = Field(
        None, description="Average monthly kWh before intervention (3-month)"
    )
    post_intervention_kwh_avg: Optional[float] = Field(
        None, description="Average monthly kWh after intervention (3-month)"
    )
    consumption_delta_kwh: Optional[float] = Field(
        None, description="Change in consumption (negative = savings)"
    )
    consumption_delta_percent: Optional[float] = Field(
        None, description="Percentage change in consumption"
    )

    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "int_abc123",
                "account_number": "1234567890",
                "postal_code": "310123",
                "housing_type": "hdb_4_room",
                "intervention_type": "led_retrofit",
                "intervention_date": "2024-06-15",
                "description": "Replaced all lighting with LED bulbs",
                "cost_sgd": 250.00,
                "pre_intervention_kwh_avg": 450.5,
                "post_intervention_kwh_avg": 380.2,
                "consumption_delta_kwh": -70.3,
                "consumption_delta_percent": -15.6,
            }
        }
