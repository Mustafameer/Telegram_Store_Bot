#!/usr/bin/env python3
"""
Fix filename mismatch between productimages and imagestorage
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🔧 Starting filename fix...\n")
    
    # Get products that need fixing
    cur.execute("""
        SELECT pi.productid, pi.imagepath, p.name
        FROM productimages pi
        JOIN products p ON pi.productid = p.productid
        WHERE pi.imagepath IN ('headphones.jpg', 'phone.jpg', 'tshirt.jpg')
    """)
    
    products_to_fix = cur.fetchall()
    print(f"Found {len(products_to_fix)} products to fix:")
    
    # Mapping of old names to new names (from test output)
    name_mapping = {
        'headphones.jpg': '1768071610_c32def6afa344606a74af7274c6d3513.jpg',
        'phone.jpg': '1765990974066_حافظة نظارات.jpg',
        'tshirt.jpg': '1765608973_4838503b05b94ae2aef0667b52cadc02.jpg'
    }
    
    for product_id, old_name, product_name in products_to_fix:
        new_name = name_mapping.get(old_name)
        if new_name:
            print(f"\n  Product {product_id} ({product_name}):")
            print(f"    Old: {old_name}")
            print(f"    New: {new_name}")
            
            # Verify new file exists in imagestorage
            cur.execute(
                "SELECT 1 FROM imagestorage WHERE filename = %s",
                (new_name,)
            )
            if cur.fetchone():
                # Update the productimages table
                cur.execute(
                    "UPDATE productimages SET imagepath = %s WHERE productid = %s AND imagepath = %s",
                    (new_name, product_id, old_name)
                )
                print(f"    ✅ Updated")
            else:
                print(f"    ❌ New file not found in imagestorage!")
    
    conn.commit()
    
    # Verify the fix
    print("\n" + "="*60)
    print("🔍 Verification:")
    cur.execute("""
        SELECT DISTINCT pi.imagepath
        FROM productimages pi
        WHERE NOT EXISTS (
            SELECT 1 FROM imagestorage img
            WHERE img.filename = pi.imagepath
        )
    """)
    
    unmatched = cur.fetchall()
    if unmatched:
        print(f"❌ Still {len(unmatched)} unmatched files:")
        for path in unmatched:
            print(f"  - {path[0]}")
    else:
        print("✅ All product images now match imagestorage filenames!")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
