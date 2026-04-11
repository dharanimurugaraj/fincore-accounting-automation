import psycopg2
import sys
import os
from dotenv import load_dotenv

# Load local environment
load_dotenv("backend/.env")
DB_URL = os.getenv("DATABASE_URL")

def init_local_db():
    print(f"Connecting to Local DB: {DB_URL}")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("Creating 'GlobalConfig' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "GlobalConfig" (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Local DB Sync Complete.")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_local_db()
