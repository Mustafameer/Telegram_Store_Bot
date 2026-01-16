#!/usr/bin/env python3
"""
Check what tables exist in the PostgreSQL database
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
    
    # Get all table names
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    print(f"\n📊 Tables in database ({len(tables)} total):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check for ImageStorage specifically
    if any('image' in t[0].lower() for t in tables):
        print("\n✅ Image-related tables found")
        for table in tables:
            if 'image' in table[0].lower():
                print(f"  - {table[0]}")
    else:
        print("\n❌ No image-related tables found")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
