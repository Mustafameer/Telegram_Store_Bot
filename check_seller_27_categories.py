#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

# Import database functions
from bot import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

try:
    # First, check all sellers
    print("=" * 60)
    print("📋 جميع البائعين في قاعدة البيانات:")
    print("=" * 60)
    cursor.execute('SELECT "SellerID", "SellerName", "TelegramID" FROM "Sellers"')
    sellers = cursor.fetchall()
    for row in sellers:
        print(f"SellerID: {row[0]}, Name: {row[1]}, TelegramID: {row[2]}")
    
    print("\n" + "=" * 60)
    print("📁 جميع الفئات في جدول Categories:")
    print("=" * 60)
    cursor.execute('SELECT "CategoryID", "SellerID", "Name", "OrderIndex" FROM "Categories" ORDER BY "SellerID"')
    categories = cursor.fetchall()
    for row in categories:
        print(f"CategoryID: {row[0]}, SellerID: {row[1]}, Name: {row[2]}, OrderIndex: {row[3]}")
    
    print("\n" + "=" * 60)
    print("🔍 الفئات الخاصة بـ seller_id = 27:")
    print("=" * 60)
    cursor.execute('SELECT "CategoryID", "SellerID", "Name" FROM "Categories" WHERE "SellerID"=27')
    seller_27_cats = cursor.fetchall()
    if seller_27_cats:
        for row in seller_27_cats:
            print(f"CategoryID: {row[0]}, SellerID: {row[1]}, Name: {row[2]}")
    else:
        print("❌ لا توجد فئات لـ seller_id = 27")
        
finally:
    cursor.close()
    conn.close()
