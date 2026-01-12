#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
التحقق من مسارات الصور في قاعدة البيانات
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")

if os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # فحص المنتجات
    cursor.execute("SELECT ProductID, Name, ImagePath FROM Products LIMIT 10")
    products = cursor.fetchall()
    
    print("=" * 60)
    print("🔍 فحص مسارات الصور في المنتجات:")
    print("=" * 60)
    
    for pid, name, img_path in products:
        print(f"\n📦 منتج #{pid}: {name}")
        print(f"   المسار في DB: {img_path}")
        
        if img_path:
            # التحقق من وجود الصورة
            if os.path.exists(img_path):
                print(f"   ✅ الصورة موجودة: {img_path}")
            else:
                # محاولة البحث في IMAGES_FOLDER
                basename = os.path.basename(img_path)
                alt_path = os.path.join(IMAGES_FOLDER, basename)
                
                if os.path.exists(alt_path):
                    print(f"   ✅ الصورة موجودة في: {alt_path}")
                    print(f"   💡 يجب تحديث المسار في DB إلى: {alt_path}")
                else:
                    print(f"   ❌ الصورة غير موجودة!")
                    print(f"   🔍 بحث في: {img_path}")
                    print(f"   🔍 بحث في: {alt_path}")
        else:
            print(f"   ⚠️ لا يوجد مسار للصورة")
    
    # عرض الصور المتوفرة
    print("\n" + "=" * 60)
    print("📸 الصور المتوفرة في data/Images:")
    print("=" * 60)
    
    if os.path.exists(IMAGES_FOLDER):
        images = os.listdir(IMAGES_FOLDER)
        for img in images:
            print(f"   ✅ {img}")
        print(f"\n📊 إجمالي: {len(images)} صورة")
    else:
        print("   ⚠️ المجلد غير موجود!")
    
    conn.close()
else:
    print(f"❌ قاعدة البيانات غير موجودة: {DB_FILE}")
