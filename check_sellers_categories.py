#!/usr/bin/env python3
"""
التحقق من الفئات لكل بائع
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔍 الفئات المرتبطة بكل بائع")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # البحث عن البائعين
    cursor.execute("SELECT sellerid, telegramid, storename FROM sellers ORDER BY sellerid")
    sellers = cursor.fetchall()
    
    print(f"\n🏪 البائعون ({len(sellers)}):")
    
    for seller_id, tg_id, store_name in sellers:
        print(f"\n   📦 ID: {seller_id}, Telegram: {tg_id}")
        print(f"      Store: {store_name}")
        
        # الفئات لهذا البائع
        cursor.execute(
            "SELECT categoryid, name FROM categories WHERE sellerid = %s ORDER BY categoryid",
            (seller_id,)
        )
        categories = cursor.fetchall()
        
        if categories:
            print(f"      ✅ عدد الفئات: {len(categories)}")
            for cat_id, cat_name in categories:
                print(f"         - {cat_name} (ID: {cat_id})")
        else:
            print(f"      ⚠️  لا توجد فئات")
    
    conn.close()
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
