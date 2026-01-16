#!/usr/bin/env python3
"""
اختبار: إضافة منتج جديد بصورة في متجر مفتوح
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if not IS_POSTGRES:
    print("❌ DATABASE_URL غير موجود")
    exit(1)

# استيراد الدوال من bot.py
sys.path.insert(0, os.path.dirname(__file__))

# محاكاة الدالة add_product_image_db
import psycopg2
from psycopg2.extras import RealDictCursor

def test_open_store_flow():
    """محاكاة تدفق إضافة منتج في متجر مفتوح"""
    print("\n" + "="*70)
    print("🧪 محاكاة تدفق إضافة منتج في متجر مفتوح")
    print("="*70)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. اختر متجر مفتوح
    cursor.execute("""
        SELECT SellerID, StoreName, RequireCustomerRegistration
        FROM Sellers
        WHERE RequireCustomerRegistration = 0
        LIMIT 1
    """)
    
    seller = cursor.fetchone()
    if not seller:
        print("❌ لا توجد متاجر مفتوحة!")
        conn.close()
        return
    
    seller_id = seller['sellerid']
    print(f"\n✅ متجر مفتوح: SellerID={seller_id}, StoreName={seller['storename']}")
    
    # 2. اختر فئة
    cursor.execute("""
        SELECT CategoryID
        FROM Categories
        WHERE SellerID = %s
        LIMIT 1
    """, (seller_id,))
    
    category = cursor.fetchone()
    if not category:
        print(f"⚠️ لا توجد فئات للمتجر {seller_id}")
        conn.close()
        return
    
    category_id = category['categoryid']
    print(f"✅ الفئة: CategoryID={category_id}")
    
    # 3. اسم منتج جديد
    product_name = f"Test Product {int(time.time())}"
    
    # 4. محاكاة process finish_adding_product
    print(f"\n🔄 محاكاة finish_adding_product:")
    print(f"   seller_id={seller_id}")
    print(f"   category_id={category_id}")
    print(f"   product_name={product_name}")
    
    # الحصول على require_registration
    cursor.execute("SELECT * FROM Sellers WHERE SellerID=%s", (seller_id,))
    seller_full = cursor.fetchone()
    
    # ترجمة النتيجة إلى tuple عادي للفهرسة
    seller_tuple = tuple(seller_full.values()) if hasattr(seller_full, 'values') else seller_full
    
    # معامل 10 = RequireCustomerRegistration (بعد إضافة ImagePath في المعامل 9)
    require_registration = seller_tuple[10] if len(seller_tuple) > 10 else 0
    
    print(f"   require_registration={require_registration} (من العامل 10)")
    
    # محاكاة الشرط
    if not require_registration:
        print("   ✅ شرط 'not require_registration' صحيح → يجب إضافة صورة واحدة")
    else:
        print("   ❌ شرط 'not require_registration' خطأ!")
    
    # 5. اختبار الإدراج في ProductImages
    test_filename = f"{int(time.time())}_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.jpg"
    print(f"\n🔄 اختبار إدراج الصورة:")
    print(f"   filename={test_filename}")
    
    # إنشاء منتج اختبار
    cursor.execute("""
        INSERT INTO Products (SellerID, CategoryID, Name, Price, Quantity, ImagePath, Status)
        VALUES (%s, %s, %s, 100000, 1, '', 'active')
    """, (seller_id, category_id, product_name))
    
    # الحصول على ProductID
    cursor.execute("""
        SELECT ProductID FROM Products 
        WHERE SellerID=%s AND CategoryID=%s AND Name=%s 
        ORDER BY ProductID DESC LIMIT 1
    """, (seller_id, category_id, product_name))
    
    result = cursor.fetchone()
    if result:
        product_id = result['productid']
        print(f"   ✅ تم إنشاء منتج: ProductID={product_id}")
        
        # محاكاة إدراج الصورة
        cursor.execute("""
            INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
            VALUES (%s, %s, 0)
        """, (product_id, test_filename))
        
        print(f"   ✅ تم إدراج الصورة في ProductImages")
        
        # التحقق
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM ProductImages
            WHERE ProductID=%s
        """, (product_id,))
        
        count_result = cursor.fetchone()
        img_count = count_result['cnt']
        
        print(f"   ✅ التحقق: وجد {img_count} صورة في ProductImages")
        
        # تنظيف
        cursor.execute("DELETE FROM ProductImages WHERE ProductID=%s", (product_id,))
        cursor.execute("DELETE FROM Products WHERE ProductID=%s", (product_id,))
        print(f"   ✅ تم حذف بيانات الاختبار")
    else:
        print(f"   ❌ فشل إنشاء المنتج!")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    test_open_store_flow()
    print("\n" + "="*70 + "\n")
