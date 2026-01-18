#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from bot import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

try:
    # Check if 'Products' table exists
    print("=" * 60)
    print("🔍 التحقق من وجود جدول 'Products':")
    print("=" * 60)
    
    cursor.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'Products'
        )
    """)
    
    exists = cursor.fetchone()[0]
    
    if exists:
        print("✅ جدول 'Products' موجود - جاري الحذف...")
        cursor.execute('DROP TABLE IF EXISTS "Products" CASCADE')
        conn.commit()
        print("✅ تم حذف جدول 'Products' بنجاح!")
    else:
        print("❌ جدول 'Products' غير موجود بالفعل")
    
    print("\n" + "=" * 60)
    print("✅ التحقق النهائي من الجداول المتبقية:")
    print("=" * 60)
    
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    for table in tables:
        tname = table[0]
        if 'product' in tname.lower():
            print(f"  {tname}")
    
finally:
    cursor.close()
    conn.close()
