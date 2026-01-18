#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار دقيق لمقارنة TelegramID المحفوظ مع TelegramID الزبون
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def compare_telegram_ids():
    """مقارنة دقيقة لـ TelegramIDs"""
    print("\n" + "="*80)
    print("🔎 مقارنة دقيقة لـ TelegramIDs للزبون حموداي في المتجر 21")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # احصل على بيانات الزبون
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID, CustomerType
            FROM CreditCustomers
            WHERE SellerID=21 AND FullName LIKE '%حمود%'
        """)
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, TelegramID, CustomerType
            FROM CreditCustomers
            WHERE SellerID=21 AND FullName LIKE '%حمود%'
        """)
    
    customer = cursor.fetchone()
    
    if customer:
        cust_id, name, stored_tele_id, cust_type = customer
        
        print(f"\n✅ وجدنا الزبون:")
        print(f"  الاسم: {name}")
        print(f"  CustomerID: {cust_id}")
        print(f"  CustomerType: {cust_type}")
        print(f"\n📊 معلومات TelegramID المحفوظة:")
        print(f"  القيمة: {stored_tele_id}")
        print(f"  النوع: {type(stored_tele_id).__name__}")
        print(f"  الطول: {len(str(stored_tele_id))}")
        print(f"  repr: {repr(stored_tele_id)}")
        
        # الآن اختبر البحث بقيم مختلفة
        test_values = [
            6619127767,
            "6619127767",
            6619127767.0,
        ]
        
        print(f"\n🧪 اختبار البحث بقيم مختلفة:")
        print("-"*80)
        
        for test_val in test_values:
            if IS_POSTGRES:
                cursor.execute("""
                    SELECT COUNT(*) FROM CreditCustomers
                    WHERE SellerID=21 AND TelegramID=%s
                """, (test_val,))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM CreditCustomers
                    WHERE SellerID=21 AND TelegramID=?
                """, (test_val,))
            
            count_result = cursor.fetchone()
            count = count_result[0] if count_result else 0
            
            match = "✅ نعم" if count > 0 else "❌ لا"
            print(f"\nالقيمة: {repr(test_val)}")
            print(f"  النوع: {type(test_val).__name__}")
            print(f"  المطابقة: {match} (عدد النتائج: {count})")
            
            # إذا لم تطابق، حاول مقارنة مباشرة
            if count == 0:
                print(f"  المقارنة: stored={repr(stored_tele_id)} vs test={repr(test_val)}")
                print(f"  متساوية؟ {stored_tele_id == test_val}")
    else:
        print(f"❌ لم نجد زبون يحتوي على 'حمود' في SellerID=21")
        
        # اعرض جميع الزبائن في SellerID=21
        if IS_POSTGRES:
            cursor.execute("""
                SELECT CustomerID, FullName, TelegramID
                FROM CreditCustomers
                WHERE SellerID=21
            """)
        else:
            cursor.execute("""
                SELECT CustomerID, FullName, TelegramID
                FROM CreditCustomers
                WHERE SellerID=21
            """)
        
        customers = cursor.fetchall()
        print(f"\n📋 جميع الزبائن في SellerID=21:")
        for cust_id, name, tele_id in customers:
            print(f"  - {name}: TelegramID={tele_id}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    compare_telegram_ids()
    print("\n" + "="*80)
