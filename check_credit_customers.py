#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    # التحقق من وجود الجدول والأعمدة
    cur.execute('''
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'creditcustomers'
        ORDER BY ordinal_position
    ''')
    
    print('📋 CreditCustomers table structure:')
    for col in cur.fetchall():
        print(f'  - {col[0]}: {col[1]}')
    
    # عدد الزبائن الآجلين
    cur.execute('SELECT COUNT(*) FROM "CreditCustomers"')
    count = cur.fetchone()[0]
    print(f'\n📊 Total credit customers: {count}')
    
    # عرض أول 5 زبائن
    if count > 0:
        cur.execute('''
            SELECT "CustomerID", "SellerID", "FullName", "PhoneNumber", "CreditBalance" 
            FROM "CreditCustomers" 
            LIMIT 5
        ''')
        print('\n👥 Sample customers:')
        for row in cur.fetchall():
            print(f'  ID: {row[0]}, Seller: {row[1]}, Name: {row[2]}, Phone: {row[3]}, Balance: {row[4]}')
    
    cur.close()
    conn.close()
else:
    print('❌ DATABASE_URL not found')
