#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Test Script for Credit Customers System
اختبار سريع لنظام الزبائن الآجلين
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import (
    get_all_credit_customers, 
    add_credit_customer,
    get_db_connection,
    CursorWrapper,
    IS_POSTGRES
)

def test_database_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        conn = get_db_connection()
        print("✅ Database connection: SUCCESS")
        print(f"   Using: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
        
        cursor = conn.cursor()
        cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
        
        if IS_POSTGRES:
            cursor_wrapper.execute("SELECT COUNT(*) FROM CreditCustomers")
        else:
            cursor_wrapper.execute("SELECT COUNT(*) FROM CreditCustomers")
        
        count = cursor_wrapper.fetchone()[0]
        print(f"   Credit Customers in DB: {count}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection FAILED: {e}")
        return False


def test_get_customers():
    """Test retrieving customers"""
    print("\n" + "="*60)
    print("TEST 2: Get All Credit Customers")
    print("="*60)
    
    try:
        # Test for SellerID=10
        customers = get_all_credit_customers(10)
        print(f"✅ get_all_credit_customers(10): {len(customers)} customers")
        
        if customers:
            for customer in customers:
                print(f"   - {customer[2]} (ID={customer[0]})")
        
        # Test for SellerID=11
        customers = get_all_credit_customers(11)
        print(f"✅ get_all_credit_customers(11): {len(customers)} customers")
        
        return True
    except Exception as e:
        print(f"❌ get_all_credit_customers FAILED: {e}")
        return False


def test_add_customer():
    """Test adding a new customer"""
    print("\n" + "="*60)
    print("TEST 3: Add Credit Customer")
    print("="*60)
    
    try:
        result = add_credit_customer(
            seller_id=15,
            full_name="Test Customer",
            phone_number=None,
            telegram_id=999999999
        )
        
        if result and result > 0:
            print(f"✅ add_credit_customer: SUCCESS (ID={result})")
            
            # Verify
            customers = get_all_credit_customers(15)
            if customers:
                print(f"✅ Verification: Customer found in list")
                return True
            else:
                print(f"❌ Verification: Customer NOT found in list")
                return False
        else:
            print(f"❌ add_credit_customer FAILED: returned {result}")
            return False
    except Exception as e:
        print(f"❌ add_credit_customer FAILED: {e}")
        return False


def main():
    print("\n🚀 Credit Customers System - Quick Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Database Connection", test_database_connection()))
    results.append(("Get Customers", test_get_customers()))
    results.append(("Add Customer", test_add_customer()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests PASSED! System is ready!")
        return 0
    else:
        print("\n❌ Some tests FAILED. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
