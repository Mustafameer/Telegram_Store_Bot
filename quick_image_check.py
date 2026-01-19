#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص سريع لحالة الصورة والـ Firebase"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(database_url)
cursor = conn.cursor()

# آخر صورة
cursor.execute("""
    SELECT imageid, filename, firebase_filename, url, updatedat, filedata IS NOT NULL as has_bytea
    FROM imagestorage
    ORDER BY updatedat DESC
    LIMIT 5
""")

print("\n📊 آخر 5 صور:")
print("="*100)

for imageid, filename, firebase_filename, url, updatedat, has_bytea in cursor.fetchall():
    print(f"\n🔍 الصورة #{imageid}")
    print(f"   الملف: {filename}")
    print(f"   Firebase: {firebase_filename}")
    print(f"   URL: {url if url else '❌ فارغ'}")
    print(f"   BYTEA: {'✅ موجود' if has_bytea else '❌ فارغ'}")
    print(f"   الوقت: {updatedat}")

cursor.close()
conn.close()
