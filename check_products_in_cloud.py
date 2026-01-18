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
    print("=" * 60)
    print("📦 جميع المنتجات في السحابة:")
    print("=" * 60)
    
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    
    if products:
        for row in products:
            print(f"  {row}")
    else:
        print("  ❌ لا توجد منتجات!")
    
    print("\n" + "=" * 60)
    print("📊 عدد المنتجات حسب البائع:")
    print("=" * 60)
    
    cursor.execute('''
        SELECT "sellerid", COUNT(*) as count 
        FROM products 
        GROUP BY "sellerid"
    ''')
    
    counts = cursor.fetchall()
    for row in counts:
        print(f"  البائع {row[0]}: {row[1]} منتج")
    
finally:
    cursor.close()
    conn.close()
