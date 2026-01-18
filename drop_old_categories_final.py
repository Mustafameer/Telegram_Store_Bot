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
    # Check if 'categories' table exists
    print("=" * 60)
    print("🔍 التحقق من وجود جدول 'categories':")
    print("=" * 60)
    
    cursor.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'categories'
        )
    """)
    
    exists = cursor.fetchone()[0]
    
    if exists:
        print("✅ جدول 'categories' موجود - جاري الحذف...")
        cursor.execute('DROP TABLE IF EXISTS "categories" CASCADE')
        conn.commit()
        print("✅ تم حذف جدول 'categories' بنجاح!")
    else:
        print("❌ جدول 'categories' غير موجود بالفعل")
    
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
        if 'categor' in tname.lower() or 'seller' in tname.lower():
            print(f"  {tname}")
    
finally:
    cursor.close()
    conn.close()
