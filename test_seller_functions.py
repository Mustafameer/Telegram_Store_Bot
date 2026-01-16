#!/usr/bin/env python3
"""
اختبار شامل لدوال إدارة المتاجر
Test comprehensive seller management functions
"""

import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

def test_sellers():
    """اختبار دوال إدارة المتاجر"""
    
    # بيانات الاتصال
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("❌ DATABASE_URL not set in .env")
        return False
    
    try:
        # الاتصال بقاعدة البيانات
        conn = psycopg2.connect(db_url, sslmode='require')
        cur = conn.cursor()
        print("✅ Connected to database")
        
        # 1. اختبار جلب جميع المتاجر
        print("\n📊 Testing: Get All Sellers")
        cur.execute('SELECT "sellerid", "telegramid", "storename", "status" FROM "Sellers"')
        sellers = cur.fetchall()
        print(f"Found {len(sellers)} sellers:")
        for seller in sellers:
            print(f"  - ID: {seller[0]}, Telegram: {seller[1]}, Name: {seller[2]}, Status: {seller[3]}")
        
        # 2. اختبار إضافة متجر جديد
        print("\n➕ Testing: Add New Seller")
        test_telegram_id = 999888777
        test_store_name = "متجر اختبار"
        test_user_name = "اختبار المستخدم"
        
        cur.execute(
            '''INSERT INTO "Sellers" ("telegramid", "storename", "username", "requirecustomerregistration", "status")
               VALUES (%s, %s, %s, %s, %s)
               RETURNING "sellerid"''',
            (test_telegram_id, test_store_name, test_user_name, 0, 'active')
        )
        new_seller_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ New seller created: ID={new_seller_id}, Telegram={test_telegram_id}, Name={test_store_name}")
        
        # 3. اختبار تحديث متجر
        print("\n✏️ Testing: Update Seller")
        updated_name = "متجر اختبار محدث"
        cur.execute(
            'UPDATE "Sellers" SET "storename" = %s WHERE "sellerid" = %s',
            (updated_name, new_seller_id)
        )
        conn.commit()
        print(f"✅ Seller updated: ID={new_seller_id}, New Name={updated_name}")
        
        # 4. اختبار تغيير حالة المتجر
        print("\n🔄 Testing: Update Seller Status")
        cur.execute(
            'UPDATE "Sellers" SET "status" = %s WHERE "sellerid" = %s',
            ('suspended', new_seller_id)
        )
        conn.commit()
        print(f"✅ Seller status updated: ID={new_seller_id}, New Status=suspended")
        
        # التحقق من التحديث
        cur.execute('SELECT "status" FROM "Sellers" WHERE "sellerid" = %s', (new_seller_id,))
        status = cur.fetchone()[0]
        print(f"   Verified status: {status}")
        
        # 5. اختبار حذف المتجر
        print("\n🗑️ Testing: Delete Seller")
        cur.execute('DELETE FROM "Sellers" WHERE "sellerid" = %s', (new_seller_id,))
        conn.commit()
        print(f"✅ Seller deleted: ID={new_seller_id}")
        
        # التحقق من الحذف
        cur.execute('SELECT COUNT(*) FROM "Sellers" WHERE "sellerid" = %s', (new_seller_id,))
        count = cur.fetchone()[0]
        if count == 0:
            print(f"   Verified deletion: Seller no longer exists")
        
        # 6. ملخص البيانات النهائي
        print("\n📈 Final Summary:")
        cur.execute('SELECT COUNT(*) FROM "Sellers"')
        seller_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Categories"')
        category_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Products"')
        product_count = cur.fetchone()[0]
        
        print(f"  Total Sellers: {seller_count}")
        print(f"  Total Categories: {category_count}")
        print(f"  Total Products: {product_count}")
        
        # إغلاق الاتصال
        cur.close()
        conn.close()
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    test_sellers()
