"""Script to load Climate Voucher retailers from PDF into vector store.

Usage:
    python scripts/load_retailers_from_pdf.py path/to/retailers.pdf

Or programmatically:
    from scripts.load_retailers_from_pdf import load_pdf_to_vectorstore
    await load_pdf_to_vectorstore("path/to/retailers.pdf")
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Windows async fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass


async def init_services():
    """Initialize encoder, database, and vector store."""
    from encoders.sealion import SeaLionEncoder
    from recommender.vector_store import VectorStore
    from psycopg_pool import AsyncConnectionPool

    # Initialize encoder
    encoder = SeaLionEncoder()
    print("[OK] SeaLion encoder initialized")

    # Build connection string
    db_host = os.getenv("SUPABASE_DB_HOST")
    db_port = os.getenv("SUPABASE_DB_PORT", "6543")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_user = os.getenv("SUPABASE_DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

    if not all([db_host, db_user, db_password]):
        raise ValueError("Missing database credentials. Set SUPABASE_DB_* environment variables.")

    conn_string = (
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        f"?sslmode={db_sslmode}"
    )

    pool = AsyncConnectionPool(
        conninfo=conn_string,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": None},
    )
    await pool.open()
    print("[OK] Database connection established")

    vector_store = VectorStore(pool)

    return encoder, vector_store, pool


def parse_pdf_to_retailers(pdf_path: str) -> list:
    """Parse PDF and extract retailer data.

    Args:
        pdf_path: Path to the Climate Voucher retailers PDF

    Returns:
        List of retailer dictionaries
    """
    try:
        import pdfplumber
    except ImportError:
        print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
        sys.exit(1)

    retailers = []
    seen_serials = set()

    # Column headers we're looking for
    product_columns = [
        "Refrigerators", "Air-conditioners", "Direct Current Fans",
        "LED lights", "Washing Machines", "Water Closets",
        "Sink/Bib taps & Mixers", "Basin Taps and Mixers",
        "Shower Taps & Mixers", "Heat Pump Water Heaters"
    ]

    print(f"\nParsing PDF: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")

        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  Processing page {page_num}/{len(pdf.pages)}...", end="\r")

            # Extract tables from page
            tables = page.extract_tables()

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Find header row
                header_row = None
                header_idx = -1
                for i, row in enumerate(table):
                    if row and any("S/N" in str(cell) for cell in row if cell):
                        header_row = row
                        header_idx = i
                        break

                if header_idx < 0:
                    continue

                # Build column index map
                col_map = {}
                for col_idx, cell in enumerate(header_row):
                    if cell:
                        cell_str = str(cell).strip()
                        if "S/N" in cell_str:
                            col_map["S/N"] = col_idx
                        elif "Retail Outlet" in cell_str:
                            col_map["Retail Outlet"] = col_idx
                        elif "Outlet Address" in cell_str:
                            col_map["Outlet Address"] = col_idx
                        elif "Website" in cell_str:
                            col_map["Website"] = col_idx
                        elif "Remarks" in cell_str:
                            col_map["Remarks"] = col_idx
                        else:
                            # Check product columns
                            for prod in product_columns:
                                if prod.lower() in cell_str.lower():
                                    col_map[prod] = col_idx
                                    break

                # Parse data rows
                for row in table[header_idx + 1:]:
                    if not row or not any(row):
                        continue

                    # Get serial number
                    sn_idx = col_map.get("S/N", 0)
                    if sn_idx >= len(row) or not row[sn_idx]:
                        continue

                    try:
                        # Extract serial number
                        sn_val = str(row[sn_idx]).strip()
                        import re
                        sn_match = re.search(r'\d+', sn_val)
                        if not sn_match:
                            continue
                        serial = int(sn_match.group())

                        if serial in seen_serials or serial == 0:
                            continue
                        seen_serials.add(serial)

                        # Helper to get cell value
                        def get_cell(col_name, default=None):
                            idx = col_map.get(col_name)
                            if idx is not None and idx < len(row):
                                val = row[idx]
                                if val and str(val).strip() not in ["", "-", "None"]:
                                    return str(val).strip()
                            return default

                        # Build retailer data
                        retailer = {
                            "S/N": serial,
                            "Retail Outlet": get_cell("Retail Outlet", "Unknown"),
                            "Outlet Address": get_cell("Outlet Address", ""),
                            "Website": get_cell("Website"),
                            "Remarks": get_cell("Remarks"),
                        }

                        # Product eligibility
                        for prod in product_columns:
                            val = get_cell(prod)
                            retailer[prod] = "Y" if val and val.upper() == "Y" else None

                        # Only add if we have a valid retailer name
                        if retailer["Retail Outlet"] and retailer["Retail Outlet"] != "Unknown":
                            retailers.append(retailer)

                    except Exception as e:
                        continue

    print(f"\n[OK] Parsed {len(retailers)} retailers from PDF")
    return retailers


async def load_pdf_to_vectorstore(pdf_path: str, batch_size: int = 10):
    """Load retailers from PDF into vector store.

    Args:
        pdf_path: Path to the Climate Voucher retailers PDF
        batch_size: Number of retailers to process before showing progress
    """
    # Parse PDF
    retailers_data = parse_pdf_to_retailers(pdf_path)

    if not retailers_data:
        print("ERROR: No retailers parsed from PDF")
        return

    # Initialize services
    print("\nInitializing services...")
    encoder, vector_store, pool = await init_services()

    # Load retailers
    print(f"\nLoading {len(retailers_data)} retailers into vector store...")

    from services.retailer_loader import load_retailers_to_vector_store

    result = await load_retailers_to_vector_store(
        encoder=encoder,
        vector_store=vector_store,
        retailers_data=retailers_data
    )

    # Cleanup
    await pool.close()

    # Print results
    print("\n" + "=" * 60)
    print("LOADING COMPLETE")
    print("=" * 60)
    print(f"  Total processed: {result['total_processed']}")
    print(f"  Successfully loaded: {result['loaded']}")
    print(f"  Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for err in result['errors'][:10]:  # Show first 10 errors
            print(f"  - {err['retailer']}: {err['error']}")
        if len(result['errors']) > 10:
            print(f"  ... and {len(result['errors']) - 10} more errors")

    return result


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python load_retailers_from_pdf.py <path_to_pdf>")
        print("\nExample:")
        print("  python scripts/load_retailers_from_pdf.py data/retailers.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    await load_pdf_to_vectorstore(pdf_path)


if __name__ == "__main__":
    asyncio.run(main())
