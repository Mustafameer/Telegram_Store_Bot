#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص صور المنتجات في قاعدة البيانات
"""
import os
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL not set!")
    print("Please set it first with: $env:DATABASE_URL='postgresql://...'")
    exit(1)

try:
    # Parse and connect
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    
    print("=" * 80)
    print("✅ Connected to PostgreSQL")
    print("=" * 80)
    
    # Check imagestorage table structure
    print("\n📋 imagestorage table structure:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'imagestorage'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    if columns:
        print("\nColumns:")
        for col_name, col_type, nullable in columns:
            print(f"  - {col_name}: {col_type} (nullable: {nullable})")
    else:
        print("❌ imagestorage table not found!")
    
    # Check total images
    print("\n📊 Image counts:")
    cursor.execute("SELECT COUNT(*) as total FROM imagestorage")
    total = cursor.fetchone()[0]
    print(f"  Total images: {total}")
    
    # Check images by product
    print("\n📦 Images grouped by productid:")
    cursor.execute("""
        SELECT productid, COUNT(*) as count
        FROM imagestorage
        GROUP BY productid
        ORDER BY productid
        LIMIT 20
    """)
    
    rows = cursor.fetchall()
    if rows:
        for product_id, count in rows:
            print(f"  - Product {product_id}: {count} images")
    else:
        print("  ❌ No products have images!")
    
    # Show sample images
    print("\n🖼️ Sample images from imagestorage:")
    cursor.execute("""
        SELECT imageid, productid, filename, imageorder
        FROM imagestorage
        ORDER BY productid, imageorder
        LIMIT 10
    """)
    
    samples = cursor.fetchall()
    if samples:
        for image_id, product_id, filename, order in samples:
            print(f"  ID: {image_id}, Product: {product_id}, File: {filename}, Order: {order}")
    else:
        print("  ❌ No images found in table!")
    
    cursor.close()
    conn.close()
    print("\n✅ Check completed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
