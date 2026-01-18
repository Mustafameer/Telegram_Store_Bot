#!/usr/bin/env python3
"""
تحديث متجر ليكون مغلق (RequireCustomerRegistration = 1)
Update store to be closed
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

IS_POSTGRES = os.environ.get('DATABASE_URL') is not None

def update_store_to_closed(seller_id):
    """تحديث متجر ليكون مغلق"""
    if IS_POSTGRES:
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print(f"🔍 التحقق من المتجر {seller_id}...")
        cursor.execute('SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) FROM "sellers" WHERE "sellerid"=%s', (seller_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ وجدنا: {result}")
            print(f"🔄 تحديث المتجر ليكون مغلق...")
            cursor.execute('UPDATE "sellers" SET "RequireCustomerRegistration"=1 WHERE "sellerid"=%s', (seller_id,))
            conn.commit()
            print(f"✅ تم تحديث المتجر {seller_id} ليكون مغلق!")
        else:
            print(f"❌ لم يتم العثور على المتجر {seller_id}")
        
        cursor.close()
        conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect('data/store.db')
        cursor = conn.cursor()
        
        print(f"🔍 التحقق من المتجر {seller_id}...")
        cursor.execute('SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) FROM Sellers WHERE SellerID=?', (seller_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ وجدنا: {result}")
            print(f"🔄 تحديث المتجر ليكون مغلق...")
            cursor.execute('UPDATE Sellers SET RequireCustomerRegistration=1 WHERE SellerID=?', (seller_id,))
            conn.commit()
            print(f"✅ تم تحديث المتجر {seller_id} ليكون مغلق!")
        else:
            print(f"❌ لم يتم العثور على المتجر {seller_id}")
        
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("⚠️ الرجاء تحديد معرف المتجر")
        print("Usage: python update_store_to_closed.py <seller_id>")
        sys.exit(1)
    
    seller_id = int(sys.argv[1])
    update_store_to_closed(seller_id)
