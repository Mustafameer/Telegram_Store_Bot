#!/usr/bin/env python3
"""
التحقق من جميع جداول الفئات والبيانات
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 التحقق من جميع جداول الفئات")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # البحث عن جميع الجداول
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename ILIKE '%categor%'
        ORDER BY tablename
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📋 الجداول الموجودة:")
    for table in tables:
        print(f"   - {table}")
    
    # عرض البيانات من كل جدول
    for table in tables:
        print(f"\n📊 جدول '{table}':")
        
        cursor.execute(f'SELECT * FROM "{table}"')
        rows = cursor.fetchall()
        
        cursor.execute(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='{table}' ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        print(f"   الأعمدة: {columns}")
        print(f"   عدد الصفوف: {len(rows)}")
        
        if rows:
            print(f"   البيانات:")
            for row in rows:
                print(f"      {row}")
        else:
            print(f"   ⚠️  الجدول فارغ")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
