"""District-level consumption aggregation service.

Handles:
- Postal code extraction and parsing (Singapore 6-digit format)
- District-level aggregation (first 2 digits = postal district)
- Sector-level aggregation (first 4 digits = postal sector)
- Housing type classification from address
- Geocoding for heatmap visualization
"""

import re
from typing import List, Dict, Optional
from collections import defaultdict
import numpy as np

from models.intervention import HousingType


# Singapore postal district mapping
# First 2 digits of postal code -> District name and approximate coordinates
SG_POSTAL_DISTRICTS = {
    "01": {"name": "Raffles Place, Cecil, Marina, People's Park", "lat": 1.2819, "lng": 103.8511},
    "02": {"name": "Anson, Tanjong Pagar", "lat": 1.2761, "lng": 103.8453},
    "03": {"name": "Queenstown, Tiong Bahru", "lat": 1.2897, "lng": 103.8067},
    "04": {"name": "Telok Blangah, Harbourfront", "lat": 1.2701, "lng": 103.8200},
    "05": {"name": "Pasir Panjang, Hong Leong Garden, Clementi", "lat": 1.2765, "lng": 103.7650},
    "06": {"name": "High Street, Beach Road", "lat": 1.2930, "lng": 103.8540},
    "07": {"name": "Middle Road, Golden Mile", "lat": 1.3020, "lng": 103.8600},
    "08": {"name": "Little India", "lat": 1.3066, "lng": 103.8518},
    "09": {"name": "Orchard, Cairnhill, River Valley", "lat": 1.3050, "lng": 103.8310},
    "10": {"name": "Ardmore, Bukit Timah, Holland Road, Tanglin", "lat": 1.3055, "lng": 103.8200},
    "11": {"name": "Watten Estate, Novena, Thomson", "lat": 1.3250, "lng": 103.8350},
    "12": {"name": "Balestier, Toa Payoh, Serangoon", "lat": 1.3350, "lng": 103.8550},
    "13": {"name": "Macpherson, Braddell", "lat": 1.3400, "lng": 103.8800},
    "14": {"name": "Geylang, Eunos", "lat": 1.3200, "lng": 103.8900},
    "15": {"name": "Katong, Joo Chiat, Amber Road", "lat": 1.3050, "lng": 103.9050},
    "16": {"name": "Bedok, Upper East Coast, Eastwood, Kew Drive", "lat": 1.3250, "lng": 103.9300},
    "17": {"name": "Loyang, Changi", "lat": 1.3550, "lng": 103.9850},
    "18": {"name": "Tampines, Pasir Ris", "lat": 1.3550, "lng": 103.9450},
    "19": {"name": "Serangoon Garden, Hougang, Punggol", "lat": 1.3750, "lng": 103.8950},
    "20": {"name": "Bishan, Ang Mo Kio", "lat": 1.3650, "lng": 103.8500},
    "21": {"name": "Upper Bukit Timah, Clementi Park, Ulu Pandan", "lat": 1.3400, "lng": 103.7700},
    "22": {"name": "Jurong", "lat": 1.3350, "lng": 103.7050},
    "23": {"name": "Hillview, Dairy Farm, Bukit Panjang, Choa Chu Kang", "lat": 1.3800, "lng": 103.7500},
    "24": {"name": "Lim Chu Kang, Tengah", "lat": 1.4100, "lng": 103.7100},
    "25": {"name": "Kranji, Woodgrove", "lat": 1.4250, "lng": 103.7550},
    "26": {"name": "Upper Thomson, Springleaf", "lat": 1.3950, "lng": 103.8200},
    "27": {"name": "Yishun, Sembawang", "lat": 1.4300, "lng": 103.8350},
    "28": {"name": "Seletar", "lat": 1.4100, "lng": 103.8700},
    "29": {"name": "Admiralty, Woodlands", "lat": 1.4400, "lng": 103.7850},
    "30": {"name": "Admiralty, Woodlands", "lat": 1.4450, "lng": 103.7900},
    "31": {"name": "Lower Mandai, Upper Thomson", "lat": 1.3850, "lng": 103.8150},
    "32": {"name": "Mandai", "lat": 1.4050, "lng": 103.7850},
    "33": {"name": "Upper Bukit Timah", "lat": 1.3600, "lng": 103.7700},
    "34": {"name": "Bukit Batok, Bukit Gombak, Hillview", "lat": 1.3550, "lng": 103.7500},
    "35": {"name": "Jurong Industrial Estate", "lat": 1.3300, "lng": 103.6850},
    "36": {"name": "Jurong Industrial Estate", "lat": 1.3250, "lng": 103.6750},
    "37": {"name": "Jurong Industrial Estate", "lat": 1.3200, "lng": 103.6650},
    "38": {"name": "Jurong East, Teban Gardens", "lat": 1.3350, "lng": 103.7350},
    "39": {"name": "Jurong West, Hong Kah", "lat": 1.3400, "lng": 103.6950},
    "40": {"name": "Jurong West, Boon Lay", "lat": 1.3450, "lng": 103.7100},
    "41": {"name": "Jurong West, Pioneer", "lat": 1.3250, "lng": 103.6550},
    "42": {"name": "Jurong Island", "lat": 1.2650, "lng": 103.6850},
    "43": {"name": "Jurong Island", "lat": 1.2600, "lng": 103.6700},
    "44": {"name": "Jurong Island", "lat": 1.2550, "lng": 103.6550},
    "45": {"name": "Jurong Island", "lat": 1.2500, "lng": 103.6400},
    "46": {"name": "Bukit Timah, Holland Road", "lat": 1.3300, "lng": 103.7950},
    "47": {"name": "Bukit Timah, King Albert Park", "lat": 1.3350, "lng": 103.7800},
    "48": {"name": "Bukit Timah, Beauty World", "lat": 1.3400, "lng": 103.7750},
    "49": {"name": "Bukit Timah, Stevens Road, Farrer Road", "lat": 1.3150, "lng": 103.8150},
    "50": {"name": "Bukit Timah, Newton", "lat": 1.3100, "lng": 103.8250},
    "51": {"name": "Bukit Timah, Novena", "lat": 1.3200, "lng": 103.8400},
    "52": {"name": "Serangoon North, Hougang", "lat": 1.3700, "lng": 103.8750},
    "53": {"name": "Serangoon North", "lat": 1.3750, "lng": 103.8700},
    "54": {"name": "Hougang, Punggol", "lat": 1.3800, "lng": 103.8850},
    "55": {"name": "Sengkang, Punggol", "lat": 1.3900, "lng": 103.8950},
    "56": {"name": "Sengkang", "lat": 1.3950, "lng": 103.8900},
    "57": {"name": "Yio Chu Kang, Ang Mo Kio", "lat": 1.3800, "lng": 103.8450},
    "58": {"name": "Ang Mo Kio", "lat": 1.3700, "lng": 103.8400},
    "59": {"name": "Ang Mo Kio, Thomson", "lat": 1.3650, "lng": 103.8350},
    "60": {"name": "Ang Mo Kio, Upper Thomson", "lat": 1.3700, "lng": 103.8300},
    "65": {"name": "Hillcrest, Bukit Panjang", "lat": 1.3750, "lng": 103.7650},
    "66": {"name": "Bukit Panjang", "lat": 1.3800, "lng": 103.7600},
    "67": {"name": "Choa Chu Kang", "lat": 1.3850, "lng": 103.7450},
    "68": {"name": "Choa Chu Kang", "lat": 1.3900, "lng": 103.7400},
    "69": {"name": "Lim Chu Kang", "lat": 1.4150, "lng": 103.7000},
    "70": {"name": "Lim Chu Kang", "lat": 1.4200, "lng": 103.6950},
    "71": {"name": "Lim Chu Kang", "lat": 1.4250, "lng": 103.6900},
    "72": {"name": "Sengkang, Punggol", "lat": 1.3950, "lng": 103.9050},
    "73": {"name": "Pasir Ris", "lat": 1.3750, "lng": 103.9500},
    "75": {"name": "Yishun", "lat": 1.4200, "lng": 103.8300},
    "76": {"name": "Yishun", "lat": 1.4250, "lng": 103.8250},
    "77": {"name": "Upper Thomson, Springleaf", "lat": 1.4000, "lng": 103.8150},
    "78": {"name": "Upper Thomson, Springleaf", "lat": 1.4050, "lng": 103.8100},
    "79": {"name": "Seletar", "lat": 1.4150, "lng": 103.8650},
    "80": {"name": "Sembawang, Yishun", "lat": 1.4350, "lng": 103.8200},
    "81": {"name": "Sembawang, Yishun", "lat": 1.4400, "lng": 103.8150},
    "82": {"name": "Sembawang, Canberra", "lat": 1.4450, "lng": 103.8100},
}


def extract_postal_code(address: str) -> Optional[str]:
    """Extract 6-digit Singapore postal code from address.

    Singapore postal codes are 6 digits, typically at end of address.

    Examples:
        "123 Orchard Road #12-34 Singapore 238888" -> "238888"
        "BLK 123 TOA PAYOH LORONG 1 #08-22 S(310123)" -> "310123"
        "45 Jurong East Ave 1 #05-12 Singapore 609788" -> "609788"

    Args:
        address: Full address string

    Returns:
        6-digit postal code or None if not found
    """
    if not address:
        return None

    # Patterns for Singapore postal codes
    patterns = [
        r'Singapore\s*(\d{6})',           # "Singapore 238888"
        r'S\((\d{6})\)',                   # "S(310123)"
        r'S(\d{6})',                       # "S310123"
        r'\b(\d{6})\s*$',                  # 6 digits at end of string
        r'(?:SG|SGP)\s*(\d{6})',           # "SG 238888"
    ]

    for pattern in patterns:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            postal = match.group(1)
            # Validate it's a plausible Singapore postal code
            district = postal[:2]
            if district in SG_POSTAL_DISTRICTS or district.isdigit():
                return postal

    return None


def get_postal_district(postal_code: str) -> str:
    """Get 2-digit postal district from 6-digit postal code.

    Args:
        postal_code: 6-digit Singapore postal code

    Returns:
        2-digit postal district code
    """
    if not postal_code or len(postal_code) < 2:
        return "00"
    return postal_code[:2]


def get_postal_sector(postal_code: str) -> str:
    """Get 4-digit postal sector from 6-digit postal code.

    Args:
        postal_code: 6-digit Singapore postal code

    Returns:
        4-digit postal sector code
    """
    if not postal_code or len(postal_code) < 4:
        return "0000"
    return postal_code[:4]


def classify_housing_type(address: str) -> HousingType:
    """Classify housing type from address string.

    Uses keywords and patterns common in Singapore addresses.

    Args:
        address: Full address string

    Returns:
        HousingType enum value
    """
    if not address:
        return HousingType.UNKNOWN

    addr_upper = address.upper()

    # HDB patterns (BLK, BLOCK, specific estate names)
    hdb_patterns = [
        r'\bBLK\b', r'\bBLOCK\b', r'\bHDB\b',
        r'\bTOA PAYOH\b', r'\bANG MO KIO\b', r'\bBEDOK\b',
        r'\bTAMPINES\b', r'\bJURONG\b', r'\bWOODLANDS\b',
        r'\bYISHUN\b', r'\bSENGKANG\b', r'\bPUNGGOL\b',
    ]

    for pattern in hdb_patterns:
        if re.search(pattern, addr_upper):
            # Try to determine room type from context
            if re.search(r'1[-\s]?ROOM|2[-\s]?ROOM', addr_upper):
                return HousingType.HDB_1_2_ROOM
            elif re.search(r'3[-\s]?ROOM', addr_upper):
                return HousingType.HDB_3_ROOM
            elif re.search(r'4[-\s]?ROOM', addr_upper):
                return HousingType.HDB_4_ROOM
            elif re.search(r'5[-\s]?ROOM', addr_upper):
                return HousingType.HDB_5_ROOM
            elif re.search(r'EXECUTIVE|MAISONETTE', addr_upper):
                return HousingType.HDB_EXECUTIVE
            # Default to 4-room as most common
            return HousingType.HDB_4_ROOM

    # Condo patterns
    condo_patterns = [
        r'\bCONDO\b', r'\bCONDOMINIUM\b', r'\bRESIDENCES?\b',
        r'\bTOWER\b', r'\bHEIGHTS\b', r'\bPARC\b', r'\bVILLE\b',
        r'\bSUITES?\b', r'\bAPARTMENT\b',
    ]

    for pattern in condo_patterns:
        if re.search(pattern, addr_upper):
            return HousingType.CONDO

    # Landed property patterns
    landed_patterns = [
        r'\bHOUSE\b', r'\bBUNGALOW\b', r'\bSEMI[-\s]?D\b',
        r'\bTERRACE\b', r'\bDETACHED\b', r'\bVILLA\b',
        r'\bJALAN\b', r'\bLORNIE\b', r'\bGCB\b',
    ]

    for pattern in landed_patterns:
        if re.search(pattern, addr_upper):
            return HousingType.LANDED

    # Commercial patterns
    commercial_patterns = [
        r'\bOFFICE\b', r'\bSHOP\b', r'\bINDUSTRIAL\b',
        r'\bWAREHOUSE\b', r'\bFACTORY\b', r'\bMALL\b',
        r'\bCENTRE\b', r'\bPLAZA\b',
    ]

    for pattern in commercial_patterns:
        if re.search(pattern, addr_upper):
            return HousingType.COMMERCIAL

    return HousingType.UNKNOWN


class DistrictAggregator:
    """Service for aggregating consumption data by postal district."""

    def __init__(self, statistical_analyzer=None):
        """Initialize the aggregator.

        Args:
            statistical_analyzer: Optional StatisticalAnalyzer instance
        """
        self.statistical_analyzer = statistical_analyzer

    async def aggregate_by_district(
        self,
        consumption_records: List[Dict]
    ) -> Dict[str, Dict]:
        """Aggregate consumption data by postal district.

        Args:
            consumption_records: List of records with premise_address and consumption_kwh

        Returns:
            Dict keyed by postal district with aggregated stats
        """
        districts = defaultdict(list)

        for record in consumption_records:
            address = record.get("premise_address", "")
            postal_code = extract_postal_code(address)

            if postal_code:
                district = get_postal_district(postal_code)
                consumption = record.get("consumption_kwh", 0)

                if consumption and consumption > 0:
                    districts[district].append({
                        "postal_code": postal_code,
                        "consumption_kwh": consumption,
                        "account_number": record.get("account_number"),
                        "housing_type": classify_housing_type(address).value,
                        "period_start": record.get("billing_period_start"),
                        "period_end": record.get("billing_period_end"),
                    })

        # Calculate aggregates per district
        result = {}
        for district, records in districts.items():
            consumptions = [r["consumption_kwh"] for r in records]
            district_info = SG_POSTAL_DISTRICTS.get(district, {
                "name": "Unknown",
                "lat": 1.3521,
                "lng": 103.8198
            })

            result[district] = {
                "postal_district": district,
                "district_name": district_info["name"],
                "latitude": district_info["lat"],
                "longitude": district_info["lng"],
                "household_count": len(records),
                "total_consumption_kwh": sum(consumptions),
                "average_consumption_kwh": sum(consumptions) / len(consumptions),
                "median_consumption_kwh": float(np.median(consumptions)),
                "min_consumption_kwh": min(consumptions),
                "max_consumption_kwh": max(consumptions),
                "records": records
            }

        return result

    async def aggregate_by_housing_type(
        self,
        consumption_records: List[Dict]
    ) -> Dict[str, Dict]:
        """Aggregate consumption data by housing type.

        Args:
            consumption_records: List of records with premise_address and consumption_kwh

        Returns:
            Dict keyed by housing type with aggregated stats
        """
        cohorts = defaultdict(list)

        for record in consumption_records:
            address = record.get("premise_address", "")
            housing_type = classify_housing_type(address)
            consumption = record.get("consumption_kwh", 0)

            if consumption and consumption > 0:
                cohorts[housing_type.value].append(consumption)

        # Calculate statistics per cohort
        result = {}
        for housing_type, consumptions in cohorts.items():
            if len(consumptions) >= 2:
                arr = np.array(consumptions)
                std = float(np.std(arr, ddof=1))
                mean = float(np.mean(arr))

                result[housing_type] = {
                    "housing_type": housing_type,
                    "sample_size": len(consumptions),
                    "mean_kwh": mean,
                    "std_dev_kwh": std,
                    "median_kwh": float(np.median(arr)),
                    "min_kwh": float(np.min(arr)),
                    "max_kwh": float(np.max(arr)),
                    "ci_lower": mean - 1.96 * std,
                    "ci_upper": mean + 1.96 * std,
                    "standard_error": std / np.sqrt(len(consumptions)),
                }

        return result

    async def generate_heatmap_data(
        self,
        district_data: Dict[str, Dict]
    ) -> List[Dict]:
        """Generate heatmap data points with normalized intensity.

        Args:
            district_data: Output from aggregate_by_district()

        Returns:
            List of heatmap data points with coordinates and intensity
        """
        if not district_data:
            return []

        # Find max for normalization
        max_consumption = max(
            d["average_consumption_kwh"]
            for d in district_data.values()
        )

        if max_consumption == 0:
            max_consumption = 1

        heatmap_points = []

        for district, data in district_data.items():
            intensity = data["average_consumption_kwh"] / max_consumption

            heatmap_points.append({
                "postal_district": district,
                "district_name": data["district_name"],
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "consumption_kwh": data["average_consumption_kwh"],
                "intensity": round(intensity, 4),
                "household_count": data["household_count"]
            })

        # Sort by intensity descending
        heatmap_points.sort(key=lambda x: x["intensity"], reverse=True)

        return heatmap_points
