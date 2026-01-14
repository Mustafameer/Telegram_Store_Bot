#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database functions
from bot import get_db_connection, get_all_credit_customers, CursorWrapper, IS_POSTGRES

print("=" * 60)
print("Testing Database Functions")
print("=" * 60)

# Test 1: Check if database has any credit customers
print("\n[TEST 1] Checking CreditCustomers table...")
conn = get_db_connection()
cursor = conn.cursor()
cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)

try:
    if IS_POSTGRES:
        cursor_wrapper.execute("SELECT COUNT(*) FROM CreditCustomers")
    else:
        cursor_wrapper.execute("SELECT COUNT(*) FROM CreditCustomers")
    result = cursor_wrapper.fetchone()
    print(f"Total CreditCustomers in database: {result[0]}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Get all sellers
print("\n[TEST 2] Checking sellers...")
try:
    if IS_POSTGRES:
        cursor_wrapper.execute("SELECT SellerID, TelegramID FROM Sellers LIMIT 5")
    else:
        cursor_wrapper.execute("SELECT SellerID, TelegramID FROM Sellers LIMIT 5")
    sellers = cursor_wrapper.fetchall()
    print(f"Found {len(sellers)} sellers:")
    for seller in sellers:
        print(f"  - SellerID={seller[0]}, TelegramID={seller[1]}")
    
    # Test 3: Get credit customers for each seller
    for seller in sellers:
        seller_id = seller[0]
        print(f"\n[TEST 3.{seller_id}] Getting credit customers for SellerID={seller_id}...")
        
        # Call the function directly
        customers = get_all_credit_customers(seller_id)
        print(f"get_all_credit_customers() returned: {type(customers)}")
        print(f"Number of customers: {len(customers) if customers else 0}")
        if customers:
            for customer in customers:
                print(f"  Customer: {customer}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

print("\n" + "=" * 60)
print("Testing Completed")
print("=" * 60)
