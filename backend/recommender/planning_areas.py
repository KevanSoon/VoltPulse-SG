"""Singapore Planning Area mapping from postal codes.

This module provides accurate postal code to planning area conversion
and planning area proximity calculations for location-based retailer ranking.

Singapore has 55 planning areas grouped by postal districts (first 2 digits).
"""

from typing import Optional, List, Dict


# Complete Singapore postal district to planning area mapping
# Based on official Singapore postal code system
DISTRICT_TO_PLANNING_AREA = {
    # Central Region
    "01": "Raffles Place",
    "02": "Anson",
    "03": "Queenstown",  # NOT Bukit Timah! (includes Jalan Bukit Merah)
    "04": "Telok Blangah",
    "05": "Pasir Panjang",
    "06": "High Street",
    "07": "Middle Road",
    "08": "Little India",
    "09": "Orchard",
    "10": "Ardmore",
    "11": "Newton",
    "12": "Balestier",
    "13": "Macpherson",
    "14": "Geylang",
    "15": "Katong",
    "16": "Bedok",
    "17": "Bedok",  # Bedok extends across 16-17
    "18": "Tampines",
    "19": "Pasir Ris",

    # East Region
    "20": "Pasir Ris",  # Pasir Ris extends
    "21": "Punggol",
    "22": "Serangoon",
    "23": "Hougang",
    "24": "Ang Mo Kio",
    "25": "Bishan",
    "26": "Toa Payoh",
    "27": "Bishan",  # Bishan extends

    # North-East Region
    "28": "Sengkang",

    # West Region
    "29": "Jurong East",
    "30": "Jurong East",  # Jurong East extends
    "31": "Bukit Timah",
    "32": "Bukit Timah",  # Bukit Timah extends
    "33": "Clementi",

    # Central Water Catchment
    "34": "Clementi",  # Clementi extends

    # Rest of West
    "35": "Jurong West",
    "36": "Jurong West",  # Jurong West extends
    "37": "Jurong West",
    "38": "Choa Chu Kang",
    "39": "Bukit Batok",
    "40": "Bukit Panjang",
    "41": "Bukit Panjang",  # Bukit Panjang extends

    # North Region
    "42": "Sembawang",
    "43": "Sembawang",  # Sembawang extends
    "44": "Yishun",
    "45": "Yishun",  # Yishun extends
    "46": "Woodlands",
    "47": "Woodlands",  # Woodlands extends
    "48": "Sungei Kadut",

    # Additional Central
    "49": "Bukit Merah",  # Distinct from Bukit Timah!
    "50": "Kallang",
    "51": "Novena",
    "52": "Toa Payoh",  # Toa Payoh extends

    # Additional East
    "53": "Serangoon",  # Serangoon extends
    "54": "Paya Lebar",
    "55": "Marine Parade",

    # Additional regions
    "56": "Ang Mo Kio",  # Ang Mo Kio extends
    "57": "Yishun",  # Yishun extends further

    # West extensions
    "58": "Jurong East",  # Jurong East industrial
    "59": "Jurong West",  # Jurong West industrial
    "60": "Jurong West",  # Jurong West extends
    "61": "Jurong West",
    "62": "Jurong West",
    "63": "Jurong West",
    "64": "Jurong West",

    # Additional North
    "65": "Woodlands",  # Woodlands industrial
    "66": "Kranji",
    "67": "Choa Chu Kang",
    "68": "Sembawang",

    # Additional East
    "69": "Punggol",  # Punggol extends
    "70": "Tampines",  # Tampines industrial
    "71": "Pasir Ris",  # Pasir Ris extends
    "72": "Jurong East",  # Jurong port
    "73": "Tuas",

    # Additional North-East
    "75": "Yishun",  # Yishun industrial
    "76": "Yishun",
    "77": "Sembawang",  # Sembawang shipyard
    "78": "Sengkang",
    "79": "Punggol",
    "80": "Sengkang",  # Sengkang extends
    "81": "Punggol",  # Punggol extends
    "82": "Punggol",  # Punggol extends

    # Sentosa / Islands
    "90": "Sentosa",
    "91": "Sentosa",
}


# Planning area adjacency for proximity scoring
# Format: planning_area -> list of neighbors within ~3-5km
PLANNING_AREA_NEIGHBORS = {
    "Raffles Place": ["Anson", "Kallang", "Queenstown"],
    "Anson": ["Raffles Place", "Telok Blangah", "Bukit Merah"],
    "Queenstown": ["Raffles Place", "Bukit Merah", "Clementi"],
    "Telok Blangah": ["Anson", "Bukit Merah", "Pasir Panjang"],
    "Pasir Panjang": ["Telok Blangah", "Clementi"],
    "High Street": ["Kallang", "Novena"],
    "Middle Road": ["Kallang", "Little India"],
    "Little India": ["Middle Road", "Novena", "Serangoon"],
    "Orchard": ["Newton", "Novena", "Bukit Timah"],
    "Ardmore": ["Orchard", "Newton"],
    "Newton": ["Orchard", "Ardmore", "Novena", "Bukit Timah"],
    "Balestier": ["Novena", "Toa Payoh"],
    "Macpherson": ["Geylang", "Paya Lebar", "Toa Payoh"],
    "Geylang": ["Macpherson", "Kallang", "Bedok"],
    "Katong": ["Marine Parade", "Geylang"],
    "Bedok": ["Geylang", "Tampines", "Marine Parade"],
    "Tampines": ["Bedok", "Pasir Ris", "Paya Lebar"],
    "Pasir Ris": ["Tampines", "Punggol"],
    "Punggol": ["Pasir Ris", "Sengkang", "Hougang"],
    "Serangoon": ["Little India", "Ang Mo Kio", "Hougang"],
    "Hougang": ["Serangoon", "Punggol", "Sengkang", "Ang Mo Kio"],
    "Ang Mo Kio": ["Serangoon", "Hougang", "Yishun", "Bishan"],
    "Bishan": ["Ang Mo Kio", "Toa Payoh", "Bukit Timah"],
    "Toa Payoh": ["Bishan", "Balestier", "Macpherson", "Novena"],
    "Sengkang": ["Punggol", "Hougang", "Yishun"],
    "Jurong East": ["Jurong West", "Clementi", "Bukit Batok"],
    "Bukit Timah": ["Orchard", "Newton", "Bishan", "Clementi"],
    "Clementi": ["Queenstown", "Bukit Timah", "Jurong East", "Pasir Panjang"],
    "Jurong West": ["Jurong East", "Choa Chu Kang", "Boon Lay"],
    "Choa Chu Kang": ["Jurong West", "Bukit Panjang", "Bukit Batok"],
    "Bukit Batok": ["Jurong East", "Choa Chu Kang", "Bukit Panjang"],
    "Bukit Panjang": ["Choa Chu Kang", "Bukit Batok", "Sembawang"],
    "Sembawang": ["Bukit Panjang", "Yishun", "Woodlands"],
    "Yishun": ["Sembawang", "Ang Mo Kio", "Sengkang"],
    "Woodlands": ["Sembawang", "Kranji"],
    "Sungei Kadut": ["Woodlands", "Choa Chu Kang"],
    "Bukit Merah": ["Anson", "Queenstown", "Telok Blangah"],
    "Kallang": ["Raffles Place", "Geylang", "Middle Road"],
    "Novena": ["Orchard", "Newton", "Toa Payoh", "Balestier"],
    "Paya Lebar": ["Macpherson", "Tampines"],
    "Marine Parade": ["Katong", "Bedok"],
    "Kranji": ["Woodlands", "Lim Chu Kang"],
    "Tuas": ["Jurong West", "Boon Lay"],
    "Sentosa": ["Telok Blangah"],
}


def get_planning_area(postal_code: str) -> Optional[str]:
    """
    Get planning area from Singapore postal code.

    Args:
        postal_code: 6-digit Singapore postal code

    Returns:
        Planning area name or None if invalid
    """
    if not postal_code or len(postal_code) < 2:
        return None

    district = postal_code[:2]
    return DISTRICT_TO_PLANNING_AREA.get(district)


def get_proximity_score(area1: str, area2: str) -> float:
    """
    Calculate location proximity score between two planning areas.

    Args:
        area1: First planning area
        area2: Second planning area

    Returns:
        1.0 = exact match
        0.7 = adjacent/neighbor
        0.0 = not close
    """
    if not area1 or not area2:
        return 0.0

    area1_norm = area1.strip()
    area2_norm = area2.strip()

    # Exact match
    if area1_norm == area2_norm:
        return 1.0

    # Check if neighbors
    neighbors = PLANNING_AREA_NEIGHBORS.get(area1_norm, [])
    if area2_norm in neighbors:
        return 0.7

    return 0.0


def get_all_planning_areas() -> List[str]:
    """Get list of all unique planning areas."""
    return sorted(set(DISTRICT_TO_PLANNING_AREA.values()))


def validate_postal_code(postal_code: str) -> bool:
    """
    Validate Singapore postal code format.

    Args:
        postal_code: String to validate

    Returns:
        True if valid Singapore postal code
    """
    if not postal_code:
        return False

    # Must be 6 digits
    if not postal_code.isdigit() or len(postal_code) != 6:
        return False

    # First 2 digits must be valid district
    district = postal_code[:2]
    return district in DISTRICT_TO_PLANNING_AREA


def get_district_name(postal_code: str) -> Optional[str]:
    """
    Get district code (first 2 digits) from postal code.

    Args:
        postal_code: 6-digit postal code

    Returns:
        Two-digit district code or None
    """
    if validate_postal_code(postal_code):
        return postal_code[:2]
    return None
