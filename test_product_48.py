#!/usr/bin/env python3
"""
اختبار المنتج الذي تم إنشاؤه مؤخراً
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
print("🔍 اختبار المنتج PID:48 (تلفزيون 55 بوصة)")
print("="*70)

# الحصول على تفاصيل المنتج
cursor.execute("""
    SELECT p.*, s.StoreName, s.RequireCustomerRegistration
    FROM Products p
    JOIN Sellers s ON p.SellerID = s.SellerID
    WHERE p.ProductID = 48
""")

product = cursor.fetchone()
if product:
    print(f"\n✅ المنتج موجود:")
    print(f"   ProductID: {product['productid']}")
    print(f"   StoreName: {product['storename']}")
    print(f"   Name: {product['name']}")
    print(f"   Price: {product['price']}")
    print(f"   Quantity: {product['quantity']}")
    print(f"   ImagePath: '{product['imagepath']}'")
    print(f"   Status: {product['status']}")
    print(f"   CreatedAt: {product['createdat']}")
    print(f"   RequireCustomerRegistration: {product['requirecustomerregistration']}")
    
    # تفاصيل ProductImages
    print(f"\n📸 جدول ProductImages:")
    cursor.execute("""
        SELECT ImageID, ImagePath, ImageOrder
        FROM ProductImages
        WHERE ProductID = 48
        ORDER BY ImageOrder
    """)
    
    images = cursor.fetchall()
    if images:
        print(f"   ✅ وجد {len(images)} صورة:")
        for img in images:
            print(f"      - ImageID:{img['imageid']} | ImagePath:{img['imagepath']} | Order:{img['imageorder']}")
    else:
        print(f"   ❌ لا توجد صور في ProductImages!")
    
    # تفاصيل ImageStorage
    if product['imagepath']:
        print(f"\n💾 جدول ImageStorage:")
        cursor.execute("""
            SELECT FileName, LENGTH(FileData) as size, UpdatedAt
            FROM ImageStorage
            WHERE FileName = %s
        """, (product['imagepath'],))
        
        storage = cursor.fetchone()
        if storage:
            print(f"   ✅ الملف موجود: {storage['filename']} ({storage['size']} bytes)")
        else:
            print(f"   ❌ الملف غير موجود في ImageStorage!")
else:
    print("❌ المنتج PID:48 غير موجود!")

conn.close()
print("\n" + "="*70 + "\n")
