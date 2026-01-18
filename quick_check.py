#!/usr/bin/env python3
import psycopg2
import os
os.chdir(r"c:\Users\Hp\Desktop\TelegramStoreBot")
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# عدد المنتجات
cursor.execute('SELECT COUNT(*) FROM products')
print(f"📦 Products: {cursor.fetchone()[0]}")

# عدد الصور
cursor.execute('SELECT COUNT(*) FROM productimages')
print(f"📸 Product Images: {cursor.fetchone()[0]}")

# الصور لكل منتج
cursor.execute('''
    SELECT p.productid, p.name, COUNT(pi.imageid) as cnt
    FROM products p
    LEFT JOIN productimages pi ON p.productid = pi.productid
    GROUP BY p.productid, p.name
    LIMIT 5
''')

print("\n📋 Images per product:")
for pid, name, cnt in cursor.fetchall():
    print(f"  {pid}: {name} = {cnt} images")

conn.close()
