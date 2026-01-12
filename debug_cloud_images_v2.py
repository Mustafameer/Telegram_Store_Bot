#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص الصور في PostgreSQL والتأكد من توافقها مع جدول Products
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse

def check_cloud_images():
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL غير موجود! يرجى تعيينه أولاً.")
        print("\nلتعيينه:")
        print("$env:DATABASE_URL='postgresql://...'")
        return
    
    try:
        # الاتصال بقاعدة البيانات
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cursor = conn.cursor()
        
        print("=" * 80)
        print("✅ متصل بـ PostgreSQL")
        print("=" * 80)
        
        # 1. فحص الصور في ImageStorage
        print("\n📸 الصور في جدول ImageStorage:")
        print("-" * 80)
        
        cursor.execute("SELECT FileName, LENGTH(FileData) as FileSize, UpdatedAt FROM ImageStorage ORDER BY UpdatedAt DESC LIMIT 20")
        images = cursor.fetchall()
        
        if not images:
            print("⚠️ لا توجد صور في جدول ImageStorage!")
        else:
            print(f"عدد الصور: {len(images)}\n")
            for idx, (filename, size, updated_at) in enumerate(images, 1):
                print(f"{idx}. {filename}")
                print(f"   الحجم: {size:,} bytes")
                print(f"   آخر تحديث: {updated_at}")
                print()
        
        # 2. فحص مسارات الصور في Products
        print("\n" + "=" * 80)
        print("📦 مسارات الصور في جدول Products:")
        print("-" * 80)
        
        cursor.execute("SELECT ProductID, Name, ImagePath FROM Products WHERE ImagePath IS NOT NULL AND ImagePath != '' LIMIT 10")
        products = cursor.fetchall()
        
        if not products:
            print("⚠️ لا توجد منتجات بصور!")
        else:
            # استخراج أسماء الصور من ImageStorage
            cursor.execute("SELECT FileName FROM ImageStorage")
            storage_files = {row[0] for row in cursor.fetchall()}
            
            print(f"عدد المنتجات بصور: {len(products)}\n")
            
            for pid, name, img_path in products:
                print(f"المنتج #{pid}: {name}")
                print(f"   المسار في DB: {img_path}")
                
                # استخراج اسم الملف فقط
                if img_path:
                    basename = os.path.basename(img_path)
                    print(f"   اسم الملف: {basename}")
                    
                    # التحقق من وجوده في ImageStorage
                    if basename in storage_files:
                        print(f"   ✅ الصورة موجودة في ImageStorage")
                    else:
                        print(f"   ❌ الصورة غير موجودة في ImageStorage!")
                        
                        # محاولة البحث بمطابقة جزئية
                        matching = [f for f in storage_files if basename in f or f in basename]
                        if matching:
                            print(f"   💡 صور مشابهة: {matching[:3]}")
                print()
        
        # 3. إحصائيات عامة
        print("\n" + "=" * 80)
        print("📊 إحصائيات:")
        print("-" * 80)
        
        cursor.execute("SELECT COUNT(*) FROM ImageStorage")
        total_images = cursor.fetchone()[0]
        print(f"✅ إجمالي الصور في ImageStorage: {total_images}")
        
        cursor.execute("SELECT COUNT(*) FROM Products WHERE ImagePath IS NOT NULL AND ImagePath != ''")
        total_products = cursor.fetchone()[0]
        print(f"✅ إجمالي المنتجات بصور: {total_products}")
        
        cursor.execute("""
            SELECT SUM(LENGTH(FileData))::bigint FROM ImageStorage
        """)
        total_size = cursor.fetchone()[0]
        if total_size:
            print(f"✅ إجمالي حجم الصور: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_cloud_images()
