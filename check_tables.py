#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import get_db_connection, IS_POSTGRES

def check_tables():
    """فحص جميع الجداول في قاعدة البيانات"""
    print("=" * 60)
    print("🔍 فحص جداول قاعدة البيانات")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            print("\n📊 الاتصال: PostgreSQL")
            
            # الحصول على جميع الجداول
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            print(f"\n✅ عدد الجداول: {len(tables)}\n")
            for idx, (table_name,) in enumerate(tables, 1):
                print(f"   {idx}. {table_name}")
            
            # البحث عن جداول تحتوي على "image"
            print(f"\n{'='*60}")
            print("🔍 البحث عن جداول صور:")
            image_tables = [t for t in tables if 'image' in t[0].lower()]
            if image_tables:
                for table_name, in image_tables:
                    print(f"   ✅ {table_name}")
            else:
                print("   ⚠️ لم يتم العثور على جداول صور")
            
            # التحقق من وجود جدول ProductImages تحديداً
            print(f"\n{'='*60}")
            print("🔍 البحث عن جدول ProductImages:")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'ProductImages'
                )
            """)
            exists = cursor.fetchone()[0]
            if exists:
                print("   ✅ جدول ProductImages موجود")
            else:
                print("   ❌ جدول ProductImages غير موجود!")
            
            # البحث عن جدول productimages (lowercase)
            print("\n🔍 البحث عن جدول productimages (lowercase):")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'productimages'
                )
            """)
            exists = cursor.fetchone()[0]
            if exists:
                print("   ✅ جدول productimages موجود")
                
                # عرض الأعمدة
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'productimages'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                print("\n   الأعمدة:")
                for col_name, col_type in columns:
                    print(f"      - {col_name} ({col_type})")
            else:
                print("   ❌ جدول productimages غير موجود")
            
            # التحقق من جدول ImageStorage
            print(f"\n{'='*60}")
            print("🔍 البحث عن جدول ImageStorage:")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'ImageStorage'
                )
            """)
            exists = cursor.fetchone()[0]
            if exists:
                print("   ✅ جدول ImageStorage موجود")
                
                # عدد الصور
                cursor.execute("SELECT COUNT(*) FROM \"ImageStorage\"")
                count = cursor.fetchone()[0]
                print(f"   📊 عدد الصور: {count}")
            else:
                print("   ❌ جدول ImageStorage غير موجود")
        
        else:
            print("\n📊 الاتصال: SQLite")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"\n✅ عدد الجداول: {len(tables)}\n")
            for idx, (table_name,) in enumerate(tables, 1):
                print(f"   {idx}. {table_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_tables()
