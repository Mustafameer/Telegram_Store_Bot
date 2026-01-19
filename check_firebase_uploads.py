#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""التحقق من الصور المرفوعة إلى Firebase"""

import os
import sys
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def check_firebase_uploads():
    """عرض الصور المرفوعة إلى Firebase في قاعدة البيانات"""
    
    try:
        # الاتصال بقاعدة البيانات
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("❌ لم يتم العثور على DATABASE_URL")
            return
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # الاستعلام عن آخر الصور المرفوعة
        cursor.execute("""
            SELECT 
                imageid,
                filename,
                firebase_filename,
                url,
                migrated_to_firebase,
                updatedat,
                productid
            FROM imagestorage
            WHERE url IS NOT NULL
            ORDER BY updatedat DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        print("\n" + "="*80)
        print("🖼️  آخر الصور المرفوعة إلى Firebase")
        print("="*80)
        
        if not results:
            print("❌ لم يتم العثور على صور مرفوعة")
            return
        
        for idx, (imageid, filename, firebase_filename, url, migrated, updated_at, productid) in enumerate(results, 1):
            print(f"\n📸 الصورة {idx}:")
            print(f"   • معرّف: {imageid}")
            print(f"   • الاسم المحلي: {filename}")
            print(f"   • الاسم في Firebase: {firebase_filename}")
            print(f"   • المنتج: {productid}")
            print(f"   • التاريخ: {updated_at}")
            
            if url:
                print(f"   • الرابط (Firebase):")
                print(f"     {url}")
            else:
                print(f"   ⚠️  لم يتم حفظ الرابط")
        
        # إحصائيات
        print("\n" + "-"*80)
        cursor.execute("""
            SELECT COUNT(*) FROM imagestorage WHERE url IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        print(f"📊 إجمالي الصور المرفوعة: {count}")
        
        # التحقق من الأخطاء
        cursor.execute("""
            SELECT COUNT(*) FROM imagestorage 
            WHERE filedata IS NOT NULL AND url IS NULL
        """)
        fallback_count = cursor.fetchone()[0]
        if fallback_count > 0:
            print(f"⚠️  صور بدون رابط Firebase (تستخدم الحفظ المحلي): {fallback_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_firebase_uploads()
