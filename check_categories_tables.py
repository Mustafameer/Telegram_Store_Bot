#!/usr/bin/env python3
"""
التحقق من جميع الجداول المتعلقة بالفئات
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 البحث عن جميع جداول الفئات في PostgreSQL")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # البحث عن جميع الجداول
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename
    """)
    
    all_tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📊 جميع الجداول ({len(all_tables)}):")
    for table in all_tables:
        print(f"   - {table}")
    
    # البحث عن جداول تحتوي على "categor"
    print(f"\n🔎 جداول تحتوي على 'categor':")
    category_tables = [t for t in all_tables if 'categor' in t.lower()]
    
    if not category_tables:
        print("   ❌ لا توجد جداول")
    else:
        for table in category_tables:
            print(f"\n   📋 {table}:")
            cursor.execute(f"""
                SELECT column_name, data_type FROM information_schema.columns 
                WHERE table_name='{table}' 
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            for col_name, col_type in columns:
                print(f"      - {col_name}: {col_type}")
            
            # عدد الصفوف
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"      📊 عدد الصفوف: {count}")
            
            # عرض البيانات
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                rows = cursor.fetchall()
                print(f"      📝 عينة البيانات (أول 5):")
                for row in rows:
                    print(f"         {row}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
