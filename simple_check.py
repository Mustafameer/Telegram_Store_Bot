#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص بسيط للصور والمنتجات
Simple check for images and products
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # فحص عدد المنتجات
    cursor.execute('SELECT COUNT(*) FROM products')
    prod_count = cursor.fetchone()[0]
    print(f"📦 عدد المنتجات: {prod_count}")
    
    # فحص عدد الصور
    cursor.execute('SELECT COUNT(*) FROM productimages')
    img_count = cursor.fetchone()[0]
    print(f"📸 عدد الصور: {img_count}")
    
    # الصور لكل منتج
    print(f"\n📋 الصور لكل منتج:")
    cursor.execute('''
        SELECT p.productid, p.name, COUNT(pi.imageid) as img_cnt
        FROM products p
        LEFT JOIN productimages pi ON p.productid = pi.productid
        GROUP BY p.productid, p.name
        LIMIT 10
    ''')
    
    for pid, name, img_cnt in cursor.fetchall():
        print(f"  ID={pid}, Name={name}: {img_cnt} صور")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
