#!/usr/bin/env python3
"""
اختبار عملية رفع المنتج والصور عند الإضافة عبر البوت
تحقق من:
1. حفظ الصورة في imagestorage
2. إضافة الصورة في productimages
3. تطابق الأسماء بين الجداول
"""

import os
import sys
import time
import uuid
from dotenv import load_dotenv

load_dotenv()

# استيراد المتغيرات
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # اتصال PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("✅ Connected to PostgreSQL")
else:
    print("❌ DATABASE_URL not set - SQLite only")
    sys.exit(1)

try:
    # 1️⃣ اختبر جدول imagestorage
    print("\n📊 === اختبار جدول imagestorage ===")
    cursor.execute("SELECT COUNT(*) as cnt FROM imagestorage")
    result = cursor.fetchone()
    print(f"📈 عدد الصور المحفوظة في السحابة: {result['cnt']}")
    
    # اعرض آخر 5 صور
    cursor.execute("SELECT filename, updatedat FROM imagestorage ORDER BY updatedat DESC LIMIT 5")
    results = cursor.fetchall()
    print("\n📸 آخر الصور المرفوعة:")
    for row in results:
        print(f"  • {row['filename']} - {row['updatedat']}")
    
    # 2️⃣ اختبر جدول productimages
    print("\n📊 === اختبار جدول productimages ===")
    cursor.execute("SELECT COUNT(*) as cnt FROM productimages")
    result = cursor.fetchone()
    print(f"📈 عدد الصور المرتبطة بالمنتجات: {result['cnt']}")
    
    # اعرض آخر 5 ربطات
    cursor.execute("""
        SELECT pi.imageid, pi.productid, pi.imagepath, p.name as product_name
        FROM productimages pi
        LEFT JOIN products p ON pi.productid = p.productid
        ORDER BY pi.imageid DESC LIMIT 5
    """)
    results = cursor.fetchall()
    print("\n🔗 آخر الصور المرتبطة بالمنتجات:")
    for row in results:
        print(f"  • ID:{row['imageid']} | PID:{row['productid']} | {row['product_name']} | {row['imagepath']}")
    
    # 3️⃣ تحقق من التطابق بين الجداول
    print("\n📊 === التحقق من التطابق ===")
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM productimages pi
        WHERE EXISTS (SELECT 1 FROM imagestorage storage WHERE storage.filename = pi.imagepath)
    """)
    result = cursor.fetchone()
    matched_count = result['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM productimages")
    result = cursor.fetchone()
    total_count = result['cnt']
    
    print(f"\n🔍 تطابق أسماء الملفات:")
    print(f"  • إجمالي الصور المرتبطة بالمنتجات: {total_count}")
    print(f"  • الصور الموجودة في imagestorage: {matched_count}")
    
    if matched_count == total_count and total_count > 0:
        print("\n✅ جميع الصور متطابقة ومحفوظة بشكل صحيح!")
    elif total_count == 0:
        print("\n⏳ لا توجد صور مضافة حتى الآن - انتظر إضافة منتج!")
    else:
        missing = total_count - matched_count
        print(f"\n⚠️ {missing} صورة مفقودة من imagestorage")
    
    # 4️⃣ معلومات عامة
    print("\n📊 === الملخص ===")
    cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE imagepath != '' AND imagepath IS NOT NULL")
    result = cursor.fetchone()
    print(f"📦 المنتجات التي بها صور في imagepath: {result['cnt']}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM products p WHERE EXISTS (SELECT 1 FROM productimages pi WHERE pi.productid = p.productid)")
    result = cursor.fetchone()
    print(f"📦 المنتجات التي بها صور في productimages: {result['cnt']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    cursor.close()
    conn.close()
    print("\n✅ الاتصال مغلق")
