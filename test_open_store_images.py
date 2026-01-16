#!/usr/bin/env python3
"""
اختبار سريع: المنتجات والصور المفتوحة
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if not IS_POSTGRES:
    print("❌ DATABASE_URL غير موجود")
    exit(1)

import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("\n" + "="*70)
print("🔍 اختبار المتاجر المفتوحة والصور")
print("="*70)

# 1. المتاجر المفتوحة
print("\n📊 1️⃣ المتاجر المفتوحة:")
cursor.execute("""
    SELECT *
    FROM Sellers
    ORDER BY CreatedAt DESC
    LIMIT 10
""")

sellers = cursor.fetchall()
if sellers:
    for seller in sellers:
        seller_id = seller['sellerid']
        store_name = seller['storename']
        # حقل RequireCustomerRegistration 
        is_open = seller['requirecustomerregistration'] == 0
        
        status = '🟢 Open' if is_open else '🔴 Closed'
        print(f"\n  🏪 SellerID:{seller_id} | {store_name} | {status}")
        
        # المنتجات
        cursor.execute("""
            SELECT productid, name, imagepath, quantity
            FROM Products
            WHERE sellerid = %s AND status = 'active'
            ORDER BY productid DESC
            LIMIT 3
        """, (seller_id,))
        
        products = cursor.fetchall()
        if products:
            for prod in products:
                print(f"    📦 PID:{prod['productid']} | {prod['name']} | Qty:{prod['quantity']}")
                print(f"       ImagePath: {prod['imagepath']}")
                
                # تحقق من ProductImages
                cursor.execute("""
                    SELECT imageid, imagepath
                    FROM ProductImages
                    WHERE productid = %s
                """, (prod['productid'],))
                
                images = cursor.fetchall()
                if images:
                    for img in images:
                        print(f"       ✅ ProductImages: {img['imagepath']}")
                        
                        # تحقق من ImageStorage
                        cursor.execute("""
                            SELECT filename, LENGTH(filedata) as size
                            FROM ImageStorage
                            WHERE filename = %s
                        """, (img['imagepath'],))
                        
                        storage = cursor.fetchone()
                        if storage:
                            print(f"          ✅ ImageStorage: {storage['filename']} ({storage['size']} bytes)")
                        else:
                            print(f"          ❌ ImageStorage: الملف غير موجود!")
                else:
                    print(f"       ⚠️ بدون صور في ProductImages")
        else:
            print(f"    ⚠️ بدون منتجات")
else:
    print("  ⚠️ لا توجد متاجر مفتوحة")

# 2. ملخص سريع
print("\n\n📊 2️⃣ الإحصائيات:")
cursor.execute("""
    SELECT COUNT(*) as cnt
    FROM Sellers
    WHERE RequireCustomerRegistration = 0
""")
result = cursor.fetchone()
print(f"\n✅ عدد المتاجر المفتوحة: {result['cnt']}")

cursor.execute("""
    SELECT COUNT(*) as cnt
    FROM Products p
    JOIN Sellers s ON p.SellerID = s.SellerID
    WHERE s.RequireCustomerRegistration = 0 AND p.Status = 'active'
""")
result = cursor.fetchone()
print(f"✅ منتجات من متاجر مفتوحة: {result['cnt']}")

cursor.execute("""
    SELECT COUNT(*) as cnt
    FROM ProductImages pi
    JOIN Products p ON pi.ProductID = p.ProductID
    JOIN Sellers s ON p.SellerID = s.SellerID
    WHERE s.RequireCustomerRegistration = 0
""")
result = cursor.fetchone()
print(f"✅ صور من منتجات متاجر مفتوحة: {result['cnt']}")

# 3. جدول ملخص
print("\n\n📊 3️⃣ ملخص تفصيلي:")
cursor.execute("""
    SELECT s.SellerID, s.StoreName, s.RequireCustomerRegistration,
           COUNT(DISTINCT p.ProductID) as product_count,
           COUNT(DISTINCT pi.ImageID) as image_count
    FROM Sellers s
    LEFT JOIN Products p ON s.SellerID = p.SellerID AND p.Status = 'active'
    LEFT JOIN ProductImages pi ON p.ProductID = pi.ProductID
    GROUP BY s.SellerID, s.StoreName, s.RequireCustomerRegistration
    ORDER BY s.RequireCustomerRegistration DESC, s.SellerID
""")

results = cursor.fetchall()
for row in results:
    store_type = '🟢 مفتوح' if row['requirecustomerregistration'] == 0 else '🔴 مقفول'
    print(f"{row['sellerid']:3} | {row['storename']:20} | {store_type} | المنتجات: {row['product_count']:2} | الصور: {row['image_count']:2}")

conn.close()
print("\n" + "="*70 + "\n")
