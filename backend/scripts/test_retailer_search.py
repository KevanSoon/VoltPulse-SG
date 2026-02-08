"""Test retailer search directly without RAG agent."""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Windows async fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR.parent / ".env")
except ImportError:
    pass


async def test_retailer_search():
    """Test retailer search tools directly."""
    print("=" * 80)
    print("TESTING RETAILER RECOMMENDATION SYSTEM")
    print("=" * 80)
    print()

    # Initialize services
    print("[1/4] Initializing services...")
    try:
        from encoders.sealion import SeaLionEncoder
        from recommender.vector_store import VectorStore
        from tools.retailer_tools import set_retailer_dependencies
        from psycopg_pool import AsyncConnectionPool

        # Initialize encoder
        encoder = SeaLionEncoder()
        print(f"  [OK] SeaLion encoder initialized (dim: {encoder.embedding_dimension})")

        # Initialize database pool
        db_host = os.getenv("SUPABASE_DB_HOST")
        db_port = os.getenv("SUPABASE_DB_PORT", "6543")
        db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        db_user = os.getenv("SUPABASE_DB_USER")
        db_password = os.getenv("SUPABASE_DB_PASSWORD")
        db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

        conn_string = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            f"?sslmode={db_sslmode}"
        )

        pool = AsyncConnectionPool(
            conninfo=conn_string,
            max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": None},
        )
        await pool.open()
        vector_store = VectorStore(pool)
        print("  [OK] Vector store initialized")

        # Set dependencies for retailer tools
        set_retailer_dependencies(encoder, vector_store)
        print("  [OK] Retailer tools configured")
        print()

    except Exception as e:
        print(f"  [ERROR] Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 1: Search for refrigerators
    print("[2/4] Test 1: Search for refrigerators")
    try:
        from tools.retailer_tools import search_climate_voucher_retailers

        query = "refrigerator shops in Singapore"
        print(f"  Query: \"{query}\"")
        print("  Encoding query...")

        # Encode the query
        embedding = await encoder.encode(query)
        print(f"  Embedding shape: {embedding.shape}")

        # Search in vector store
        print("  Searching vector store...")
        results = await vector_store.find_similar(
            query_embedding=embedding,
            form_type="retailer",
            limit=10
        )

        print(f"  Found {len(results)} retailers")
        print()
        print("  Top 5 results:")
        for i, result in enumerate(results[:5], 1):
            data = result.form_data
            name = data.get('retail_outlet', 'Unknown')
            area = data.get('planning_area', 'Unknown')
            products = data.get('eligible_products', [])
            score = result.score

            print(f"    {i}. {name}")
            print(f"       Area: {area}")
            print(f"       Products: {len(products)} categories")
            print(f"       Similarity: {score:.4f}")
            print()

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Search for air conditioners in Bedok
    print("[3/4] Test 2: Search for air conditioners in Bedok")
    try:
        query = "air conditioner shops in Bedok Singapore"
        print(f"  Query: \"{query}\"")

        embedding = await encoder.encode(query)
        results = await vector_store.find_similar(
            query_embedding=embedding,
            form_type="retailer",
            limit=20
        )

        # Filter by planning area and product
        bedok_results = [
            r for r in results
            if 'bedok' in r.form_data.get('planning_area', '').lower()
            and 'air_conditioners' in r.form_data.get('eligible_products', [])
        ]

        print(f"  Found {len(results)} total results")
        print(f"  Filtered to {len(bedok_results)} Bedok air conditioner retailers")
        print()
        print("  Top 3 filtered results:")
        for i, result in enumerate(bedok_results[:3], 1):
            data = result.form_data
            name = data.get('retail_outlet', 'Unknown')
            address = data.get('outlet_address', 'Unknown')
            score = result.score

            print(f"    {i}. {name}")
            print(f"       Address: {address[:60]}...")
            print(f"       Similarity: {score:.4f}")
            print()

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Find all retailers selling LED lights
    print("[4/4] Test 3: Find retailers selling LED lights")
    try:
        # Get all retailers
        all_retailers = await vector_store.find_by_form_type("retailer", limit=500)

        # Filter by LED lights
        led_retailers = [
            r for r in all_retailers
            if 'led_lights' in r.form_data.get('eligible_products', [])
        ]

        print(f"  Total retailers in DB: {len(all_retailers)}")
        print(f"  Retailers with LED lights: {len(led_retailers)}")
        print()
        print("  Sample LED retailers:")
        for i, result in enumerate(led_retailers[:5], 1):
            data = result.form_data
            name = data.get('retail_outlet', 'Unknown')
            area = data.get('planning_area', 'Unknown')
            website = data.get('website', 'No website')

            print(f"    {i}. {name}")
            print(f"       Area: {area}")
            print(f"       Website: {website}")
            print()

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    await pool.close()
    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_retailer_search())
