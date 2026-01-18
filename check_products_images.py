#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import get_db_connection, IS_POSTGRES

def check_products_and_images():
    """فحص المنتجات والصور"""
    print("=" * 60)
    print("🔍 فحص المنتجات والصور")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n1️⃣ عدد المنتجات:")
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        print(f"   ✅ إجمالي المنتجات: {count}")
        
        print("\n2️⃣ عدد الصور:")
        cursor.execute("SELECT COUNT(*) FROM productimages")
        count = cursor.fetchone()[0]
        print(f"   ✅ إجمالي الصور: {count}")
        
        print("\n3️⃣ عدد منتجات لها صور:")
        cursor.execute("SELECT COUNT(DISTINCT productid) FROM productimages")
        count = cursor.fetchone()[0]
        print(f"   ✅ منتجات بصور: {count}")
        
        print("\n4️⃣ أول 5 منتجات لها صور:")
        cursor.execute("""
            SELECT productid, imagepath, imageorder 
            FROM productimages 
            ORDER BY productid, imageorder 
            LIMIT 15
        """)
        
        results = cursor.fetchall()
        if results:
            current_product_id = None
            for productid, imagepath, imageorder in results:
                if productid != current_product_id:
                    print(f"\n   📦 المنتج ID={productid}:")
                    current_product_id = productid
                print(f"      • صورة #{imageorder}: {imagepath}")
        else:
            print("   ⚠️ لا توجد صور في قاعدة البيانات")
        
        print("\n5️⃣ منتجات بدون صور:")
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE productid NOT IN (SELECT DISTINCT productid FROM productimages)
        """)
        count = cursor.fetchone()[0]
        print(f"   ✅ عدد المنتجات بدون صور: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_products_and_images()
