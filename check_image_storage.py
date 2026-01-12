#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص وجود الصور في ImageStorage على PostgreSQL
"""
import os
import psycopg2
from urllib.parse import urlparse

def check_image_storage():
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL غير موجود!")
        return
    
    try:
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
        
        # فحص عدد الصور في ImageStorage
        cursor.execute("SELECT COUNT(*) FROM ImageStorage")
        count = cursor.fetchone()[0]
        
        print(f"\n📸 عدد الصور في ImageStorage: {count}")
        
        if count == 0:
            print("\n❌ لا توجد صور في ImageStorage!")
            print("\n💡 **الحل:**")
            print("1. افتح تطبيق Flutter Desktop (desktop app)")
            print("2. سجل دخولك كصاحب متجر")
            print("3. أضف منتجات جديدة **مع صور**")
            print("4. يجب أن يقوم التطبيق برفع الصور إلى السحابة")
            print("\nأو:")
            print("1. استخدم أمر /check_images في البوت (كأدمن)")
            print("2. سيعرض عدد الصور المتوفرة")
        else:
            # عرض أمثلة من الصور
            cursor.execute("""
                SELECT FileName, LENGTH(FileData) as FileSize 
                FROM ImageStorage 
                ORDER BY UpdatedAt DESC 
                LIMIT 10
            """)
            images = cursor.fetchall()
            
            print("\n✅ الصور الموجودة:")
            for idx, (filename, size) in enumerate(images, 1):
                print(f"{idx}. {filename[:50]}... ({size:,} bytes)")
        
        # فحص المنتجات وصورها
        print("\n" + "=" * 80)
        cursor.execute("""
            SELECT ProductID, Name, ImagePath 
            FROM Products 
            WHERE ImagePath IS NOT NULL AND ImagePath != ''
            LIMIT 10
        """)
        products = cursor.fetchall()
        
        print(f"📦 عدد المنتجات بصور: {len(products)}")
        
        if products:
            # استخراج أسماء الصور من ImageStorage
            cursor.execute("SELECT FileName FROM ImageStorage")
            storage_files = {row[0] for row in cursor.fetchall()}
            
            print("\n📋 المنتجات والصور المرتبطة بها:")
            for pid, name, img_path in products:
                basename = os.path.basename(img_path) if img_path else "N/A"
                exists_in_storage = "✅" if basename in storage_files else "❌"
                print(f"{exists_in_storage} {name}: {basename[:40]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_image_storage()
