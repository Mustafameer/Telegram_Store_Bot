#!/usr/bin/env python3
"""
أمر bot للتحقق والتحديث السريع
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

import sqlite3

def check_and_set_store():
    """التحقق من المتجر وتحديثه"""
    
    # استخدم نفس المسار من bot.py
    db_path = "data/store.db"
    
    if not os.path.exists(db_path):
        print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("🔍 فحص جميع المتاجر...")
    print("="*80)
    
    cursor.execute('''
        SELECT SellerID, StoreName, UserName, COALESCE(RequireCustomerRegistration, 0) as is_closed
        FROM Sellers
        ORDER BY SellerID
    ''')
    
    sellers = cursor.fetchall()
    
    if not sellers:
        print("❌ لا توجد متاجر!")
        cursor.close()
        conn.close()
        return
    
    for seller_id, store_name, username, is_closed in sellers:
        status = "🔒 مغلق" if is_closed == 1 else "🔓 مفتوح"
        print(f"  ID: {seller_id} | Store: {store_name} | User: {username} | {status}")
    
    print("\n" + "="*80)
    print("⚠️ لتحديث متجر ليكون مغلق، استخدم:")
    print("   python update_store_to_closed.py <seller_id>")
    print("="*80 + "\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_and_set_store()
