#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
تشخيص مشكلة إضافة الصور
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
    print("🔍 تشخيص مشكلة إضافة الصور")
    print("=" * 80)
    
    # 1. التحقق من وجود جدول imagestorage
    print("\n1️⃣ التحقق من جدول imagestorage:")
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name = 'imagestorage'
    """)
    if cursor.fetchone():
        print("   ✅ الجدول موجود")
    else:
        print("   ❌ الجدول غير موجود!")
    
    # 2. التحقق من الأعمدة
    print("\n2️⃣ أعمدة جدول imagestorage:")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_name = 'imagestorage'
        ORDER BY ordinal_position
    """)
    cols = cursor.fetchall()
    if cols:
        for col_name, col_type in cols:
            print(f"   - {col_name}: {col_type}")
    
    # 3. التحقق من جدول productimages
    print("\n3️⃣ التحقق من جدول productimages:")
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name = 'productimages'
    """)
    if cursor.fetchone():
        print("   ✅ الجدول موجود")
        
        # عرض الأعمدة
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns
            WHERE table_name = 'productimages'
            ORDER BY ordinal_position
        """)
        for col_name, col_type in cursor.fetchall():
            print(f"   - {col_name}: {col_type}")
    else:
        print("   ❌ الجدول غير موجود!")
    
    # 4. عدد الصور في imagestorage
    print("\n4️⃣ عدد الصور في imagestorage:")
    cursor.execute("SELECT COUNT(*) FROM imagestorage")
    count = cursor.fetchone()[0]
    print(f"   {count} صورة")
    
    # 5. عدد الصور في productimages
    print("\n5️⃣ عدد الصور في productimages:")
    cursor.execute("SELECT COUNT(*) FROM productimages")
    count = cursor.fetchone()[0]
    print(f"   {count} صورة")
    
    # 6. عينة من productimages
    print("\n6️⃣ عينة من productimages:")
    cursor.execute("""
        SELECT imageid, productid, imagepath, imageorder 
        FROM productimages 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"   ID:{row[0]}, Product:{row[1]}, Path:{row[2]}, Order:{row[3]}")
    else:
        print("   (لا توجد صور)")
    
    cursor.close()
    conn.close()
    print("\n✅ التشخيص اكتمل بنجاح!")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
