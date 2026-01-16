#!/usr/bin/env python3
"""
Test script to verify image upload from Flutter app works correctly
"""
import psycopg2
import os
from dotenv import load_dotenv
import time

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("✅ Connected to PostgreSQL")
    
    # Check if imagestorage table exists (lowercase)
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'imagestorage'
        )
    """)
    if not cursor.fetchone()[0]:
        print("❌ imagestorage table doesn't exist!")
        exit(1)
    
    print("✅ imagestorage table exists")
    
    # Check if there are any images in imagestorage
    cursor.execute("SELECT COUNT(*) FROM imagestorage")
    image_count = cursor.fetchone()[0]
    print(f"📊 Total images in imagestorage: {image_count}")
    
    # Check if there are products with images
    cursor.execute("""
        SELECT COUNT(*) FROM productimages
    """)
    product_image_count = cursor.fetchone()[0]
    print(f"📊 Total product-image relationships: {product_image_count}")
    
    # Check a sample
    if image_count > 0:
        cursor.execute("""
            SELECT filename, LENGTH(filedata) as filesize, updatedat 
            FROM imagestorage 
            LIMIT 5
        """)
        images = cursor.fetchall()
        print("\n📸 Sample images in storage:")
        for fname, size, updated in images:
            print(f"  - {fname}: {size:,} bytes (updated: {updated})")
    
    # Check for products that have images
    cursor.execute("""
        SELECT p.productid, p.name, COUNT(pi.imageid) as image_count
        FROM products p
        LEFT JOIN productimages pi ON p.productid = pi.productid
        WHERE p.status = 'active'
        GROUP BY p.productid, p.name
        HAVING COUNT(pi.imageid) > 0
        ORDER BY image_count DESC
        LIMIT 5
    """)
    
    products_with_images = cursor.fetchall()
    if products_with_images:
        print("\n📦 Products with images:")
        for pid, name, count in products_with_images:
            print(f"  - Product {pid}: {name} ({count} images)")
            
            # Get the image paths for this product
            cursor.execute("""
                SELECT imagepath FROM productimages 
                WHERE productid = %s
                LIMIT 3
            """, (pid,))
            image_paths = cursor.fetchall()
            for img_path in image_paths:
                print(f"    • {img_path[0]}")
    else:
        print("\n⚠️ No products with images found")
    
    # Check if images in productimages match images in imagestorage
    cursor.execute("""
        SELECT DISTINCT pi.imagepath
        FROM productimages pi
        WHERE NOT EXISTS (
            SELECT 1 FROM imagestorage img
            WHERE img.filename = pi.imagepath
        )
        LIMIT 5
    """)
    
    unmatched = cursor.fetchall()
    if unmatched:
        print(f"\n⚠️ Found {len(unmatched)} product images without matching storage:")
        for path in unmatched[:5]:
            print(f"  - {path[0]}")
    else:
        print("\n✅ All product images have matching storage files")
    
    cursor.close()
    conn.close()
    print("\n✅ Test completed successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
