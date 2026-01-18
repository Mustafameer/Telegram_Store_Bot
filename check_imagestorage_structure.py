#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
التحقق من هيكل جدول imagestorage الحالي
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def check_imagestorage_structure():
    """التحقق من هيكل imagestorage"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير محدد")
        return False
    
    try:
        print("🔗 جاري الاتصال بقاعدة البيانات...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # التحقق من الأعمدة
        print("\n📋 أعمدة جدول imagestorage:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'imagestorage'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        if not columns:
            print("❌ لم يتم العثور على الجدول")
            return False
        
        for col_name, data_type, is_nullable in columns:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"   ✅ {col_name}: {data_type} ({nullable})")
        
        # عداد الصور
        print("\n📊 إحصائيات:")
        cursor.execute("SELECT COUNT(*) FROM imagestorage")
        total = cursor.fetchone()[0]
        print(f"   • إجمالي الصور: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM imagestorage WHERE productid IS NOT NULL")
        with_product = cursor.fetchone()[0]
        print(f"   • صور مع productid: {with_product}")
        
        cursor.execute("SELECT COUNT(*) FROM imagestorage WHERE productid IS NULL")
        without_product = cursor.fetchone()[0]
        print(f"   • صور بدون productid: {without_product}")
        
        # عينة من البيانات
        print("\n📸 عينة من البيانات:")
        cursor.execute("""
            SELECT imageid, filename, productid, imageorder 
            FROM imagestorage 
            LIMIT 5
        """)
        
        samples = cursor.fetchall()
        if samples:
            for imageid, filename, productid, imageorder in samples:
                print(f"   • ID:{imageid} | Product:{productid} | Order:{imageorder} | File:{filename[:40]}...")
        else:
            print("   ⚠️ لا توجد بيانات")
        
        cursor.close()
        conn.close()
        
        print("\n✅ التحقق اكتمل بنجاح!")
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    success = check_imagestorage_structure()
    exit(0 if success else 1)
