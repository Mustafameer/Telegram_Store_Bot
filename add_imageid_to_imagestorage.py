#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إضافة عمود imageid إلى جدول imagestorage
Add imageid column to imagestorage table
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def add_imageid_column():
    """إضافة عمود imageid إلى جدول imagestorage"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير محدد في متغيرات البيئة")
        return False
    
    try:
        print(f"🔗 جاري الاتصال بقاعدة البيانات...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # التحقق من وجود العمود
        print("🔍 جاري التحقق من وجود العمود imageid...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'imagestorage' AND column_name = 'imageid'
        """)
        
        if cursor.fetchone():
            print("✅ العمود imageid موجود بالفعل")
            cursor.close()
            conn.close()
            return True
        
        # إضافة العمود
        print("📝 جاري إضافة العمود imageid...")
        cursor.execute("""
            ALTER TABLE "imagestorage"
            ADD COLUMN "imageid" SERIAL UNIQUE NOT NULL
        """)
        
        conn.commit()
        print("✅ تم إضافة العمود imageid بنجاح")
        
        # التحقق من النتيجة
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'imagestorage'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 أعمدة جدول imagestorage:")
        for column_name, data_type in cursor.fetchall():
            print(f"   - {column_name}: {data_type}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ تم تحديث قاعدة البيانات بنجاح!")
        return True
        
    except psycopg2.errors.DuplicateColumn:
        print("⚠️ العمود موجود بالفعل")
        return True
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    success = add_imageid_column()
    exit(0 if success else 1)
