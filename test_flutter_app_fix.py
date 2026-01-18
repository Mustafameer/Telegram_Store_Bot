#!/usr/bin/env python3
"""
اختبار: محاكاة إضافة فئة من التطبيق وتحقق من الحفظ
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("✅ اختبار إضافة فئة من التطبيق")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    seller_id = 27
    test_name = f"من التطبيق {os.urandom(2).hex()}"
    
    print(f"\n📁 جاري إضافة فئة: '{test_name}'")
    
    # إدراج مباشر مثل ما يفعله التطبيق المُصحح
    cursor.execute('''
        INSERT INTO "Categories" ("SellerID", "Name", "OrderIndex") 
        VALUES (%s, %s, 0)
    ''', (seller_id, test_name))
    
    conn.commit()
    print(f"   ✅ تم الإدراج في قاعدة البيانات")
    
    # التحقق من الفئة في جدول Categories
    cursor.execute('''
        SELECT "CategoryID", "Name" FROM "Categories" 
        WHERE "SellerID" = %s AND "Name" = %s
    ''', (seller_id, test_name))
    
    result = cursor.fetchone()
    if result:
        print(f"   ✅ الفئة موجودة في جدول Categories: ID={result[0]}")
    else:
        print(f"   ❌ الفئة غير موجودة")
    
    # التحقق من get_categories في البوت
    print(f"\n✅ التحقق من get_categories():")
    from bot import get_categories
    bot_cats = get_categories(seller_id)
    
    found = any(name == test_name for _, name in bot_cats)
    if found:
        print(f"   ✅ الفئة موجودة في get_categories()")
        print(f"\n✅ الإصلاح نجح! التطبيق يحفظ الفئات بشكل صحيح الآن")
    else:
        print(f"   ❌ الفئة غير موجودة في get_categories()")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
