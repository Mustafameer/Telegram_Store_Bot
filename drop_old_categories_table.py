#!/usr/bin/env python3
"""
حذف جدول categories القديم والاحتفاظ فقط بـ Categories
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🗑️ حذف جدول categories القديم")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # قبل الحذف - التحقق
    print("\n📊 قبل الحذف:")
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename ILIKE '%categor%'
        ORDER BY tablename
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"   الجداول الموجودة: {tables}")
    
    # حذف الجدول القديم
    print("\n🗑️ جاري حذف جدول 'categories'...")
    cursor.execute('DROP TABLE IF EXISTS "categories" CASCADE')
    conn.commit()
    print("   ✅ تم حذفه")
    
    # بعد الحذف - التحقق
    print("\n📊 بعد الحذف:")
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename ILIKE '%categor%'
        ORDER BY tablename
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"   الجداول الموجودة: {tables}")
    
    # التحقق من البيانات في Categories
    print("\n✅ التحقق من جدول 'Categories':")
    cursor.execute('SELECT COUNT(*) FROM "Categories"')
    count = cursor.fetchone()[0]
    print(f"   عدد الفئات: {count}")
    
    if count > 0:
        cursor.execute('SELECT "CategoryID", "Name" FROM "Categories" LIMIT 5')
        rows = cursor.fetchall()
        for cat_id, name in rows:
            print(f"      - ID: {cat_id}, Name: {name}")
    
    conn.close()
    print("\n✅ انتهت العملية بنجاح!")
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
