#!/usr/bin/env python3
"""
اختبار: تحقق من ترتيب الأعمدة في جدول Sellers
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# الحصول على بيانات seller واحد
cursor.execute("""
    SELECT * FROM Sellers WHERE SellerID = 21
""")

seller = cursor.fetchone()

if seller:
    print("\n" + "="*70)
    print("📊 ترتيب الأعمدة في جدول Sellers (كـ dict):")
    print("="*70 + "\n")
    
    for idx, (key, value) in enumerate(seller.items()):
        print(f"{idx:2}: {key:35} = {value}")
    
    # الآن حاول كـ tuple
    print("\n" + "="*70)
    print("📊 كـ tuple (indexed):")
    print("="*70 + "\n")
    
    # تحويل إلى tuple من القيم فقط
    seller_values = tuple(seller.values())
    for idx, value in enumerate(seller_values):
        print(f"{idx:2}: {value}")

conn.close()
