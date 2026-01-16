#!/usr/bin/env python3
"""
اختبار شامل: التحقق من أن open store products لديها صور الآن
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if not IS_POSTGRES:
    print("❌ DATABASE_URL غير موجود")
    exit(1)

import psycopg2
from psycopg2.extras import RealDictCursor

print("\n" + "="*70)
print("🔍 اختبار شامل: Open Store Products والصور")
print("="*70)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# 1. الإحصائيات الكاملة
print("\n📊 الإحصائيات الكاملة:")
cursor.execute("""
    SELECT 
        COUNT(DISTINCT s.SellerID) as total_sellers,
        COUNT(DISTINCT CASE WHEN s.RequireCustomerRegistration = 0 THEN s.SellerID END) as open_stores,
        COUNT(DISTINCT CASE WHEN s.RequireCustomerRegistration = 1 THEN s.SellerID END) as closed_stores
    FROM Sellers s
""")

stats = cursor.fetchone()
print(f"   إجمالي المتاجر: {stats['total_sellers']}")
print(f"   متاجر مفتوحة: {stats['open_stores']}")
print(f"   متاجر مقفولة: {stats['closed_stores']}")

# 2. المنتجات والصور
print("\n📊 المنتجات والصور:")
cursor.execute("""
    SELECT 
        COUNT(DISTINCT p.ProductID) as total_products,
        COUNT(DISTINCT CASE WHEN s.RequireCustomerRegistration = 0 THEN p.ProductID END) as open_store_products,
        COUNT(DISTINCT CASE WHEN s.RequireCustomerRegistration = 1 THEN p.ProductID END) as closed_store_products,
        COUNT(DISTINCT pi.ImageID) as total_images
    FROM Products p
    JOIN Sellers s ON p.SellerID = s.SellerID
    LEFT JOIN ProductImages pi ON p.ProductID = pi.ProductID
""")

prod_stats = cursor.fetchone()
print(f"   إجمالي المنتجات: {prod_stats['total_products']}")
print(f"   منتجات متاجر مفتوحة: {prod_stats['open_store_products']}")
print(f"   منتجات متاجر مقفولة: {prod_stats['closed_store_products']}")
print(f"   إجمالي الصور: {prod_stats['total_images']}")

# 3. تفاصيل منتجات الـ Open Store
print("\n📊 تفاصيل منتجات المتاجر المفتوحة:")
cursor.execute("""
    SELECT 
        s.SellerID,
        s.StoreName,
        s.RequireCustomerRegistration,
        COUNT(DISTINCT p.ProductID) as product_count,
        COUNT(DISTINCT pi.ImageID) as image_count,
        SUM(CASE WHEN pi.ImageID IS NOT NULL THEN 1 ELSE 0 END) as products_with_images,
        SUM(CASE WHEN pi.ImageID IS NULL THEN 1 ELSE 0 END) as products_without_images
    FROM Sellers s
    LEFT JOIN Products p ON s.SellerID = p.SellerID AND p.Status = 'active'
    LEFT JOIN ProductImages pi ON p.ProductID = pi.ProductID
    WHERE s.RequireCustomerRegistration = 0
    GROUP BY s.SellerID, s.StoreName, s.RequireCustomerRegistration
    ORDER BY s.SellerID
""")

open_stores = cursor.fetchall()
for store in open_stores:
    print(f"\n   🏪 SellerID:{store['sellerid']} | {store['storename']}")
    print(f"      المنتجات: {store['product_count']}")
    print(f"      الصور الإجمالية: {store['image_count']}")
    if store['product_count'] and store['product_count'] > 0:
        print(f"      منتجات بصور: {store['products_with_images']}/{store['product_count']}")
        if store['products_without_images']:
            print(f"      ⚠️ منتجات بدون صور: {store['products_without_images']}")

# 4. المنتجات بدون صور في جداول Sellers/Products
print("\n\n📊 المنتجات بدون صور في open stores:")
cursor.execute("""
    SELECT 
        p.ProductID,
        p.Name,
        s.StoreName,
        p.ImagePath,
        COUNT(pi.ImageID) as image_count
    FROM Products p
    JOIN Sellers s ON p.SellerID = s.SellerID
    LEFT JOIN ProductImages pi ON p.ProductID = pi.ProductID
    WHERE s.RequireCustomerRegistration = 0 AND p.Status = 'active'
    GROUP BY p.ProductID, p.Name, s.StoreName, p.ImagePath
    HAVING COUNT(pi.ImageID) = 0
    ORDER BY p.ProductID DESC
    LIMIT 5
""")

missing_images = cursor.fetchall()
if missing_images:
    print(f"   ❌ وجدت {len(missing_images)} منتج بدون صور:")
    for prod in missing_images:
        print(f"      - PID:{prod['productid']} | {prod['name']} | {prod['storename']}")
        print(f"        ImagePath: '{prod['imagepath']}'")
else:
    print(f"   ✅ جميع منتجات المتاجر المفتوحة لديها صور!")

conn.close()
print("\n" + "="*70 + "\n")
