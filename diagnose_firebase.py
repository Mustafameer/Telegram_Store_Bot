#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تشخيص شامل لحالة الصور والـ Firebase"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def diagnose_images():
    """تشخيص كامل للصور والـ Firebase"""
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL غير موجود")
            return
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("🔍 تشخيص شامل للصور")
        print("="*80)
        
        # 1. عدد الصور الكلي
        cursor.execute("SELECT COUNT(*) FROM imagestorage")
        total = cursor.fetchone()[0]
        print(f"\n📊 إجمالي الصور: {total}")
        
        # 2. الصور بـ Firebase URL
        cursor.execute("SELECT COUNT(*) FROM imagestorage WHERE url IS NOT NULL")
        firebase = cursor.fetchone()[0]
        print(f"🔥 صور في Firebase: {firebase}")
        
        # 3. الصور بـ BYTEA فقط (الاحتياطية)
        cursor.execute("""
            SELECT COUNT(*) FROM imagestorage 
            WHERE filedata IS NOT NULL AND url IS NULL
        """)
        bytea_only = cursor.fetchone()[0]
        print(f"💾 صور في PostgreSQL (BYTEA): {bytea_only}")
        
        # 4. آخر صورة تم إضافتها
        print("\n" + "-"*80)
        print("📸 آخر صورة تم إضافتها:")
        print("-"*80)
        
        cursor.execute("""
            SELECT 
                imageid,
                filename,
                firebase_filename,
                url,
                updatedat,
                productid
            FROM imagestorage
            ORDER BY updatedat DESC
            LIMIT 1
        """)
        
        last_image = cursor.fetchone()
        if last_image:
            imageid, filename, firebase_filename, url, updated_at, productid = last_image
            print(f"معرّف: {imageid}")
            print(f"الاسم: {filename}")
            print(f"Firebase: {firebase_filename}")
            print(f"URL: {url if url else '❌ بدون URL'}")
            print(f"التاريخ: {updated_at}")
            print(f"المنتج: {productid}")
        else:
            print("❌ لا توجد صور في الجدول")
        
        # 5. التحقق من Firebase
        print("\n" + "-"*80)
        print("🔥 حالة Firebase:")
        print("-"*80)
        
        if os.path.exists('firebase-key.json'):
            print("✅ ملف firebase-key.json موجود")
        else:
            print("❌ ملف firebase-key.json غير موجود")
        
        try:
            import firebase_admin
            print("✅ firebase-admin مثبت")
        except ImportError:
            print("❌ firebase-admin غير مثبت")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    diagnose_images()
