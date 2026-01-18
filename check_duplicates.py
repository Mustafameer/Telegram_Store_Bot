#!/usr/bin/env python3
"""
Check database state and fix any duplicate Telegram IDs
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("🔍 Checking Sellers table for duplicate Telegram IDs...")
        cursor.execute("""
            SELECT StoreName, SellerID, TelegramID 
            FROM Sellers 
            WHERE TelegramID IS NOT NULL
            ORDER BY TelegramID
        """)
        
        sellers = cursor.fetchall()
        print(f"\n📊 Total sellers with TelegramID: {len(sellers)}\n")
        
        for store, seller_id, tg_id in sellers:
            print(f"  Store: {store:20} | SellerID: {seller_id:3} | TelegramID: {tg_id}")
        
        # Check for duplicates
        cursor.execute("""
            SELECT TelegramID, COUNT(*) as count
            FROM Sellers
            WHERE TelegramID IS NOT NULL
            GROUP BY TelegramID
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"\n⚠️  FOUND DUPLICATES ({len(duplicates)} TelegramID(s) used multiple times):")
            for tg_id, count in duplicates:
                print(f"  TelegramID {tg_id}: used {count} times")
                
                cursor.execute("""
                    SELECT StoreName, SellerID 
                    FROM Sellers 
                    WHERE TelegramID = %s
                """, (tg_id,))
                
                stores = cursor.fetchall()
                for store, seller_id in stores:
                    print(f"    - {store} (SellerID: {seller_id})")
        else:
            print("\n✅ No duplicate Telegram IDs found!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
else:
    print("❌ DATABASE_URL not set")
