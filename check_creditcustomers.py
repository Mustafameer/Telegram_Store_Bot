#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("DATABASE_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'creditcustomers'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    print("Columns in creditcustomers table:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")
    
    # Get all data
    cursor.execute("SELECT * FROM creditcustomers ORDER BY \"SellerID\", \"FullName\"")
    
    data = cursor.fetchall()
    print(f"\nTotal records: {len(data)}")
    for row in data:
        print(f"  {row}")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
