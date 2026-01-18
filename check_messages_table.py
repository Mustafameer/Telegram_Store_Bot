#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    print(f"Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check messages table specifically
    print("\n--- Looking for messages table ---")
    for table in tables:
        if 'message' in table[0].lower():
            print(f"Found: {table[0]}")
            
            # Get columns
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table[0],))
            
            cols = cur.fetchall()
            print(f"Columns in {table[0]}:")
            for col in cols:
                print(f"  - {col[0]}")
            
            # Get count
            cur.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
            count = cur.fetchone()[0]
            print(f"Total records: {count}")
    
    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
