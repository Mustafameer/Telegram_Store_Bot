#!/usr/bin/env python3
"""
اختبار تحديث صورة المنتج
يتحقق من أن الصورة الجديدة تُحفظ بشكل صحيح في ProductImages و imagestorage
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if not IS_POSTGRES:
    print("❌ DATABASE_URL غير مضبوط - SQLite فقط")
    sys.exit(1)

import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("""
╔════════════════════════════════════════════════════════════════╗
║       🔍 اختبار تحديث صورة المنتج                             ║
╚════════════════════════════════════════════════════════════════╝
""")

# 1️⃣ اختبر آخر منتج تم إضافته
print("\n📊 1️⃣ آخر المنتجات المضافة:")
cursor.execute("""
    SELECT productid, name, imagepath, createdat
    FROM products
    ORDER BY productid DESC LIMIT 5
""")
products = cursor.fetchall()

for p in products:
    print(f"\n  • PID:{p['productid']} | {p['name']}")
    print(f"    ImagePath: {p['imagepath']}")
    print(f"    Created: {p['createdat']}")
    
    # تحقق من الصور المرتبطة
    cursor.execute("""
        SELECT imageid, imagepath, imageorder, updatedat
        FROM productimages
        WHERE productid = %s
        ORDER BY imageorder, imageid
    """, (p['productid'],))
    
    images = cursor.fetchall()
    if images:
        print(f"    📸 الصور المرتبطة ({len(images)}):")
        for img in images:
            print(f"       - ImageID:{img['imageid']} | {img['imagepath']} | Order:{img['imageorder']}")
            
            # تحقق من وجود الصورة في imagestorage
            cursor.execute("""
                SELECT filename, LENGTH(filedata) as size, updatedat
                FROM imagestorage
                WHERE filename = %s
            """, (img['imagepath'],))
            
            storage = cursor.fetchone()
            if storage:
                print(f"         ✅ في imagestorage ({storage['size']} bytes)")
            else:
                print(f"         ❌ ليست في imagestorage")
    else:
        print(f"    ⚠️  لا توجد صور مرتبطة")

# 2️⃣ إحصائيات عامة
print("\n\n📊 2️⃣ الإحصائيات العامة:")
cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE imagepath IS NOT NULL AND imagepath != ''")
result = cursor.fetchone()
print(f"\n✅ المنتجات التي بها imagepath: {result['cnt']}")

cursor.execute("""
    SELECT COUNT(*) as cnt
    FROM products p
    WHERE EXISTS (SELECT 1 FROM productimages pi WHERE pi.productid = p.productid)
""")
result = cursor.fetchone()
print(f"✅ المنتجات التي بها صور في ProductImages: {result['cnt']}")

cursor.execute("SELECT COUNT(*) as cnt FROM imagestorage")
result = cursor.fetchone()
print(f"✅ إجمالي الصور في ImageStorage: {result['cnt']}")

# 3️⃣ التحقق من التطابق
print("\n\n📊 3️⃣ التحقق من التطابق بين الجداول:")
cursor.execute("""
    SELECT COUNT(*) as cnt
    FROM productimages pi
    WHERE EXISTS (SELECT 1 FROM imagestorage storage WHERE storage.filename = pi.imagepath)
""")
result = cursor.fetchone()
matched = result['cnt']

cursor.execute("SELECT COUNT(*) as cnt FROM productimages")
result = cursor.fetchone()
total = result['cnt']

print(f"\n✅ الصور المرتبطة التي موجودة في ImageStorage: {matched}/{total}")

if matched == total and total > 0:
    print("\n✅✅✅ جميع الصور متطابقة ومحفوظة بشكل صحيح!")
elif total == 0:
    print("\n⏳ لا توجد صور مضافة حتى الآن")
else:
    missing = total - matched
    print(f"\n⚠️ {missing} صورة مفقودة من ImageStorage")

# 4️⃣ إحصائيات الصور الحديثة
print("\n\n📊 4️⃣ آخر الصور المضافة/المحدثة:")
cursor.execute("""
    SELECT filename, updatedat, LENGTH(filedata) as size
    FROM imagestorage
    ORDER BY updatedat DESC LIMIT 5
""")
results = cursor.fetchall()

for img in results:
    print(f"\n  • {img['filename']}")
    print(f"    Size: {img['size']} bytes")
    print(f"    Updated: {img['updatedat']}")

conn.close()

print("\n" + "="*62 + "\n")
