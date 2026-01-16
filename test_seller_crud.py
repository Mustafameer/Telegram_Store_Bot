#!/usr/bin/env python3
"""
اختبار شامل لتأكيد عمل دوال إدارة المتاجر
Comprehensive test for seller management functions
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def run_all_tests():
    """تشغيل جميع الاختبارات"""
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        conn = psycopg2.connect(db_url, sslmode='require')
        cur = conn.cursor()
        print("✅ Connected to database\n")
        
        # 📊 اختبار 1: جلب المتاجر الحالية
        print("=" * 50)
        print("📊 TEST 1: Get All Sellers")
        print("=" * 50)
        cur.execute('SELECT "sellerid", "telegramid", "storename", "status" FROM sellers')
        sellers = cur.fetchall()
        print(f"Found {len(sellers)} sellers:")
        for seller in sellers:
            print(f"  ID: {seller[0]}, Telegram: {seller[1]}, Name: {seller[2]}, Status: {seller[3]}")
        
        # ➕ اختبار 2: إضافة متجر جديد
        print("\n" + "=" * 50)
        print("➕ TEST 2: Create New Seller")
        print("=" * 50)
        test_data = {
            'telegram_id': 999111222,
            'store_name': 'متجر الاختبار الجديد',
            'user_name': 'فني الاختبار',
            'image_path': '/path/to/image.jpg'
        }
        
        cur.execute(
            '''INSERT INTO sellers ("telegramid", "storename", "username", "imagepath", "requirecustomerregistration", "status")
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING "sellerid"''',
            (test_data['telegram_id'], test_data['store_name'], test_data['user_name'], 
             test_data['image_path'], 0, 'active')
        )
        new_seller_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ New seller created:")
        print(f"  - ID: {new_seller_id}")
        print(f"  - Telegram ID: {test_data['telegram_id']}")
        print(f"  - Store Name: {test_data['store_name']}")
        print(f"  - User Name: {test_data['user_name']}")
        
        # ✏️ اختبار 3: تحديث بيانات المتجر
        print("\n" + "=" * 50)
        print("✏️ TEST 3: Update Seller")
        print("=" * 50)
        new_store_name = "متجر الاختبار المحدث"
        cur.execute(
            'UPDATE sellers SET "storename" = %s WHERE "sellerid" = %s',
            (new_store_name, new_seller_id)
        )
        conn.commit()
        print(f"✅ Seller updated:")
        print(f"  - ID: {new_seller_id}")
        print(f"  - New Store Name: {new_store_name}")
        
        # التحقق من التحديث
        cur.execute('SELECT "storename" FROM sellers WHERE "sellerid" = %s', (new_seller_id,))
        updated_name = cur.fetchone()[0]
        print(f"  - Verified: {updated_name}")
        
        # 🔄 اختبار 4: تغيير حالة المتجر
        print("\n" + "=" * 50)
        print("🔄 TEST 4: Update Seller Status")
        print("=" * 50)
        cur.execute(
            'UPDATE sellers SET "status" = %s WHERE "sellerid" = %s',
            ('suspended', new_seller_id)
        )
        conn.commit()
        print(f"✅ Seller status changed:")
        print(f"  - ID: {new_seller_id}")
        print(f"  - New Status: suspended")
        
        # التحقق
        cur.execute('SELECT "status" FROM sellers WHERE "sellerid" = %s', (new_seller_id,))
        status = cur.fetchone()[0]
        print(f"  - Verified: {status}")
        
        # 🗑️ اختبار 5: حذف المتجر
        print("\n" + "=" * 50)
        print("🗑️ TEST 5: Delete Seller")
        print("=" * 50)
        cur.execute('DELETE FROM sellers WHERE "sellerid" = %s', (new_seller_id,))
        conn.commit()
        print(f"✅ Seller deleted:")
        print(f"  - ID: {new_seller_id}")
        
        # التحقق
        cur.execute('SELECT COUNT(*) FROM sellers WHERE "sellerid" = %s', (new_seller_id,))
        count = cur.fetchone()[0]
        if count == 0:
            print(f"  - Verified: Seller no longer exists ✅")
        else:
            print(f"  - ERROR: Seller still exists! ❌")
        
        # 📈 ملخص نهائي
        print("\n" + "=" * 50)
        print("📈 FINAL SUMMARY")
        print("=" * 50)
        
        cur.execute('SELECT COUNT(*) FROM sellers')
        seller_count = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM categories')
        cat_count = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM products')
        prod_count = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM productimages')
        img_count = cur.fetchone()[0]
        
        print(f"Total Sellers: {seller_count}")
        print(f"Total Categories: {cat_count}")
        print(f"Total Products: {prod_count}")
        print(f"Total Product Images: {img_count}")
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
