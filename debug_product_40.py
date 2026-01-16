#!/usr/bin/env python3
"""
Test the complete image display flow for a specific product
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
IMAGES_FOLDER = "data/Images"
IS_POSTGRES = True

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def get_product_images(product_id):
    """الحصول على جميع صور المنتج"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ImageID, ImagePath, ImageOrder 
        FROM ProductImages 
        WHERE ProductID=%s 
        ORDER BY ImageOrder, ImageID
    """, (product_id,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_image_from_cloud(filename):
    """جلب صورة من السحابة"""
    try:
        filename = os.path.basename(filename) if filename else None
        if not filename:
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute("SELECT FileData FROM ImageStorage WHERE FileName = %s", (filename,))
        result = cursor.fetchone()
        
        if result and result[0]:
            conn.close()
            return result[0]
        
        # If exact match fails, try case-insensitive
        cursor.execute("SELECT FileData FROM ImageStorage WHERE LOWER(FileName) = LOWER(%s) LIMIT 1", (filename,))
        result = cursor.fetchone()
        
        conn.close()
        if result and result[0]:
            return result[0]
        
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test for Product 40 (الهاتف الذكي)
print("="*70)
print("🔍 TESTING PRODUCT 40 (هاتف ذكي)")
print("="*70 + "\n")

# Step 1: Get product images
print("1️⃣ Getting product images from ProductImages table...")
images = get_product_images(40)

if images:
    print(f"   ✅ Found {len(images)} image(s)")
    for img_id, img_path, img_order in images:
        print(f"      - Image {img_id}: {img_path} (order: {img_order})")
        
        # Step 2: Try to get image from cloud
        print(f"\n2️⃣ Testing get_image_from_cloud('{img_path}')...")
        cloud_image = get_image_from_cloud(img_path)
        
        if cloud_image:
            print(f"   ✅ SUCCESS! Got {len(cloud_image):,} bytes from cloud")
            print(f"   📸 Image data ready to send to bot.send_photo()")
        else:
            print(f"   ❌ FAILED! get_image_from_cloud returned None")
            print(f"\n      Debugging:")
            
            # Check if filename exists in imagestorage
            conn = get_db_connection()
            cursor = conn.cursor()
            
            print(f"      → Checking exact match in imagestorage...")
            cursor.execute("SELECT 1 FROM imagestorage WHERE filename = %s", (img_path,))
            if cursor.fetchone():
                print(f"        ✅ Exact match found")
            else:
                print(f"        ❌ Exact match not found")
                
                # Check similar names
                print(f"      → Looking for similar files...")
                cursor.execute("SELECT filename FROM imagestorage WHERE filename ILIKE %s", (f"%{img_path}%",))
                similar = cursor.fetchone()
                if similar:
                    print(f"        Found similar: {similar[0]}")
                else:
                    print(f"        No similar files")
            
            conn.close()
else:
    print(f"   ❌ NO IMAGES FOUND for product 40!")
    
    # Debug: Check what's in ProductImages table
    print(f"\n   Debugging: All ProductImages in database:")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT productid, imagepath FROM productimages LIMIT 10")
    all_imgs = cursor.fetchall()
    for pid, path in all_imgs:
        print(f"      Product {pid}: {path}")
    conn.close()

print("\n" + "="*70)
print("✅ Test completed")
print("="*70)
