#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
التحقق من مسارات الصور في قاعدة البيانات
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")

# البحث عن قواعد البيانات
db_files = [
    os.path.join(BASE_DIR, "store.db"),
    os.path.join(BASE_DIR, "store_local.db"),
    os.path.join(DATA_DIR, "store_local_new.db"),
]

for DB_FILE in db_files:
    if not os.path.exists(DB_FILE):
        continue
        
    print("=" * 80)
    print(f"🔍 فحص قاعدة البيانات: {DB_FILE}")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # فحص المنتجات
        cursor.execute("SELECT ProductID, Name, ImagePath FROM Products LIMIT 5")
        products = cursor.fetchall()
        
        print(f"\n📦 المنتجات ({len(products)}):")
        
        for pid, name, img_path in products:
            print(f"\n   المنتج #{pid}: {name}")
            print(f"   المسار: {img_path}")
            
            if img_path:
                basename = os.path.basename(img_path)
                
                # التحقق من المسار المباشر
                if os.path.exists(img_path):
                    print(f"   ✅ موجود: {img_path}")
                else:
                    # التحقق في IMAGES_FOLDER
                    alt_path = os.path.join(IMAGES_FOLDER, basename)
                    if os.path.exists(alt_path):
                        print(f"   ✅ موجود في: {alt_path}")
                    else:
                        print(f"   ❌ غير موجود!")
            else:
                print(f"   ⚠️ لا يوجد مسار")
        
        conn.close()
        print("\n")
        
    except Exception as e:
        print(f"❌ خطأ: {e}\n")

# عرض الصور المتوفرة
print("=" * 80)
print("📸 الصور المتوفرة في data/Images:")
print("=" * 80)

if os.path.exists(IMAGES_FOLDER):
    images = os.listdir(IMAGES_FOLDER)
    for img in images:
        img_path = os.path.join(IMAGES_FOLDER, img)
        size = os.path.getsize(img_path)
        print(f"   ✅ {img} ({size:,} bytes)")
    print(f"\n📊 إجمالي: {len(images)} صورة")
else:
    print("   ⚠️ المجلد غير موجود!")
