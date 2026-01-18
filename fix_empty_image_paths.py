#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص جدول productimages للتحقق من imagepath الفارغة
"""
import os
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("DATABASE_URL not set!")
    exit(1)

try:
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 فحص جدول productimages للصور ذات imagepath الفارغة")
    print("=" * 80)
    
    # 1. عدد الصور الإجمالي
    cursor.execute("SELECT COUNT(*) FROM productimages")
    total = cursor.fetchone()[0]
    print(f"\n📊 إجمالي الصور في productimages: {total}")
    
    # 2. الصور ذات imagepath الفارغة
    cursor.execute("SELECT COUNT(*) FROM productimages WHERE imagepath IS NULL OR imagepath = ''")
    empty = cursor.fetchone()[0]
    print(f"❌ عدد الصور ذات imagepath الفارغة: {empty}")
    
    if empty > 0:
        print("\n🔴 تم العثور على صور ذات imagepath فارغة!")
        print("📝 عينة من الصور الفارغة:")
        cursor.execute("""
            SELECT imageid, productid, imagepath, imageorder 
            FROM productimages 
            WHERE imagepath IS NULL OR imagepath = '' 
            LIMIT 10
        """)
        for image_id, product_id, image_path, order in cursor.fetchall():
            print(f"  - ID: {image_id}, Product: {product_id}, Path: '{image_path}', Order: {order}")
        
        # محاولة إصلاح الصور الفارغة
        print("\n🔧 محاولة إصلاح الصور الفارغة...")
        cursor.execute("""
            DELETE FROM productimages 
            WHERE imagepath IS NULL OR imagepath = ''
        """)
        conn.commit()
        deleted = cursor.rowcount
        print(f"✅ تم حذف {deleted} صورة فارغة من قاعدة البيانات")
    else:
        print("✅ جميع الصور لديها imagepath صحيح")
    
    # 3. عرض عينة من الصور الصحيحة
    print("\n📸 عينة من الصور الصحيحة:")
    cursor.execute("""
        SELECT imageid, productid, imagepath, imageorder 
        FROM productimages 
        WHERE imagepath IS NOT NULL AND imagepath != '' 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    if rows:
        for image_id, product_id, image_path, order in rows:
            print(f"  - ID: {image_id}, Product: {product_id}, Path: {image_path}, Order: {order}")
    else:
        print("  (لا توجد صور صحيحة)")
    
    cursor.close()
    conn.close()
    print("\n✅ الفحص اكتمل!")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
