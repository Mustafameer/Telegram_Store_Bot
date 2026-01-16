#!/usr/bin/env python3
"""
Test the image retrieval and display flow exactly like the bot does
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
IS_POSTGRES = True

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def get_image_from_cloud(filename):
    """
    جلب صورة من السحابة مباشرة دون الحاجة لحفظها محلياً
    (This is the actual function from bot.py)
    """
    if not IS_POSTGRES:
        return None
        
    try:
        filename = os.path.basename(filename) if filename else None
        
        if not filename:
            return None
        
        print(f"  🔍 Looking for: {filename}")
        
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        
        # Try exact match first
        print(f"    → Try 1: Exact match")
        cursor.execute("SELECT FileData FROM ImageStorage WHERE FileName = %s", (filename,))
        result = cursor.fetchone()
        
        if result:
            print(f"    ✅ Found (exact match)")
            conn.close()
            if result[0]:
                return result[0]
        
        # If exact match fails, try case-insensitive
        print(f"    → Try 2: Case-insensitive")
        cursor.execute("SELECT FileData FROM ImageStorage WHERE LOWER(FileName) = LOWER(%s) LIMIT 1", (filename,))
        result = cursor.fetchone()
        
        if result:
            print(f"    ✅ Found (case-insensitive)")
            conn.close()
            if result[0]:
                return result[0]
        
        # If still not found, try partial match
        print(f"    → Try 3: Partial match")
        base_without_ext = os.path.splitext(filename)[0]
        cursor.execute("""
            SELECT FileData 
            FROM ImageStorage 
            WHERE FileName LIKE %s 
            ORDER BY UpdatedAt DESC 
            LIMIT 1
        """, (f"%{base_without_ext}%",))
        result = cursor.fetchone()
        
        if result:
            print(f"    ✅ Found (partial match)")
            conn.close()
            if result[0]:
                return result[0]
        
        print(f"    ❌ NOT FOUND")
        conn.close()
        return None
        
    except Exception as e:
        print(f"    ❌ Error getting image from cloud: {e}")
        return None

def test_product_image_display():
    """Test if products can display images"""
    
    conn = get_db_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    print("\n" + "="*70)
    print("🔍 TESTING PRODUCT IMAGE DISPLAY")
    print("="*70 + "\n")
    
    # Get first product with image
    print("1️⃣ Getting products with images...")
    cur.execute("""
        SELECT p.productid, p.name, pi.imagepath
        FROM products p
        JOIN productimages pi ON p.productid = pi.productid
        WHERE p.status = 'active'
        LIMIT 1
    """)
    
    product = cur.fetchone()
    if not product:
        print("❌ No products with images found!")
        conn.close()
        return
    
    product_id, product_name, image_path = product
    print(f"   ✅ Found: Product {product_id}: {product_name}")
    print(f"   📦 Image path: {image_path}\n")
    
    # Test get_image_from_cloud
    print("2️⃣ Testing get_image_from_cloud()...")
    print(f"   Calling get_image_from_cloud('{image_path}')")
    image_data = get_image_from_cloud(image_path)
    
    if image_data:
        print(f"   ✅ SUCCESS! Got {len(image_data)} bytes\n")
    else:
        print(f"   ❌ FAILED! Image not found\n")
    
    # Check what files are in imagestorage
    print("3️⃣ Checking imagestorage table contents...")
    cur.execute("SELECT filename, LENGTH(filedata) as size FROM imagestorage ORDER BY updatedat DESC")
    files = cur.fetchall()
    
    print(f"   📁 Found {len(files)} files in imagestorage:")
    for filename, size in files:
        match = "✅" if filename == image_path else "❌"
        print(f"     {match} {filename} ({size:,} bytes)")
    
    # Check if image_path exists in imagestorage
    print(f"\n4️⃣ Checking for exact match of '{image_path}'...")
    cur.execute(
        "SELECT 1 FROM imagestorage WHERE filename = %s",
        (image_path,)
    )
    if cur.fetchone():
        print(f"   ✅ Exact match found in imagestorage")
    else:
        print(f"   ❌ Exact match NOT found")
        
        # Try without quotes
        print(f"\n   Trying LIKE match...")
        cur.execute(
            "SELECT filename FROM imagestorage WHERE filename ILIKE %s",
            (f"%{image_path}%",)
        )
        similar = cur.fetchone()
        if similar:
            print(f"   Found similar: {similar[0]}")
        else:
            print(f"   No similar files found either")
    
    conn.close()
    
    # Summary
    print("\n" + "="*70)
    if image_data:
        print("✅ RESULT: Images SHOULD display in bot")
    else:
        print("❌ RESULT: Images will NOT display - filename mismatch or retrieval error")
    print("="*70 + "\n")

test_product_image_display()
