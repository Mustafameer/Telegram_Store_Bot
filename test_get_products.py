#!/usr/bin/env python3
"""
Test what get_products() returns
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Check what get_products returns
print("🔍 Testing what get_products() returns:\n")

cursor.execute("""
    SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath 
    FROM Products 
    WHERE Quantity > 0 AND Status='active'
    LIMIT 1
""")

product = cursor.fetchone()

if product:
    pid, name, desc, price, wprice, qty, img_path = product
    print(f"Product ID: {pid}")
    print(f"Name: {name}")
    print(f"Price: {price}")
    print(f"Qty: {qty}")
    print(f"ImagePath column value: '{img_path}'")
    print(f"ImagePath type: {type(img_path)}")
    
    if img_path:
        print(f"\n✅ ImagePath is not null/empty")
        print(f"   Length: {len(img_path)} characters")
        print(f"   Repr: {repr(img_path)}")
    else:
        print(f"\n❌ ImagePath is NULL or EMPTY!")
else:
    print("❌ No products found")

conn.close()
