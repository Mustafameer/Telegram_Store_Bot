#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
حذف فوري للصور والرسائل والطلبات
"""
import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# تحميل متغيرات البيئة من .env
load_dotenv()

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL not set!")
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
    print("🗑️  حذف الصور والرسائل والطلبات")
    print("=" * 80)
    
    # عرض الإحصائيات قبل الحذف
    print("\n📊 البيانات قبل الحذف:")
    
    cursor.execute("SELECT COUNT(*) FROM \"ProductImages\"")
    product_images = cursor.fetchone()[0]
    print(f"  - صور المنتجات: {product_images}")
    
    cursor.execute("SELECT COUNT(*) FROM \"ImageStorage\"")
    storage = cursor.fetchone()[0]
    print(f"  - ملفات الصور: {storage}")
    
    cursor.execute("SELECT COUNT(*) FROM \"Orders\"")
    orders = cursor.fetchone()[0]
    print(f"  - الطلبات: {orders}")
    
    cursor.execute("SELECT COUNT(*) FROM \"Messages\"")
    messages = cursor.fetchone()[0]
    print(f"  - الرسائل: {messages}")
    
    print("\n🔥 جاري الحذف...")
    
    # حذف البيانات
    cursor.execute("DELETE FROM \"Orders\"")
    d1 = cursor.rowcount
    
    cursor.execute("DELETE FROM \"Messages\"")
    d2 = cursor.rowcount
    
    cursor.execute("DELETE FROM \"ProductImages\"")
    d3 = cursor.rowcount
    
    cursor.execute("DELETE FROM \"ImageStorage\"")
    d4 = cursor.rowcount
    
    # حفظ
    conn.commit()
    
    print("\n" + "=" * 80)
    print("✅ تم الحذف بنجاح!")
    print("=" * 80)
    print(f"\n📊 ملخص الحذف:")
    print(f"  - حذف من orders: {d1}")
    print(f"  - حذف من messages: {d2}")
    print(f"  - حذف من productimages: {d3}")
    print(f"  - حذف من imagestorage: {d4}")
    print(f"  - الإجمالي: {d1 + d2 + d3 + d4}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()
