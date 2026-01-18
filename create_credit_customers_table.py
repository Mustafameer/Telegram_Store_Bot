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
    
    print("📋 Creating CreditCustomers table...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "CreditCustomers"(
            "CustomerID" SERIAL PRIMARY KEY,
            "SellerID" INTEGER,
            "FullName" TEXT NOT NULL,
            "PhoneNumber" TEXT,
            "TelegramID" BIGINT,
            "CustomerType" TEXT DEFAULT 'CreditCustomer',
            "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE("SellerID", "PhoneNumber"),
            FOREIGN KEY ("SellerID") REFERENCES "Sellers"("SellerID")
        )
    """)
    
    conn.commit()
    print("✅ CreditCustomers table created successfully")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
