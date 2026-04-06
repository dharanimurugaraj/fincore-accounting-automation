
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Production URL from the user
DATABASE_URL = "postgres://208db83baa13430e5ac6e4dbea267664d695626a3906cbc16d7facf6fb24e805:sk_3h6i03MU-VWiKBTeRAE4-@db.prisma.io:5432/postgres?sslmode=require"

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def seed():
    conn = get_conn()
    cur = conn.cursor()
    
    print("🌱 Seeding production roles...")
    roles = [
        (0, 'SUPER_ADMIN', 'Platform-wide total access', '{*}'),
        (1, 'ADMIN', 'Organization-level administration', '{*}'),
        (2, 'ANALYST', 'Standard organization user', '{Dashboard,Upload,Documents,Reports,"WCDL Tracker","Forex Register",Activity}'),
        (3, 'VIEWER', 'Read-only organization access', '{Dashboard,Reports}'),
        (4, 'PENDING_APPROVAL', 'User awaiting administrator confirmation', '{}'),
    ]
    
    for r in roles:
        cur.execute('''
            INSERT INTO "Role" (id, name, description, "allowedPages")
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                "allowedPages" = EXCLUDED."allowedPages"
        ''', r)
    
    print("✅ Roles seeded.")
    
    print("🌱 Seeding default organisation...")
    cur.execute('''
        INSERT INTO "Organisation" (id, name, "legalName", departments)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    ''', ('default-org', 'Vyrenzo Bank Demo', 'Vyrenzo Financial Services Ltd.', ['Investment Banking', 'Asset Management', 'Operations']))
    
    print("✅ Default organisation seeded.")
    
    conn.commit()
    cur.close()
    conn.close()
    print("🚀 Production seeding complete.")

if __name__ == "__main__":
    seed()
