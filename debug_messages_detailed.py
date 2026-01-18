#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import psycopg2
import json
from datetime import datetime

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    print("=" * 60)
    print("DEBUG: مشكلة عدم وصول الرسائل للتطبيق")
    print("=" * 60)
    
    # 1. التحقق من جداول البيانات المتاحة
    print("\n1️⃣ جداول البيانات المتاحة:")
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    for table in tables:
        print(f"   ✓ {table[0]}")
    
    # 2. التحقق من وجود جدول messages
    print("\n2️⃣ فحص جدول messages:")
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'messages'
        );
    """)
    messages_exists = cur.fetchone()[0]
    print(f"   جدول messages موجود: {messages_exists}")
    
    if messages_exists:
        # 3. عدد الرسائل الإجمالي
        cur.execute('SELECT COUNT(*) FROM messages')
        total_msgs = cur.fetchone()[0]
        print(f"\n3️⃣ إجمالي الرسائل: {total_msgs}")
        
        if total_msgs > 0:
            # 4. عرض آخر 5 رسائل
            print("\n4️⃣ آخر 5 رسائل:")
            cur.execute("""
                SELECT messageid, orderid, sellerid, messagetype, 
                       messagetext, isread, createdat
                FROM messages 
                ORDER BY messageid DESC 
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                msg_id, order_id, seller_id, msg_type, msg_text, is_read, created = row
                print(f"\n   📬 Message ID: {msg_id}")
                print(f"      Order ID: {order_id}")
                print(f"      Seller ID: {seller_id}")
                print(f"      Type: {msg_type}")
                print(f"      Text: {msg_text[:50] if msg_text else 'None'}...")
                print(f"      Read: {is_read}")
                print(f"      Created: {created}")
            
            # 5. عدد الرسائل لكل بائع
            print("\n5️⃣ عدد الرسائل لكل بائع:")
            cur.execute("""
                SELECT sellerid, COUNT(*) as count 
                FROM messages 
                GROUP BY sellerid
                ORDER BY count DESC
            """)
            
            for seller_id, count in cur.fetchall():
                print(f"   Seller {seller_id}: {count} رسالة")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
