import os
import psycopg2
import json
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load credentials from root .env or backend/.env
load_dotenv(".env")
load_dotenv("backend/.env")

LOCAL_DB = "postgresql://postgres:Bharadwaj2112@localhost:5432/fincore_dev"
CLOUD_DB = "postgres://208db83baa13430e5ac6e4dbea267664d695626a3906cbc16d7facf6fb24e805:sk_3h6i03MU-VWiKBTeRAE4-@db.prisma.io:5432/postgres?sslmode=require"

TABLES_ORDER = [
    "Role",
    "Organisation",
    "User",
    "PipelineRun",
    "Upload",
    "WCDLLoan",
    "ForexTransaction",
    "AgentConfig",
    "AIUsageLog",
    "FormulaConfiguration"
]

def migrate():
    print("🚀 Starting Data Migration: Local -> Cloud (JSON-Safe)")
    
    try:
        local_conn = psycopg2.connect(LOCAL_DB)
        cloud_conn = psycopg2.connect(CLOUD_DB)
        
        local_cur = local_conn.cursor(cursor_factory=RealDictCursor)
        cloud_cur = cloud_conn.cursor()

        for table in TABLES_ORDER:
            print(f"📦 Migrating table: {table}...")
            
            # 1. Fetch data from local
            local_cur.execute(f'SELECT * FROM "{table}"')
            rows = local_cur.fetchall()
            
            if not rows:
                print(f"   (No data found in {table}, skipping)")
                continue

            # 2. Get columns
            columns = rows[0].keys()
            col_list = ", ".join([f'"{c}"' for c in columns])
            placeholder_list = ", ".join(["%s"] * len(columns))

            # 4. Insert into cloud
            insert_query = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholder_list}) ON CONFLICT DO NOTHING'
            
            # Convert dictionary types to JSON strings for Postgres insertion
            # Keep lists as-is so Psycopg2 can handle them as Postgres Arrays
            data_to_insert = []
            for row in rows:
                processed_row = []
                for val in row.values():
                    if isinstance(val, dict):
                        processed_row.append(json.dumps(val))
                    else:
                        processed_row.append(val)
                data_to_insert.append(tuple(processed_row))

            cloud_cur.executemany(insert_query, data_to_insert)
            
            print(f"   ✅ Successfully migrated {len(data_to_insert)} rows to {table}.")

        cloud_conn.commit()
        print("\n✨ Migration COMPLETE. All local data is now in the Cloud!")

    except Exception as e:
        print(f"\n❌ Migration FAILED: {str(e)}")
    finally:
        if 'local_conn' in locals(): local_conn.close()
        if 'cloud_conn' in locals(): cloud_conn.close()

if __name__ == "__main__":
    migrate()
