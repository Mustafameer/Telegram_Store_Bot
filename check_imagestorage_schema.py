#!/usr/bin/env python3
"""
Check the schema of the imagestorage table
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("✅ Connected to PostgreSQL")
    
    # Get column information for imagestorage table
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'imagestorage'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    print("\n📋 imagestorage table schema:")
    for col_name, data_type, nullable in columns:
        nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
        print(f"  - {col_name}: {data_type} ({nullable_str})")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
