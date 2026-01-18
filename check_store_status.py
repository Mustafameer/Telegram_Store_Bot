#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
التحقق من أي متاجر مغلقة
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def check_closed_stores():
    """التحقق من المتاجر المغلقة"""
    print("\n" + "="*80)
    print("🔍 فحص المتاجر المغلقة والمفتوحة")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT SellerID, StoreName, RequireCustomerRegistration, TelegramID
            FROM Sellers
            ORDER BY SellerID
        """)
    else:
        cursor.execute("""
            SELECT SellerID, StoreName, RequireCustomerRegistration, TelegramID
            FROM Sellers
            ORDER BY SellerID
        """)
    
    sellers = cursor.fetchall()
    
    if sellers:
        print(f"\n✅ وجدنا {len(sellers)} متجر:\n")
        for seller_id, store_name, require_reg, tele_id in sellers:
            status = "🔐 مغلق (يتطلب تسجيل)" if require_reg else "🔓 مفتوح"
            print(f"SellerID={seller_id}: {store_name}")
            print(f"  {status}")
            print(f"  TelegramID={tele_id}")
            print()
    
    # الآن تحقق من الزبون "رضاوي" في SellerID=21
    print("\n" + "="*80)
    print("🔎 التحقق من الزبون 'رضاوي' في SellerID=21")
    print("="*80)
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=21 AND FullName LIKE '%رضا%'
        """)
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID
            FROM CreditCustomers
            WHERE SellerID=21 AND FullName LIKE '%رضا%'
        """)
    
    customer = cursor.fetchone()
    
    if customer:
        cust_id, name, tele_id = customer
        print(f"\n✅ وجدنا الزبون:")
        print(f"  CustomerID={cust_id}")
        print(f"  الاسم={name}")
        print(f"  TelegramID={tele_id}")
        print(f"  SellerID=21")
        
        # تحقق من هل SellerID=21 مغلق؟
        if IS_POSTGRES:
            cursor.execute("""
                SELECT RequireCustomerRegistration
                FROM Sellers
                WHERE SellerID=21
            """)
        else:
            cursor.execute("""
                SELECT RequireCustomerRegistration
                FROM Sellers
                WHERE SellerID=21
            """)
        
        result = cursor.fetchone()
        if result:
            require_reg = result[0]
            print(f"\n  هل SellerID=21 مغلق؟ {require_reg}")
            if require_reg:
                print(f"  ✅ نعم، المتجر مغلق والزبون مسجل فيه!")
            else:
                print(f"  ❌ لا، المتجر مفتوح")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_closed_stores()
    print("\n" + "="*80)
