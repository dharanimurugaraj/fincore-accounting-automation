import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('d:/Personal Project Freelance/vyrenzo-bank/fincore-backend/.env')
DB_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        with open('d:/Personal Project Freelance/vyrenzo-bank/fincore-backend/database/schema.sql', 'r') as f:
            sql = f.read()
            cur.execute(sql)
            print('Schema successfully applied!')
    conn.close()
except Exception as e:
    print(f'Error applying schema: {e}')
