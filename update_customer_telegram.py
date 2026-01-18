#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحديث TelegramID للزبون حموداي
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def update_customer_telegram_id():
    """تحديث TelegramID للزبون"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    seller_id = 21
    old_telegram_id = 6941559294
    new_telegram_id = 6619127767
    
    print(f"\n{'='*80}")
    print(f"🔄 تحديث TelegramID للزبون حموداي")
    print(f"{'='*80}")
    
    print(f"\nBefore:")
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=%s AND TelegramID=%s
        """, (seller_id, old_telegram_id))
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=? AND TelegramID=?
        """, (seller_id, old_telegram_id))
    
    customer = cursor.fetchone()
    if customer:
        cust_id, name, tele_id = customer
        print(f"  CustomerID: {cust_id}")
        print(f"  الاسم: {name}")
        print(f"  TelegramID: {tele_id}")
    
    # التحديث
    print(f"\n🔄 جاري التحديث...")
    if IS_POSTGRES:
        cursor.execute("""
            UPDATE CreditCustomers
            SET TelegramID=%s
            WHERE SellerID=%s AND TelegramID=%s
        """, (new_telegram_id, seller_id, old_telegram_id))
    else:
        cursor.execute("""
            UPDATE CreditCustomers
            SET TelegramID=?
            WHERE SellerID=? AND TelegramID=?
        """, (new_telegram_id, seller_id, old_telegram_id))
    
    conn.commit()
    
    # التحقق من التحديث
    print(f"\nAfter:")
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=%s AND TelegramID=%s
        """, (seller_id, new_telegram_id))
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=? AND TelegramID=?
        """, (seller_id, new_telegram_id))
    
    customer = cursor.fetchone()
    if customer:
        cust_id, name, tele_id = customer
        print(f"  CustomerID: {cust_id}")
        print(f"  الاسم: {name}")
        print(f"  TelegramID: {tele_id}")
        print(f"\n✅ تم التحديث بنجاح!")
    else:
        print(f"❌ فشل التحديث!")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_customer_telegram_id()
    print(f"\n{'='*80}")
