#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get all products for seller 21
    print("📦 المنتجات:")
    cur.execute("SELECT productid, name FROM products WHERE sellerid = 21 ORDER BY productid")
    products = cur.fetchall()
    for p in products:
        print(f"   - ID: {p[0]}, Name: {p[1]}")
    
    if not products:
        print("❌ لا توجد منتجات")
        conn.close()
        exit(1)
    
    # Get all images without productid
    print("\n🖼️ الصور بدون productid:")
    cur.execute("SELECT imageid, filename FROM imagestorage WHERE productid IS NULL ORDER BY imageid")
    images = cur.fetchall()
    print(f"عدد الصور: {len(images)}")
    
    # Assign images to products in round-robin fashion
    if images and products:
        product_ids = [p[0] for p in products]
        
        print(f"\n📌 جاري ربط الصور بالمنتجات...")
        for idx, (image_id, filename) in enumerate(images):
            product_id = product_ids[idx % len(product_ids)]
            image_order = idx // len(product_ids)
            
            cur.execute(
                "UPDATE imagestorage SET productid = %s, imageorder = %s WHERE imageid = %s",
                (product_id, image_order, image_id)
            )
            print(f"   - صورة {image_id} → منتج {product_id} (ترتيب: {image_order})")
        
        conn.commit()
        print(f"\n✅ تم ربط {len(images)} صورة بنجاح")
    
    # Verify
    print("\n✅ التحقق:")
    for p_id in product_ids:
        cur.execute("SELECT COUNT(*) FROM imagestorage WHERE productid = %s", (p_id,))
        count = cur.fetchone()[0]
        print(f"   - المنتج {p_id}: {count} صور")
    
    conn.close()
except Exception as e:
    print(f'❌ خطأ: {e}')
    import traceback
    traceback.print_exc()
