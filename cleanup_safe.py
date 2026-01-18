#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
حذف آمن: صور المنتجات والطلبات والرسائل فقط
يقبل معامل --auto للتأكيد التلقائي
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL not set!")
    exit(1)

auto_confirm = '--auto' in sys.argv or '-y' in sys.argv

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
    print("🧹 حذف آمن: صور المنتجات والطلبات والرسائل")
    print("=" * 80)
    print("\n📌 ملاحظة: سيتم حذف البيانات التالية فقط:")
    print("  ✓ صور المنتجات (productimages)")
    print("  ✓ ملفات الصور (imagestorage)")
    print("  ✓ الطلبات (orders)")
    print("  ✓ الرسائل (messages)")
    print("\n❌ لن يتم حذف:")
    print("  ✗ المنتجات (products)")
    print("  ✗ الفئات (categories)")
    print("  ✗ البائعين (sellers)")
    print("  ✗ الزبائن (users)")
    
    # عرض الإحصائيات
    print("\n📊 الإحصائيات الحالية:")
    
    cursor.execute("SELECT COUNT(*) FROM productimages")
    product_images = cursor.fetchone()[0]
    print(f"  - صور المنتجات: {product_images}")
    
    cursor.execute("SELECT COUNT(*) FROM imagestorage")
    storage = cursor.fetchone()[0]
    print(f"  - ملفات الصور: {storage}")
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders = cursor.fetchone()[0]
    print(f"  - الطلبات: {orders}")
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    messages = cursor.fetchone()[0]
    print(f"  - الرسائل: {messages}")
    
    cursor.execute("SELECT COUNT(*) FROM products")
    products = cursor.fetchone()[0]
    print(f"\n✓ المنتجات (سيبقى): {products}")
    
    total = product_images + storage + orders + messages
    
    # طلب التأكيد إذا لم يكن تلقائياً
    if not auto_confirm:
        print(f"\n⚠️  سيتم حذف {total} سجل. هل تريد المتابعة؟")
        print("اكتب 'نعم' أو 'yes' للتأكيد:")
        response = input().strip().lower()
        
        if response not in ['نعم', 'yes', 'y']:
            print("❌ تم الإلغاء.")
            cursor.close()
            conn.close()
            exit(0)
    else:
        print(f"\n⚡ التأكيد التلقائي مفعّل - جاري الحذف ({total} سجل)...")
    
    print("\n🔥 جاري حذف البيانات...\n")
    
    # حذف الطلبات أولاً (قد تكون لديها تبعيات)
    cursor.execute("DELETE FROM orders")
    deleted_orders = cursor.rowcount
    print(f"✅ تم حذف {deleted_orders} طلب من جدول orders")
    
    # حذف الرسائل
    cursor.execute("DELETE FROM messages")
    deleted_messages = cursor.rowcount
    print(f"✅ تم حذف {deleted_messages} رسالة من جدول messages")
    
    # حذف صور المنتجات
    cursor.execute("DELETE FROM productimages")
    deleted_product_images = cursor.rowcount
    print(f"✅ تم حذف {deleted_product_images} صورة من جدول productimages")
    
    # حذف ملفات الصور
    cursor.execute("DELETE FROM imagestorage")
    deleted_storage = cursor.rowcount
    print(f"✅ تم حذف {deleted_storage} ملف من جدول imagestorage")
    
    # حفظ التغييرات
    conn.commit()
    
    total_deleted = deleted_orders + deleted_messages + deleted_product_images + deleted_storage
    
    print("\n" + "=" * 80)
    print("✅ اكتمل الحذف بنجاح!")
    print("=" * 80)
    print(f"\n📊 ملخص النتائج:")
    print(f"  - حذف من orders: {deleted_orders}")
    print(f"  - حذف من messages: {deleted_messages}")
    print(f"  - حذف من productimages: {deleted_product_images}")
    print(f"  - حذف من imagestorage: {deleted_storage}")
    print(f"  - الإجمالي المحذوف: {total_deleted}")
    print(f"\n✓ عدد المنتجات المتبقية: {products}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()
    if 'conn' in locals():
        conn.rollback()
