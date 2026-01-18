#!/usr/bin/env python3
"""
إعادة بناء كاملة لقاعدة البيانات بأسماء الأعمدة الصحيحة
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔄 إعادة بناء كاملة لقاعدة البيانات")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Drop all tables in reverse order of dependencies
    print("\n📍 حذف الجداول القديمة...")
    tables_to_drop = [
        'AuctionBidders', 'AuctionBids', 'AuctionResults', 'AuctionProducts', 
        'Auctions', 'Returns', 'OrderItems', 'Orders', 'Carts',
        'Products', 'Categories', 'CreditCustomers', 'CreditLimits', 'CustomCredit',
        'Messages', 'ImageStorage', 'FeatureFlags', 'Users', 'Sellers'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            print(f"   ✅ حذفت {table}")
        except:
            pass
    
    conn.commit()
    print("\n✅ تم حذف جميع الجداول")
    
    # Now run initialization script
    print("\n📍 إنشاء الجداول الجديدة...")
    print("   ⏳ يرجى الانتظار...")
    
    # Import bot and initialize
    from bot import initialize_database
    initialize_database()
    
    print("\n✅ تم إنشاء جميع الجداول بنجاح بأسماء الأعمدة الصحيحة!")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
