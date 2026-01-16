#!/usr/bin/env python3
"""
تنظيف المنتجات القديمة التي لم تُحفظ صورها بشكل صحيح
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

import psycopg2

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("\n" + "="*70)
print("🧹 حذف المنتجات القديمة بدون صور من المتاجر المفتوحة")
print("="*70)

# حذف المنتجات بدون صور في open stores
cursor.execute("""
    DELETE FROM Products
    WHERE SellerID IN (
        SELECT SellerID FROM Sellers WHERE RequireCustomerRegistration = 0
    )
    AND ProductID NOT IN (
        SELECT DISTINCT ProductID FROM ProductImages
    )
    AND Status = 'active'
""")

deleted_count = cursor.rowcount
print(f"\n✅ تم حذف {deleted_count} منتج بدون صور")

conn.commit()
conn.close()
print("\n" + "="*70 + "\n")
