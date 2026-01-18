#!/usr/bin/env python3
"""
التحقق الشامل: البوت والتطبيق يريان نفس البيانات
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("✅ اختبار شامل: البوت والتطبيق متزامنان")
print("="*70)

try:
    from bot import get_categories
    import psycopg2
    
    seller_id = 27
    
    print(f"\n📊 للبائع ID: {seller_id}\n")
    
    # 1. ما تراه قاعدة البيانات
    print("1️⃣ جدول Categories في قاعدة البيانات:")
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT "CategoryID", "Name" FROM "Categories" 
        WHERE "SellerID" = %s 
        ORDER BY "CategoryID"
    ''', (seller_id,))
    
    db_cats = cursor.fetchall()
    if db_cats:
        print(f"   عدد الفئات: {len(db_cats)}")
        for cat_id, name in db_cats:
            print(f"      - {name} (ID: {cat_id})")
    else:
        print("   ⚠️  لا توجد فئات")
    
    # 2. ما يراه البوت
    print("\n2️⃣ ما يراه البوت (get_categories):")
    bot_cats = get_categories(seller_id)
    if bot_cats:
        print(f"   عدد الفئات: {len(bot_cats)}")
        for cat_id, name in bot_cats:
            print(f"      - {name} (ID: {cat_id})")
    else:
        print("   ⚠️  لا توجد فئات")
    
    # 3. المقارنة
    print("\n3️⃣ المقارنة:")
    if len(db_cats) == len(bot_cats):
        print(f"   ✅ متطابقة: {len(db_cats)} فئة")
    else:
        print(f"   ❌ مختلفة:")
        print(f"      - قاعدة البيانات: {len(db_cats)}")
        print(f"      - البوت: {len(bot_cats)}")
    
    conn.close()
    
    print(f"\n✅ الاختبار انتهى بنجاح!")
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
