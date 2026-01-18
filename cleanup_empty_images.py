#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
حذف الصور ذات imagepath الفارغة من قاعدة البيانات
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
    print("🗑️ حذف الصور ذات imagepath الفارغة")
    print("=" * 80)
    
    # البحث عن الصور الفارغة
    cursor.execute("""
        SELECT COUNT(*) FROM productimages 
        WHERE imagepath IS NULL OR imagepath = ''
    """)
    count = cursor.fetchone()[0]
    print(f"\nعدد الصور ذات imagepath الفارغة: {count}")
    
    if count == 0:
        print("✅ لا توجد صور فارغة!")
    else:
        # عرض الصور الفارغة قبل الحذف
        print("\n📝 الصور التي سيتم حذفها:")
        cursor.execute("""
            SELECT imageid, productid, imageorder 
            FROM productimages 
            WHERE imagepath IS NULL OR imagepath = ''
            ORDER BY productid, imageid
        """)
        for image_id, product_id, order in cursor.fetchall():
            print(f"  - Image ID: {image_id}, Product: {product_id}, Order: {order}")
        
        # تأكيد الحذف
        response = input("\n⚠️ هل تريد حذف هذه الصور؟ (نعم/لا): ")
        if response.lower() in ['نعم', 'yes', 'y']:
            # حذف الصور الفارغة
            cursor.execute("""
                DELETE FROM productimages 
                WHERE imagepath IS NULL OR imagepath = ''
            """)
            conn.commit()
            deleted = cursor.rowcount
            print(f"\n✅ تم حذف {deleted} صورة فارغة بنجاح!")
        else:
            print("\nتم الإلغاء.")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
