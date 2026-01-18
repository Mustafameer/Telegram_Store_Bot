#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
حذف جميع الصور والطلبات والرسائل من قاعدة البيانات السحابية
⚠️ تحذير: هذا سيحذف جميع البيانات بشكل دائم!
"""
import os
import psycopg2
from urllib.parse import urlparse

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
    print("⚠️  تحذير: سيتم حذف جميع الصور والطلبات والرسائل بشكل دائم!")
    print("=" * 80)
    
    # عرض الإحصائيات الحالية
    print("\n📊 الإحصائيات الحالية:")
    
    cursor.execute("SELECT COUNT(*) FROM productimages")
    product_images_count = cursor.fetchone()[0]
    print(f"  - صور المنتجات (productimages): {product_images_count} صورة")
    
    cursor.execute("SELECT COUNT(*) FROM imagestorage")
    image_storage_count = cursor.fetchone()[0]
    print(f"  - تخزين الصور (imagestorage): {image_storage_count} ملف")
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders_count = cursor.fetchone()[0]
    print(f"  - الطلبات (orders): {orders_count} طلب")
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    messages_count = cursor.fetchone()[0]
    print(f"  - الرسائل (messages): {messages_count} رسالة")
    
    total_records = product_images_count + image_storage_count + orders_count + messages_count
    print(f"\n📌 إجمالي السجلات التي سيتم حذفها: {total_records}")
    
    # طلب التأكيد
    print("\n⚠️  هل تريد متابعة الحذف؟")
    print("اكتب 'نعم' أو 'yes' للتأكيد (أي شيء آخر سيلغي العملية):")
    response = input().strip().lower()
    
    if response not in ['نعم', 'yes', 'y']:
        print("\n❌ تم إلغاء العملية.")
        cursor.close()
        conn.close()
        exit(0)
    
    print("\n🔥 جاري حذف البيانات...")
    
    # حذف الطلبات (قد تكون لديها تبعيات)
    print("  - حذف الطلبات...")
    cursor.execute("DELETE FROM orders")
    deleted_orders = cursor.rowcount
    print(f"    ✅ تم حذف {deleted_orders} طلب")
    
    # حذف الرسائل
    print("  - حذف الرسائل...")
    cursor.execute("DELETE FROM messages")
    deleted_messages = cursor.rowcount
    print(f"    ✅ تم حذف {deleted_messages} رسالة")
    
    # حذف صور المنتجات
    print("  - حذف صور المنتجات...")
    cursor.execute("DELETE FROM productimages")
    deleted_product_images = cursor.rowcount
    print(f"    ✅ تم حذف {deleted_product_images} صورة منتج")
    
    # حذف تخزين الصور
    print("  - حذف تخزين الصور...")
    cursor.execute("DELETE FROM imagestorage")
    deleted_image_storage = cursor.rowcount
    print(f"    ✅ تم حذف {deleted_image_storage} ملف صورة")
    
    # حفظ التغييرات
    conn.commit()
    
    print("\n" + "=" * 80)
    print("✅ تم حذف جميع البيانات بنجاح!")
    print("=" * 80)
    print(f"\n📊 ملخص الحذف:")
    print(f"  - صور المنتجات: {deleted_product_images}")
    print(f"  - ملفات الصور: {deleted_image_storage}")
    print(f"  - الطلبات: {deleted_orders}")
    print(f"  - الرسائل: {deleted_messages}")
    print(f"  - الإجمالي: {deleted_product_images + deleted_image_storage + deleted_orders + deleted_messages}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    if conn:
        conn.rollback()
