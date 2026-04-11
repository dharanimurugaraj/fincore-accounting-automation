import psycopg2
import sys

# Production Neon Connection String provided by user
CONN_STR = "postgresql://neondb_owner:npg_DtVbwo3HG5eR@ep-proud-pine-ansyb2t9.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def check_prod_db():
    print("Connecting to Production DB...")
    try:
        conn = psycopg2.connect(CONN_STR)
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM "GlobalConfig"')
        count = cur.fetchone()[0]
        print(f"Success: 'GlobalConfig' table exists with {count} records.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_prod_db()
