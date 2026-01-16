#!/usr/bin/env python3
"""
اختبار: التحقق من أن صور المنتجات تُسترجع بشكل صحيح من ProductImages
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

import psycopg2
from psycopg2.extras import RealDictCursor

print("\n" + "="*70)
print("🔍 اختبار استرجاع الصور من ProductImages")
print("="*70)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# الحصول على أحدث منتج من متجر مفتوح
cursor.execute("""
    SELECT p.ProductID, p.Name, p.Price, s.StoreName
    FROM Products p
    JOIN Sellers s ON p.SellerID = s.SellerID
    WHERE s.RequireCustomerRegistration = 0 AND p.Status = 'active'
    ORDER BY p.ProductID DESC
    LIMIT 1
""")

product = cursor.fetchone()
if not product:
    print("❌ لا توجد منتجات في المتاجر المفتوحة!")
    conn.close()
    exit(1)

product_id = product['productid']
print(f"\n✅ المنتج: PID={product_id} | {product['name']} | {product['storename']}")
print(f"   السعر: {product['price']}")

# استرجاع الصور من ProductImages (نفس ما تفعله send_product_with_image)
print(f"\n🔄 استرجاع الصور من ProductImages:")
cursor.execute("""
    SELECT imageid, imagepath, imageorder
    FROM ProductImages
    WHERE productid = %s
    ORDER BY imageorder
""", (product_id,))

images = cursor.fetchall()
if images:
    print(f"✅ وجدت {len(images)} صورة:")
    for img in images:
        filename = img['imagepath']
        print(f"   - ImageOrder:{img['imageorder']} | Filename:{filename}")
        
        # استرجاع الصورة من ImageStorage
        cursor.execute("""
            SELECT filename, LENGTH(filedata) as size, updatedat
            FROM ImageStorage
            WHERE filename = %s
        """, (filename,))
        
        storage = cursor.fetchone()
        if storage:
            print(f"     ✅ موجودة في ImageStorage: {storage['size']} bytes (آخر تحديث: {storage['updatedat']})")
        else:
            print(f"     ❌ غير موجودة في ImageStorage!")
else:
    print(f"❌ لا توجد صور للمنتج في ProductImages!")

conn.close()
print("\n" + "="*70 + "\n")
