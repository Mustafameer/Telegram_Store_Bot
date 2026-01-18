#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    print("=== MESSAGES TABLE ===\n")
    
    # Get all messages
    cur.execute('SELECT * FROM messages ORDER BY messageid DESC LIMIT 10')
    messages = cur.fetchall()
    
    if not messages:
        print("❌ لا توجد رسائل في قاعدة البيانات")
    else:
        # Get column names
        col_names = [desc[0] for desc in cur.description]
        print(f"الأعمدة: {col_names}\n")
        
        print(f"آخر {len(messages)} رسائل:")
        for msg in messages:
            print(f"\n📬 الرسالة:")
            for i, col in enumerate(col_names):
                print(f"   {col}: {msg[i]}")
    
    # Check by seller
    print("\n\n=== عدد الرسائل لكل بائع ===")
    cur.execute('SELECT sellerid, COUNT(*) as count FROM messages GROUP BY sellerid')
    seller_msgs = cur.fetchall()
    for seller_id, count in seller_msgs:
        print(f"   Seller {seller_id}: {count} رسالة")
    
    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
