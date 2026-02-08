"""Diagnostic script to check retailer data in the vector database.

This script checks:
1. Number of retailers in the database
2. Data quality (fields, embeddings)
3. Sample retailer records
4. Planning area distribution
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
    load_dotenv(BACKEND_DIR.parent / ".env")
except ImportError:
    pass


async def diagnose():
    """Run diagnostic checks on retailer data."""
    print("=" * 80)
    print("RETAILER RECOMMENDATION SYSTEM DIAGNOSTIC")
    print("=" * 80)
    print()

    # Initialize database connection
    print("[1/6] Connecting to database...")
    try:
        from psycopg_pool import AsyncConnectionPool

        db_host = os.getenv("SUPABASE_DB_HOST")
        db_port = os.getenv("SUPABASE_DB_PORT", "6543")
        db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        db_user = os.getenv("SUPABASE_DB_USER")
        db_password = os.getenv("SUPABASE_DB_PASSWORD")
        db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

        if not all([db_host, db_user, db_password]):
            print("❌ FAILED: Missing database credentials")
            print("   Please set SUPABASE_DB_* environment variables in .env")
            return

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
        print("✅ Database connection established")
        print()

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return

    # Check if my_embeddings table exists
    print("[2/6] Checking if my_embeddings table exists...")
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_name='my_embeddings'
                """)
                result = await cur.fetchone()
                if result:
                    print("✅ Table my_embeddings exists")
                else:
                    print("❌ Table my_embeddings does NOT exist")
                    await pool.close()
                    return
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        await pool.close()
        return

    # Count retailers
    print("[3/6] Counting retailers in database...")
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Count by form_type
                await cur.execute("""
                    SELECT
                        metadata->>'form_type' as form_type,
                        COUNT(*) as count
                    FROM my_embeddings
                    GROUP BY metadata->>'form_type'
                    ORDER BY count DESC
                """)
                rows = await cur.fetchall()

                retailer_count = 0
                print("   Form types in database:")
                for row in rows:
                    form_type, count = row
                    print(f"     - {form_type}: {count}")
                    if form_type == "retailer":
                        retailer_count = count

                if retailer_count == 0:
                    print()
                    print("⚠️  WARNING: No retailers found in database!")
                    print("   You need to load retailer data (Phase 3)")
                elif retailer_count < 775:
                    print()
                    print(f"⚠️  PARTIAL: Only {retailer_count} retailers (expected 775)")
                    print("   Consider loading full dataset for better results")
                else:
                    print()
                    print(f"✅ Full dataset loaded: {retailer_count} retailers")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        await pool.close()
        return

    if retailer_count == 0:
        print("Skipping remaining checks (no retailer data)")
        await pool.close()
        return

    # Sample retailer records
    print("[4/6] Checking sample retailer records...")
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT
                        source_id,
                        text_content,
                        metadata,
                        (embedding IS NOT NULL) as has_embedding
                    FROM my_embeddings
                    WHERE metadata->>'form_type' = 'retailer'
                    LIMIT 5
                """)
                rows = await cur.fetchall()

                print(f"   Showing {len(rows)} sample retailers:")
                for i, row in enumerate(rows, 1):
                    source_id, text_content, metadata, has_embedding = row

                    # Parse JSON (might already be parsed by psycopg3)
                    if isinstance(text_content, str):
                        try:
                            data = json.loads(text_content)
                        except:
                            data = {}
                    else:
                        data = text_content or {}

                    retailer_name = data.get('retail_outlet', 'Unknown')
                    address = data.get('outlet_address', 'Unknown')
                    planning_area = data.get('planning_area', 'N/A')
                    products = data.get('eligible_products', [])

                    print(f"\n   #{i} {retailer_name}")
                    print(f"       Address: {address[:60]}...")
                    print(f"       Planning Area: {planning_area}")
                    print(f"       Products: {len(products)} types")
                    print(f"       Has Embedding: {'✅' if has_embedding else '❌'}")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Check data completeness
    print("[5/6] Analyzing data completeness...")
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT
                        COUNT(*) as total_retailers,
                        COUNT(CASE WHEN text_content::jsonb->>'retail_outlet' IS NOT NULL THEN 1 END) as with_name,
                        COUNT(CASE WHEN text_content::jsonb->>'outlet_address' IS NOT NULL THEN 1 END) as with_address,
                        COUNT(CASE WHEN text_content::jsonb->>'planning_area' IS NOT NULL THEN 1 END) as with_planning_area,
                        COUNT(CASE WHEN text_content::jsonb->>'website' IS NOT NULL THEN 1 END) as with_website,
                        COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embedding
                    FROM my_embeddings
                    WHERE metadata->>'form_type' = 'retailer'
                """)
                row = await cur.fetchone()

                if row:
                    total, with_name, with_address, with_area, with_website, with_embedding = row

                    print(f"   Total retailers: {total}")
                    print(f"   With name: {with_name}/{total} ({100*with_name//total}%)")
                    print(f"   With address: {with_address}/{total} ({100*with_address//total}%)")
                    print(f"   With planning area: {with_area}/{total} ({100*with_area//total}%)")
                    print(f"   With website: {with_website}/{total} ({100*with_website//total}%)")
                    print(f"   With embedding: {with_embedding}/{total} ({100*with_embedding//total}%)")

                    if with_embedding < total:
                        print()
                        print(f"   ⚠️  WARNING: {total - with_embedding} retailers missing embeddings!")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Check planning area distribution
    print("[6/6] Checking planning area distribution...")
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT
                        text_content::jsonb->>'planning_area' as planning_area,
                        COUNT(*) as count
                    FROM my_embeddings
                    WHERE metadata->>'form_type' = 'retailer'
                    GROUP BY planning_area
                    ORDER BY count DESC
                    LIMIT 10
                """)
                rows = await cur.fetchall()

                print("   Top 10 planning areas by retailer count:")
                for area, count in rows:
                    print(f"     - {area or 'Unknown'}: {count} retailers")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Close connection
    await pool.close()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
