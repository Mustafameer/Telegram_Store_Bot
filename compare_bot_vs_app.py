#!/usr/bin/env python3
"""
مقارنة بين ما يراه البوت والتطبيق من البيانات
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 مقارنة البيانات بين البوت والتطبيق")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # اختبار البائع
    seller_id = 27
    
    print(f"\n📊 للبائع ID: {seller_id}\n")
    
    # 1. جدول Categories (ما يراه التطبيق)
    print("1️⃣ جدول Categories (يستخدمه التطبيق):")
    cursor.execute('''
        SELECT "CategoryID", "SellerID", "Name", "OrderIndex", "ImagePath" 
        FROM "Categories" 
        WHERE "SellerID" = %s 
        ORDER BY "CategoryID"
    ''', (seller_id,))
    
    categories_app = cursor.fetchall()
    if categories_app:
        print(f"   عدد الفئات: {len(categories_app)}")
        for cat_id, sel_id, name, order_idx, img_path in categories_app:
            print(f"      - ID:{cat_id}, Name:'{name}', OrderIndex:{order_idx}")
    else:
        print("   ⚠️  لا توجد فئات")
    
    # 2. جدول categories (القديم)
    print("\n2️⃣ جدول categories (القديم - يمكن يستخدمه البوت):")
    cursor.execute('''
        SELECT COUNT(*) FROM "categories"
    ''')
    count_old = cursor.fetchone()[0]
    print(f"   عدد الصفوف الكلي: {count_old}")
    
    if count_old > 0:
        cursor.execute('''
            SELECT categoryid, sellerid, name 
            FROM "categories" 
            WHERE sellerid = %s 
            ORDER BY categoryid
        ''', (seller_id,))
        categories_old = cursor.fetchall()
        if categories_old:
            print(f"   للبائع {seller_id}:")
            for cat_id, sel_id, name in categories_old:
                print(f"      - ID:{cat_id}, Name:'{name}'")
        else:
            print(f"   لا توجد فئات للبائع {seller_id}")
    
    # 3. اختبار دالة get_categories من البوت
    print("\n3️⃣ نتيجة get_categories من البوت:")
    from bot import get_categories
    
    bot_categories = get_categories(seller_id)
    if bot_categories:
        print(f"   عدد الفئات: {len(bot_categories)}")
        for cat_id, name in bot_categories:
            print(f"      - ID:{cat_id}, Name:'{name}'")
    else:
        print("   ⚠️  لا توجد فئات")
    
    # 4. مقارنة
    print("\n🔄 المقارنة:")
    if len(categories_app) == len(bot_categories):
        print(f"   ✅ العدد متطابق: {len(categories_app)}")
    else:
        print(f"   ❌ العدد مختلف:")
        print(f"      - التطبيق يرى: {len(categories_app)}")
        print(f"      - البوت يرى: {len(bot_categories)}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
