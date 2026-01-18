#!/usr/bin/env python3
"""
التحقق من أسماء الأعمدة الدقيقة في جدول Categories
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 أسماء الأعمدة الدقيقة في جدول Categories")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # قائمة الجداول
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename ILIKE '%categor%'
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📋 الجداول المطابقة:")
    for table in tables:
        print(f"\n   📊 جدول: '{table}'")
        
        # أسماء الأعمدة الدقيقة
        cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='{table}' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        for col_name, col_type in columns:
            print(f"      - {col_name} ({col_type})")
        
        # عدد الصفوف
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"      📊 عدد الصفوف: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
