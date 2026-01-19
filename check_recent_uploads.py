#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""التحقق من الصور المرفوعة الجديدة"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def check_recent_uploads():
    """عرض آخر الصور المرفوعة إلى Firebase"""
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL غير موجود")
            return
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # آخر الصور (آخر 24 ساعة)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        cursor.execute("""
            SELECT 
                imageid,
                filename,
                firebase_filename,
                url,
                updatedat,
                productid
            FROM imagestorage
            WHERE updatedat > %s
            ORDER BY updatedat DESC
        """, [twenty_four_hours_ago])
        
        results = cursor.fetchall()
        
        print("\n" + "="*80)
        print("🖼️  آخر الصور المرفوعة (آخر 24 ساعة)")
        print("="*80)
        
        if not results:
            print("❌ لم يتم العثور على صور جديدة")
        else:
            for idx, (imageid, filename, firebase_filename, url, updated_at, productid) in enumerate(results, 1):
                status = "🔥 Firebase" if url else "💾 PostgreSQL"
                print(f"\n{idx}. {status}")
                print(f"   المعرّف: {imageid}")
                print(f"   الاسم: {filename}")
                print(f"   التاريخ: {updated_at}")
                if url:
                    print(f"   الرابط: {url}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    check_recent_uploads()
