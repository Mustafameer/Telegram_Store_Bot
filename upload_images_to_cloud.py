#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
رفع الصور من data/Images إلى ImageStorage على PostgreSQL
"""
import os
import psycopg2
from urllib.parse import urlparse

def upload_images_to_cloud():
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL غير موجود!")
        return
    
    # مسار مجلد الصور المحلي
    images_folder = os.path.join(os.path.dirname(__file__), "data", "Images")
    
    if not os.path.exists(images_folder):
        print(f"❌ مجلد الصور غير موجود: {images_folder}")
        return
    
    # قائمة الصور
    image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
    
    if not image_files:
        print("❌ لا توجد صور في مجلد data/Images")
        return
    
    print(f"📸 عدد الصور المراد رفعها: {len(image_files)}")
    
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
        
        # التأكد من وجود جدول ImageStorage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage (
                FileName TEXT PRIMARY KEY,
                FileData BYTEA,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✅ جدول ImageStorage موجود/تم إنشاؤه")
        
        # رفع الصور
        uploaded = 0
        failed = 0
        skipped = 0
        
        for filename in image_files:
            filepath = os.path.join(images_folder, filename)
            
            try:
                # قراءة الصورة
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                # التحقق من وجود الصورة
                cursor.execute("SELECT FileName FROM ImageStorage WHERE FileName = %s", (filename,))
                exists = cursor.fetchone()
                
                if exists:
                    print(f"⏭️  موجودة بالفعل: {filename}")
                    skipped += 1
                else:
                    # رفع الصورة
                    cursor.execute(
                        "INSERT INTO ImageStorage (FileName, FileData) VALUES (%s, %s)",
                        (filename, file_data)
                    )
                    conn.commit()
                    print(f"✅ تم رفع: {filename} ({len(file_data):,} bytes)")
                    uploaded += 1
                    
            except Exception as e:
                print(f"❌ خطأ في رفع {filename}: {e}")
                failed += 1
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print(f"📊 النتائج:")
        print(f"✅ تم رفع: {uploaded}")
        print(f"⏭️  موجودة بالفعل: {skipped}")
        print(f"❌ فشل: {failed}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ خطأ الاتصال: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    upload_images_to_cloud()
