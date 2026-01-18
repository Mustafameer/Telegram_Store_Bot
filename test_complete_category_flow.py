#!/usr/bin/env python3
"""
اختبار شامل: إضافة فئة والتحقق من ظهورها في التطبيق
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("✅ اختبار شامل لإضافة الفئات")
print("="*70)

try:
    from bot import add_category, get_categories, get_seller_by_telegram
    import psycopg2
    
    # الحصول على البائع
    seller = get_seller_by_telegram(999999999)
    if not seller:
        print("❌ لم نجد البائع")
        sys.exit(1)
    
    seller_id = seller[0]
    print(f"\n✅ البائع موجود: ID={seller_id}, Name={seller[3]}")
    
    # إضافة فئة جديدة
    test_cat_name = f"فئة اختبار {os.urandom(2).hex()}"
    print(f"\n📁 جاري إضافة الفئة: '{test_cat_name}'")
    
    add_category(seller_id, test_cat_name)
    
    # التحقق من أن الفئة في جدول Categories
    print(f"\n🔍 التحقق من جدول Categories:")
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    cursor.execute('SELECT "CategoryID", "Name" FROM "Categories" WHERE "SellerID" = %s ORDER BY "CategoryID" DESC LIMIT 1', (seller_id,))
    latest = cursor.fetchone()
    
    if latest and latest[1] == test_cat_name:
        print(f"   ✅ الفئة موجودة في جدول Categories: ID={latest[0]}, Name='{latest[1]}'")
    else:
        print(f"   ❌ الفئة غير موجودة في جدول Categories")
    
    # التحقق من جدول categories (القديم)
    print(f"\n🔍 التحقق من جدول categories (القديم):")
    cursor.execute('SELECT COUNT(*) FROM "categories"')
    count = cursor.fetchone()[0]
    print(f"   عدد الصفوف: {count}")
    
    # الآن التحقق من get_categories (للبوت)
    print(f"\n🔍 اختبار get_categories (دالة البوت):")
    categories = get_categories(seller_id)
    if categories:
        print(f"   ✅ get_categories أرجعت {len(categories)} فئة:")
        for cat_id, cat_name in categories:
            print(f"      - {cat_name} (ID: {cat_id})")
    else:
        print(f"   ❌ get_categories لم ترجع أي فئات")
    
    conn.close()
    
    print(f"\n✅ الاختبار انتهى بنجاح!")
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
