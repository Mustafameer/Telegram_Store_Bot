#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Get all sellers
    cur.execute('SELECT * FROM sellers')
    sellers = cur.fetchall()
    print(f"=== SELLERS ({len(sellers)} total) ===")
    for seller in sellers:
        print(f"  {seller}")
    
    print("\n=== CREDIT CUSTOMERS ===")
    
    # Get column names from creditcustomers
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='creditcustomers' ORDER BY ordinal_position")
    cols = [row[0] for row in cur.fetchall()]
    print(f"Columns: {cols}\n")
    
    # Get all credit customers
    cur.execute("SELECT * FROM creditcustomers ORDER BY \"SellerID\"")
    customers = cur.fetchall()
    print(f"Total customers: {len(customers)}")
    for cust in customers:
        print(f"  {cust}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
