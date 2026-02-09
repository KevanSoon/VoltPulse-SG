"""Climate Voucher Retailer Data Loader.

Parses the NEA Climate Vouchers retailer PDF and loads retailer data
into the vector store for semantic search and recommendations.
"""

import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import re


# Product categories from the Climate Voucher scheme
ELIGIBLE_PRODUCTS = [
    "refrigerators",
    "air_conditioners",
    "dc_fans",
    "led_lights",
    "washing_machines",
    "water_closets",
    "sink_bib_taps_mixers",
    "basin_taps_mixers",
    "shower_taps_mixers",
    "heat_pump_water_heaters"
]

# Map PDF column names to standardized keys
PRODUCT_COLUMN_MAP = {
    "Refrigerators": "refrigerators",
    "Air-conditioners": "air_conditioners",
    "Direct Current Fans": "dc_fans",
    "LED lights": "led_lights",
    "Washing Machines": "washing_machines",
    "Water Closets": "water_closets",
    "Sink/Bib taps & Mixers": "sink_bib_taps_mixers",
    "Basin Taps and Mixers": "basin_taps_mixers",
    "Shower Taps & Mixers": "shower_taps_mixers",
    "Heat Pump Water Heaters": "heat_pump_water_heaters"
}


@dataclass
class ClimateVoucherRetailer:
    """Represents a Climate Voucher participating retailer."""
    serial_number: int
    retail_outlet: str
    outlet_address: str
    postal_code: str
    website: Optional[str]
    eligible_products: List[str]
    remarks: Optional[str]

    # Derived fields
    planning_area: Optional[str] = None
    district: Optional[str] = None

    @property
    def breadth_score(self) -> float:
        """
        Pre-computed breadth score for RRF ranking.

        Returns:
            Float 0-1.5: product breadth (0-1) + website bonus (0.5)
        """
        product_score = len(self.eligible_products) / 10.0  # Max 10 products
        website_score = 0.5 if self.website and self.website != "Not available" else 0.0
        return product_score + website_score

    @property
    def postal_prefix(self) -> Optional[str]:
        """
        Get first 2 digits of postal code (Singapore district).

        Returns:
            Two-digit district code or None
        """
        if self.postal_code and len(self.postal_code) >= 2:
            return self.postal_code[:2]
        return None

    def to_embedding_text(self) -> str:
        """Generate text for SeaLion embedding."""
        products_str = ", ".join(self.eligible_products)
        text = f"""
Climate Voucher Retailer: {self.retail_outlet}
Address: {self.outlet_address}
Postal Code: {self.postal_code}
Products Available: {products_str}
Website: {self.website or 'Not available'}
Remarks: {self.remarks or 'None'}
Singapore Planning Area: {self.planning_area or 'Unknown'}
""".strip()
        return text


def extract_postal_code(address: str) -> Optional[str]:
    """Extract Singapore postal code from address."""
    # Singapore postal codes are 6 digits
    match = re.search(r'Singapore\s*(\d{6})', address, re.IGNORECASE)
    if match:
        return match.group(1)
    # Try just finding 6 consecutive digits
    match = re.search(r'\b(\d{6})\b', address)
    if match:
        return match.group(1)
    return None


def get_planning_area_from_postal(postal_code: str) -> Optional[str]:
    """Map postal code to Singapore planning area (first 2 digits)."""
    if not postal_code or len(postal_code) < 2:
        return None

    # Singapore postal district mapping (first 2 digits)
    district_map = {
        "01": "Raffles Place", "02": "Raffles Place", "03": "Raffles Place",
        "04": "Raffles Place", "05": "Raffles Place", "06": "Raffles Place",
        "07": "Anson", "08": "Anson",
        "09": "Orchard", "10": "Orchard",
        "11": "Newton", "12": "Newton", "13": "Newton",
        "14": "Bukit Timah", "15": "Bukit Timah", "16": "Bukit Timah",
        "17": "River Valley",
        "18": "Pasir Panjang", "19": "Pasir Panjang",
        "20": "Queenstown", "21": "Queenstown",
        "22": "Bukit Merah", "23": "Bukit Merah",
        "24": "Tanjong Pagar", "25": "Tanjong Pagar",
        "26": "Katong", "27": "Katong",
        "28": "Geylang", "29": "Geylang",
        "30": "Eunos", "31": "Eunos", "32": "Eunos",
        "33": "Bedok", "34": "Bedok", "35": "Bedok", "36": "Bedok",
        "37": "Changi", "38": "Changi",
        "39": "Pasir Ris", "40": "Pasir Ris",
        "41": "Tampines",
        "42": "Loyang",
        "43": "Hougang", "44": "Hougang", "45": "Hougang",
        "46": "Serangoon", "47": "Serangoon", "48": "Serangoon",
        "49": "Sengkang", "50": "Sengkang", "51": "Sengkang",
        "52": "Bishan",
        "53": "Ang Mo Kio", "54": "Ang Mo Kio", "55": "Ang Mo Kio", "56": "Ang Mo Kio",
        "57": "Yishun", "58": "Yishun", "59": "Yishun", "60": "Yishun",
        "61": "Sembawang", "62": "Sembawang", "63": "Sembawang",
        "64": "Woodlands", "65": "Woodlands", "66": "Woodlands",
        "67": "Kranji", "68": "Kranji",
        "69": "Lim Chu Kang", "70": "Lim Chu Kang", "71": "Lim Chu Kang",
        "72": "Jurong East", "73": "Jurong East",
        "75": "Jurong West", "76": "Jurong West",
        "77": "Bukit Batok", "78": "Bukit Batok",
        "79": "Choa Chu Kang",
        "80": "Bukit Panjang",
        "81": "Clementi", "82": "Clementi",
    }

    prefix = postal_code[:2]
    return district_map.get(prefix)


def parse_retailer_from_row(row_data: Dict[str, Any]) -> ClimateVoucherRetailer:
    """Parse a single row from the PDF into a ClimateVoucherRetailer."""
    # Extract eligible products (columns with "Y" value)
    eligible_products = []
    for col_name, product_key in PRODUCT_COLUMN_MAP.items():
        if row_data.get(col_name) == "Y":
            eligible_products.append(product_key)

    # Extract postal code and planning area
    address = row_data.get("Outlet Address", "")
    postal_code = extract_postal_code(address)
    planning_area = get_planning_area_from_postal(postal_code) if postal_code else None

    return ClimateVoucherRetailer(
        serial_number=int(row_data.get("S/N", 0)),
        retail_outlet=row_data.get("Retail Outlet", "Unknown"),
        outlet_address=address,
        postal_code=postal_code or "",
        website=row_data.get("Website") if row_data.get("Website") not in ["-", ""] else None,
        eligible_products=eligible_products,
        remarks=row_data.get("Remarks") if row_data.get("Remarks") else None,
        planning_area=planning_area,
        district=postal_code[:2] if postal_code else None
    )


def parse_retailers_from_structured_data(data: List[Dict[str, Any]]) -> List[ClimateVoucherRetailer]:
    """Parse structured data (from PDF extraction) into retailer objects."""
    retailers = []
    for row in data:
        try:
            retailer = parse_retailer_from_row(row)
            if retailer.retail_outlet and retailer.retail_outlet != "Unknown":
                retailers.append(retailer)
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    return retailers


# Pre-parsed retailer data from the PDF (sample - you would load full data)
# This can be populated by running the PDF through a parser like PyMuPDF or pdfplumber
SAMPLE_RETAILERS_DATA = [
    {
        "S/N": 1,
        "Retail Outlet": "1 PR (Macpherson Road)",
        "Outlet Address": "401 Macpherson Road, #03-19, Singapore 368125",
        "Website": "https://www.facebook.com/1PRPTELTD/",
        "Refrigerators": None,
        "Air-conditioners": None,
        "Direct Current Fans": "Y",
        "LED lights": None,
        "Washing Machines": None,
        "Water Closets": "Y",
        "Sink/Bib taps & Mixers": "Y",
        "Basin Taps and Mixers": "Y",
        "Shower Taps & Mixers": "Y",
        "Heat Pump Water Heaters": None,
        "Remarks": "By Appointment"
    },
    {
        "S/N": 36,
        "Retail Outlet": "Audio House Marketing (Audio House Building)",
        "Outlet Address": "23 Ubi Road 4, #01-01, Singapore 408620",
        "Website": "https://audiohouse.com.sg/",
        "Refrigerators": "Y",
        "Air-conditioners": "Y",
        "Direct Current Fans": None,
        "LED lights": "Y",
        "Washing Machines": "Y",
        "Water Closets": None,
        "Sink/Bib taps & Mixers": None,
        "Basin Taps and Mixers": None,
        "Shower Taps & Mixers": None,
        "Heat Pump Water Heaters": None,
        "Remarks": None
    },
    {
        "S/N": 350,
        "Retail Outlet": "Gain City (Ang Mo Kio Showroom)",
        "Outlet Address": "8 Ang Mo Kio Industrial Park 2, Singapore 569500",
        "Website": "https://www.gaincity.com/",
        "Refrigerators": "Y",
        "Air-conditioners": "Y",
        "Direct Current Fans": "Y",
        "LED lights": "Y",
        "Washing Machines": "Y",
        "Water Closets": "Y",
        "Sink/Bib taps & Mixers": "Y",
        "Basin Taps and Mixers": "Y",
        "Shower Taps & Mixers": "Y",
        "Heat Pump Water Heaters": "Y",
        "Remarks": "Accepts vouchers upon delivery"
    },
    {
        "S/N": 58,
        "Retail Outlet": "Best Denki (Bedok Mall)",
        "Outlet Address": "311 New Upper Changi Road, #B1-01/43/44, Singapore 467360",
        "Website": "https://www.bestdenki.com.sg/",
        "Refrigerators": "Y",
        "Air-conditioners": "Y",
        "Direct Current Fans": None,
        "LED lights": "Y",
        "Washing Machines": "Y",
        "Water Closets": None,
        "Sink/Bib taps & Mixers": None,
        "Basin Taps and Mixers": None,
        "Shower Taps & Mixers": None,
        "Heat Pump Water Heaters": "Y",
        "Remarks": None
    },
    {
        "S/N": 120,
        "Retail Outlet": "Courts (Ang Mo Kio)",
        "Outlet Address": "730 Ang Mo Kio Ave 6, #1,2-, Singapore 560730",
        "Website": "https://www.courts.com.sg/",
        "Refrigerators": "Y",
        "Air-conditioners": "Y",
        "Direct Current Fans": None,
        "LED lights": "Y",
        "Washing Machines": "Y",
        "Water Closets": None,
        "Sink/Bib taps & Mixers": None,
        "Basin Taps and Mixers": None,
        "Shower Taps & Mixers": None,
        "Heat Pump Water Heaters": None,
        "Remarks": None
    }
]


async def load_retailers_to_vector_store(
    encoder,
    vector_store,
    retailers_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Load retailer data into the vector store.

    Args:
        encoder: SeaLion encoder instance
        vector_store: VectorStore instance
        retailers_data: Optional list of retailer dictionaries.
                       If None, uses SAMPLE_RETAILERS_DATA.

    Returns:
        Summary of loading operation
    """
    data = retailers_data or SAMPLE_RETAILERS_DATA
    retailers = parse_retailers_from_structured_data(data)

    loaded = 0
    errors = []

    for retailer in retailers:
        try:
            # Generate embedding text
            text = retailer.to_embedding_text()

            # Create embedding using SeaLion
            embedding = await encoder.encode(text)

            # Generate unique ID
            retailer_id = f"retailer_{retailer.serial_number}_{uuid.uuid4().hex[:8]}"

            # Prepare form data with full retailer info
            form_data = {
                **asdict(retailer),
                "source_type": "climate_voucher_retailer",
                "country": "SG",
                "embedding_text": text
            }

            # Store in vector store
            await vector_store.store_embedding(
                form_id=retailer_id,
                form_type="retailer",
                embedding=embedding,
                form_data=form_data
            )

            loaded += 1
            print(f"Loaded retailer: {retailer.retail_outlet}")

        except Exception as e:
            errors.append({
                "retailer": retailer.retail_outlet,
                "error": str(e)
            })

    return {
        "total_processed": len(retailers),
        "loaded": loaded,
        "errors": errors
    }


async def load_from_pdf_text(
    pdf_text: str,
    encoder,
    vector_store
) -> Dict[str, Any]:
    """Parse retailer data from raw PDF text and load into vector store.

    This is a simplified parser - for production, use pdfplumber or PyMuPDF
    with proper table extraction.

    Args:
        pdf_text: Raw text extracted from PDF
        encoder: SeaLion encoder
        vector_store: VectorStore instance

    Returns:
        Loading summary
    """
    # Simple line-by-line parsing (placeholder for more sophisticated extraction)
    # In production, you'd use pdfplumber.extract_tables() or similar

    lines = pdf_text.strip().split('\n')
    retailers_data = []

    # Parse tabular data (this is simplified - real implementation needs table detection)
    current_entry = {}

    for line in lines:
        # Skip header lines
        if 'S/N' in line and 'Retail Outlet' in line:
            continue

        # Try to parse as a data row
        # This would need proper CSV/table parsing logic
        pass

    return await load_retailers_to_vector_store(encoder, vector_store, retailers_data)