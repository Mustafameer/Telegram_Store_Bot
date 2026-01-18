#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'CreditCustomers'
        );
    """)
    
    table_exists = cursor.fetchone()[0]
    print(f"📊 CreditCustomers table exists: {table_exists}")
    
    if table_exists:
        # Get all sellers
        cursor.execute('SELECT "SellerID", COUNT(*) as count FROM "CreditCustomers" GROUP BY "SellerID"')
        sellers_data = cursor.fetchall()
        print(f"\n👥 Credit customers by seller:")
        for seller_id, count in sellers_data:
            print(f"   Seller {seller_id}: {count} customers")
        
        # Get all credit customers
        cursor.execute('''
            SELECT "CustomerID", "SellerID", "FullName", "PhoneNumber", "TelegramID", "CreatedAt" 
            FROM "CreditCustomers" 
            ORDER BY "SellerID", "FullName"
        ''')
        
        customers = cursor.fetchall()
        print(f"\n📋 All credit customers ({len(customers)} total):")
        for cust in customers:
            print(f"   ID: {cust[0]}, Seller: {cust[1]}, Name: {cust[2]}, Phone: {cust[3]}, TelegramID: {cust[4]}, Created: {cust[5]}")
    
    cursor.close()
    conn.close()
    print("\n✅ Database check complete")

except Exception as e:
    print(f"❌ Error: {e}")
