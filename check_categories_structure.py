#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from bot import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

try:
    # Check what columns exist in Categories table
    print("=" * 60)
    print("🏗️ هيكل جدول Categories:")
    print("=" * 60)
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'Categories'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
    
    print("\n" + "=" * 60)
    print("📦 البيانات الموجودة حالياً:")
    print("=" * 60)
    cursor.execute('SELECT * FROM "Categories"')
    
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  {row}")
    else:
        print("  ❌ لا توجد بيانات")
            
finally:
    cursor.close()
    conn.close()
