#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Connect directly to check table names
try:
    conn = psycopg2.connect(
        host=os.getenv('DATABASE_URL_HOST', 'switchback.proxy.rlwy.net'),
        port=os.getenv('DATABASE_PORT', 5432),
        user=os.getenv('DATABASE_USER', 'postgres'),
        password=os.getenv('DATABASE_PASSWORD'),
        database=os.getenv('DATABASE_NAME', 'railway')
    )
    cursor = conn.cursor()
    
    # Get all table names
    print("=" * 60)
    print("📋 جميع الجداول في قاعدة البيانات:")
    print("=" * 60)
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 60)
    print("🔍 البحث عن جداول تتعلق بـ sellers و categories:")
    print("=" * 60)
    for table in tables:
        if 'seller' in table[0].lower() or 'categor' in table[0].lower():
            print(f"  ✅ {table[0]}")
            
            # Get column names for each relevant table
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table[0]}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            for col in columns:
                print(f"     - {col[0]} ({col[1]})")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ في الاتصال: {e}")
