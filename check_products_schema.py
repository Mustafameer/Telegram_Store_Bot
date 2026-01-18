#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import get_db_connection, IS_POSTGRES

def check_products_schema():
    """فحص schema جدول products"""
    print("=" * 60)
    print("🔍 فحص جدول products")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            # الحصول على أسماء الأعمدة
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'products'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            print(f"\n✅ أعمدة جدول products:\n")
            for col_name, col_type in columns:
                print(f"   - {col_name} ({col_type})")
            
            # اختبر الاستعلام مع أول منتج
            print(f"\n🧪 اختبار الاستعلام:")
            cursor.execute('SELECT * FROM products LIMIT 1')
            result = cursor.fetchone()
            if result:
                print(f"   ✅ النتيجة: {result}")
        else:
            cursor.execute("PRAGMA table_info(Products)")
            columns = cursor.fetchall()
            print(f"\n✅ أعمدة جدول Products:\n")
            for col_info in columns:
                print(f"   - {col_info[1]} ({col_info[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_products_schema()
