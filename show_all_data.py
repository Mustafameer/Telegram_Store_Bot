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
    # Check all sellers
    print("=" * 60)
    print("📋 جميع البائعين:")
    print("=" * 60)
    cursor.execute('SELECT * FROM sellers')
    sellers = cursor.fetchall()
    for row in sellers:
        print(f"  {row}")
    print(f"Total: {len(sellers)}")
    
    print("\n" + "=" * 60)
    print("📁 جميع الفئات في Categories:")
    print("=" * 60)
    cursor.execute('SELECT * FROM "Categories"')
    categories = cursor.fetchall()
    for row in categories:
        print(f"  {row}")
    print(f"Total: {len(categories)}")
    
    print("\n" + "=" * 60)
    print("📁 جميع الفئات في categories (القديمة):")
    print("=" * 60)
    cursor.execute('SELECT * FROM categories')
    old_cats = cursor.fetchall()
    for row in old_cats:
        print(f"  {row}")
    print(f"Total: {len(old_cats)}")
            
finally:
    cursor.close()
    conn.close()
