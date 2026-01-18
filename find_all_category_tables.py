#!/usr/bin/env python3
"""
البحث عن جميع جداول الفئات المحتملة
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 البحث عن جميع الجداول المتعلقة بـ Category/categories")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # البحث عن جميع الجداول التي تحتوي على "categor"
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename ILIKE '%categor%'
        ORDER BY tablename
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print("❌ لم نجد جداول تحتوي على 'categor'")
    else:
        print(f"\n📋 الجداول المتطابقة ({len(tables)}):")
        
        for table in tables:
            print(f"\n   📊 جدول: '{table}'")
            
            # أعمدة الجدول
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='{table}' 
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            print(f"      الأعمدة:")
            for col_name, col_type in columns:
                print(f"         - {col_name}: {col_type}")
            
            # عدد الصفوف
            cursor.execute(f"SELECT COUNT(*) FROM \"{table}\"")
            count = cursor.fetchone()[0]
            print(f"      📊 عدد الصفوف: {count}")
            
            if count > 0:
                # عرض البيانات
                cursor.execute(f"SELECT * FROM \"{table}\" LIMIT 3")
                rows = cursor.fetchall()
                print(f"      📝 عينة البيانات:")
                for row in rows:
                    print(f"         {row}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
