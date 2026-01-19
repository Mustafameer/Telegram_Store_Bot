#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محاكاة عملية شراء كاملة من التطبيق:
1. جلب منتج
2. جلب صوره
3. إضافة معاملة ائتمانية
4. تحديث الكمية
5. حذف الصور
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# استيراد دوال البوت
sys.path.insert(0, os.path.dirname(__file__))
from bot import (
    get_db_connection, 
    get_product_by_id, 
    get_product_images,
    add_credit_transaction,
    IS_POSTGRES
)

def simulate_purchase():
    """محاكاة عملية شراء"""
    
    print("=" * 70)
    print("🧪 محاكاة عملية شراء من التطبيق")
    print("=" * 70)
    
    # البيانات
    product_id = 1
    quantity_to_buy = 2
    customer_id = 1
    seller_id = 1
    
    print(f"\n📋 بيانات الشراء:")
    print(f"   Product ID: {product_id}")
    print(f"   Quantity: {quantity_to_buy}")
    print(f"   Customer ID: {customer_id}")
    print(f"   Seller ID: {seller_id}")
    
    # 1. جلب المنتج
    print(f"\n1️⃣ جلب المنتج {product_id}...")
    product = get_product_by_id(product_id)
    if not product:
        print("❌ المنتج غير موجود")
        return False
    
    product_name = product[3]
    price = product[5]
    print(f"   ✅ اسم المنتج: {product_name}")
    print(f"   💰 السعر: {price}")
    
    # 2. جلب صور المنتج
    print(f"\n2️⃣ جلب صور المنتج...")
    images = get_product_images(product_id)
    print(f"   ✅ عدد الصور: {len(images)}")
    for image_id, filename, order in images[:5]:  # اعرض أول 5 صور فقط
        print(f"      - {image_id}: {filename}")
    
    if len(images) < quantity_to_buy:
        print(f"❌ لا توجد صور كافية (متاح: {len(images)}, مطلوب: {quantity_to_buy})")
        return False
    
    # 3. إضافة معاملة ائتمانية
    print(f"\n3️⃣ إضافة معاملة ائتمانية...")
    total_amount = price * quantity_to_buy
    if add_credit_transaction(customer_id, seller_id, total_amount, f"شراء {quantity_to_buy} صورة"):
        print(f"   ✅ تم إضافة {total_amount} د.ع للحساب الآجل")
    else:
        print("❌ فشل إضافة المعاملة الائتمانية")
        return False
    
    # 4. تحديث كمية المنتج
    print(f"\n4️⃣ تحديث كمية المنتج...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        cursor.execute(
            'UPDATE products SET quantity = GREATEST(0, quantity - %s) WHERE productid = %s',
            (quantity_to_buy, product_id)
        )
    else:
        cursor.execute(
            'UPDATE Products SET Quantity = MAX(0, Quantity - ?) WHERE ProductID = ?',
            (quantity_to_buy, product_id)
        )
    conn.commit()
    print(f"   ✅ تم تقليل الكمية بـ {quantity_to_buy}")
    
    # 5. حذف الصور
    print(f"\n5️⃣ حذف {quantity_to_buy} صور...")
    images_to_delete = images[:quantity_to_buy]
    deleted = 0
    
    for image_id, filename, order in images_to_delete:
        try:
            if IS_POSTGRES:
                cursor.execute('DELETE FROM imagestorage WHERE imageid = %s', (image_id,))
            else:
                cursor.execute('DELETE FROM imagestorage WHERE imageid = ?', (image_id,))
            deleted += 1
            print(f"   ✅ تم حذف: {filename}")
        except Exception as e:
            print(f"   ❌ خطأ في حذف {filename}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 النتائج:")
    print(f"   تم حذف {deleted} من {quantity_to_buy} صورة")
    
    # التحقق النهائي
    print(f"\n✅ التحقق النهائي:")
    images_after = get_product_images(product_id)
    print(f"   الصور المتبقية: {len(images_after)} (كانت {len(images)})")
    
    if len(images_after) == len(images) - deleted:
        print(f"   ✅ تم حذف الصور بنجاح!")
        return True
    else:
        print(f"   ❌ عدد الصور لم يتغير كما هو متوقع")
        return False

if __name__ == "__main__":
    success = simulate_purchase()
    sys.exit(0 if success else 1)
