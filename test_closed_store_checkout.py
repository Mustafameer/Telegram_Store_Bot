#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for closed store checkout flow
Tests the new immediate order creation for registered customers
"""

import sqlite3
import os
from datetime import datetime

# Test database
DB_PATH = 'data/bot_storage.db'

def test_closed_store_checkout():
    """Test the closed store checkout flow"""
    print("=" * 60)
    print("🧪 Testing Closed Store Checkout Flow")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if TELEBOT store exists
        print("\n1️⃣  Checking for TELEBOT closed store...")
        cursor.execute("""
            SELECT SellerID, TelegramID, StoreName, RequireCustomerRegistration 
            FROM Sellers 
            WHERE TelegramID = 999999999
        """)
        telebot_seller = cursor.fetchone()
        
        if telebot_seller:
            seller_id, telegram_id, store_name, require_reg = telebot_seller
            print(f"✅ Found: {store_name} (ID: {seller_id})")
            print(f"   Telegram ID: {telegram_id}")
            print(f"   Require Registration: {require_reg}")
            print(f"   Closed Store: {require_reg == 1}")
        else:
            print("❌ TELEBOT store not found")
            return False
        
        # Check for test products in TELEBOT store
        print("\n2️⃣  Checking products in TELEBOT store...")
        cursor.execute("""
            SELECT COUNT(*) FROM Products WHERE SellerID = ?
        """, (seller_id,))
        product_count = cursor.fetchone()[0]
        print(f"✅ Found {product_count} products in TELEBOT store")
        
        # Check for registered customers
        print("\n3️⃣  Checking registered customers (CreditCustomers)...")
        cursor.execute("""
            SELECT CustomerID, TelegramID, FirstName, LastName, SellerID
            FROM CreditCustomers
            WHERE SellerID = ?
            LIMIT 5
        """, (seller_id,))
        
        customers = cursor.fetchall()
        if customers:
            print(f"✅ Found {len(customers)} registered customers:")
            for cust_id, tg_id, fname, lname, seller in customers:
                print(f"   - {fname} {lname} (Telegram: {tg_id})")
        else:
            print("⚠️  No registered customers found for TELEBOT store")
        
        # Check existing orders
        print("\n4️⃣  Checking existing orders for TELEBOT store...")
        cursor.execute("""
            SELECT COUNT(*), Status FROM Orders 
            WHERE SellerID = ?
            GROUP BY Status
        """, (seller_id,))
        
        order_stats = cursor.fetchall()
        if order_stats:
            print("✅ Order statistics:")
            for count, status in order_stats:
                print(f"   - Status '{status}': {count} orders")
        else:
            print("ℹ️  No orders found yet")
        
        # Check Carts
        print("\n5️⃣  Checking sample carts...")
        cursor.execute("""
            SELECT UserID, COUNT(*) as ItemCount
            FROM Carts
            GROUP BY UserID
            LIMIT 5
        """)
        
        carts = cursor.fetchall()
        if carts:
            print(f"✅ Found {len(carts)} users with items in cart:")
            for user_id, item_count in carts:
                print(f"   - User {user_id}: {item_count} items")
        else:
            print("ℹ️  No carts found")
        
        print("\n" + "=" * 60)
        print("✅ Database structure is ready for closed store checkout!")
        print("=" * 60)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_functions_exist():
    """Check if required functions exist in bot.py"""
    print("\n" + "=" * 60)
    print("🔍 Checking required functions in bot.py")
    print("=" * 60)
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        functions = [
            'create_confirmed_order_for_closed_store',
            'clear_cart_db',
            'get_seller_by_id',
            'is_customer_registered_for_store_by_telegram_id',
            'create_order',
            'get_user',
            'get_cart_items_db',
            'handle_checkout_cart'
        ]
        
        print("\n✓ Required functions:")
        for func in functions:
            if f'def {func}(' in content:
                print(f"  ✅ {func}")
            else:
                print(f"  ❌ {func}")
        
        # Check for the new closed store logic in handle_checkout_cart
        if 'all_sellers_closed' in content and 'create_confirmed_order_for_closed_store' in content:
            print("\n✅ New closed store checkout logic found in handle_checkout_cart")
        else:
            print("\n❌ New closed store checkout logic NOT found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading bot.py: {e}")
        return False

if __name__ == '__main__':
    print("\n🚀 Starting Closed Store Checkout Tests\n")
    
    # Run tests
    test_functions_exist()
    test_closed_store_checkout()
    
    print("\n📋 Manual Testing Instructions:")
    print("=" * 60)
    print("1. Register a test customer with /register command")
    print("2. Add items from TELEBOT (closed) store to cart")
    print("3. Click 'تأكيد الطلب' (Confirm Order)")
    print("4. Should see: '✅ تم إنزال طلبك بنجاح!'")
    print("5. Check that:")
    print("   - Order created with status='Confirmed'")
    print("   - Cart is cleared")
    print("   - Store owner received notification")
    print("=" * 60)
