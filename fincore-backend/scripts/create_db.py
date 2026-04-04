import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    conn = psycopg2.connect("postgresql://postgres:Bharadwaj2112@localhost:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE fincore_dev")
        print("Database 'fincore_dev' created successfully!")
    conn.close()
except psycopg2.errors.DuplicateDatabase:
    print("Database 'fincore_dev' already exists.")
except Exception as e:
    print(f"Error creating database: {e}")
