#!/usr/bin/env python3
"""
اختبار ما يراه التطبيق من البيانات بأسماء الأعمدة الجديدة
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 التحقق من البيانات بأسماء الأعمدة الجديدة")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Check Categories
    print("\n📋 جدول Categories:")
    cursor.execute('SELECT "CategoryID", "SellerID", "Name" FROM "Categories" ORDER BY "CategoryID"')
    categories = cursor.fetchall()
    
    if categories:
        print(f"   ✅ عدد الفئات: {len(categories)}")
        for cat_id, seller_id, name in categories:
            print(f"      - {name} (ID: {cat_id}, SellerID: {seller_id})")
    else:
        print("   ⚠️  لا توجد فئات")
    
    # Check Products
    print("\n📦 جدول Products:")
    cursor.execute('SELECT "ProductID", "SellerID", "CategoryID", "Name" FROM "Products" LIMIT 5')
    products = cursor.fetchall()
    
    if products:
        print(f"   ✅ عدد المنتجات (عرض 5): {len(products)}")
        for prod_id, seller_id, cat_id, name in products:
            print(f"      - {name} (ID: {prod_id}, SellerID: {seller_id}, CategoryID: {cat_id})")
    else:
        print("   ⚠️  لا توجد منتجات")
    
    # Check overall count
    cursor.execute('SELECT COUNT(*) FROM "Products"')
    total_products = cursor.fetchone()[0]
    print(f"\n   📊 إجمالي المنتجات: {total_products}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
