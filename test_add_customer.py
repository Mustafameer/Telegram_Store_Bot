#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database functions
from bot import add_credit_customer, get_all_credit_customers, CursorWrapper, get_db_connection, IS_POSTGRES

print("=" * 60)
print("Testing Add Customer Function")
print("=" * 60)

# Test adding a customer for SellerID=11
seller_id = 11
full_name = "أحمد محمد"
telegram_id = 123456789

print(f"\n[TEST] Adding customer:")
print(f"  SellerID: {seller_id}")
print(f"  Full Name: {full_name}")
print(f"  Telegram ID: {telegram_id}")
print()

result = add_credit_customer(
    seller_id=seller_id, 
    full_name=full_name,
    phone_number=None,
    telegram_id=telegram_id
)

print(f"\nResult from add_credit_customer: {result}")
print(f"Result Type: {type(result)}")

if result and result > 0:
    print(f"✅ SUCCESS: Customer added with ID={result}")
    
    # Now try to retrieve it
    print("\n[TEST] Verifying customer was added...")
    customers = get_all_credit_customers(seller_id)
    print(f"Found {len(customers)} customers for SellerID={seller_id}:")
    for customer in customers:
        print(f"  {customer}")
else:
    print(f"❌ FAILED: add_credit_customer returned {result}")
    
    # Check if customer was actually added anyway
    print("\n[TEST] Checking database anyway...")
    customers = get_all_credit_customers(seller_id)
    print(f"Found {len(customers)} customers for SellerID={seller_id}:")
    for customer in customers:
        print(f"  {customer}")

print("\n" + "=" * 60)
print("Testing Completed")
print("=" * 60)
