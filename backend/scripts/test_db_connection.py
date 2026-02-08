"""Simple database connection test."""

import os
import sys
from pathlib import Path

# Add parent directory
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR.parent / ".env")
except ImportError:
    pass

# Print environment variables (masking password)
db_host = os.getenv("SUPABASE_DB_HOST")
db_port = os.getenv("SUPABASE_DB_PORT", "6543")
db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
db_user = os.getenv("SUPABASE_DB_USER")
db_password = os.getenv("SUPABASE_DB_PASSWORD")
db_sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")

print("Database Configuration:")
print(f"  Host: {db_host}")
print(f"  Port: {db_port}")
print(f"  Database: {db_name}")
print(f"  User: {db_user}")
print(f"  Password: {'*' * len(db_password) if db_password else 'NOT SET'}")
print(f"  SSL Mode: {db_sslmode}")
print()

if not all([db_host, db_user, db_password]):
    print("ERROR: Missing database credentials!")
    sys.exit(1)

# Try synchronous connection first
print("Testing synchronous connection with psycopg...")
try:
    import psycopg

    conn_string = (
        f"host={db_host} port={db_port} dbname={db_name} "
        f"user={db_user} password={db_password} sslmode={db_sslmode}"
    )

    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"[OK] Connected successfully!")
            print(f"   PostgreSQL version: {version[:50]}...")
            print()

            # Check for pgvector extension
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """)
            has_vector = cur.fetchone()[0]
            if has_vector:
                print("[OK] pgvector extension is installed")
            else:
                print("[WARN] pgvector extension not found")
            print()

            # Check for my_embeddings table
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'my_embeddings'
                )
            """)
            has_table = cur.fetchone()[0]
            if has_table:
                print("[OK] my_embeddings table exists")

                # Count retailers
                cur.execute("""
                    SELECT COUNT(*)
                    FROM my_embeddings
                    WHERE metadata->>'form_type' = 'retailer'
                """)
                count = cur.fetchone()[0]
                print(f"   Retailer count: {count}")
            else:
                print("[WARN] my_embeddings table not found")

except Exception as e:
    print(f"[ERROR] Connection failed: {e}")
    import traceback
    traceback.print_exc()
