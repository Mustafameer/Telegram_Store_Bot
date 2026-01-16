#!/usr/bin/env python3
"""
اختبار سريع للتحقق من أن إضافة المتاجر تعمل
Quick test to verify seller management is working
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def quick_test():
    """اختبار سريع"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return
    
    try:
        conn = psycopg2.connect(db_url, sslmode='require')
        cur = conn.cursor()
        
        print("🔍 الاختبار السريع للمتاجر\n")
        
        # 1. عدد المتاجر الحالية
        cur.execute('SELECT COUNT(*) FROM sellers')
        count = cur.fetchone()[0]
        print(f"✅ عدد المتاجر الموجودة: {count}")
        
        # 2. إضافة متجر اختبار
        print("\n➕ محاولة إضافة متجر جديد...")
        test_id = 777888999
        test_name = f"متجر الاختبار {datetime.now().strftime('%H:%M:%S')}"
        
        cur.execute(
            '''INSERT INTO sellers ("telegramid", "storename", "status")
               VALUES (%s, %s, %s) RETURNING "sellerid"''',
            (test_id, test_name, 'active')
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ تم إضافة المتجر: ID={new_id}")
        
        # 3. التحقق من وجوده
        cur.execute('SELECT "storename" FROM sellers WHERE "sellerid" = %s', (new_id,))
        name = cur.fetchone()[0]
        print(f"✅ التحقق: المتجر موجود باسم '{name}'")
        
        # 4. حذفه
        cur.execute('DELETE FROM sellers WHERE "sellerid" = %s', (new_id,))
        conn.commit()
        print(f"✅ تم حذف المتجر")
        
        print("\n" + "="*40)
        print("✅ جميع الاختبارات نجحت!")
        print("="*40)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    quick_test()
