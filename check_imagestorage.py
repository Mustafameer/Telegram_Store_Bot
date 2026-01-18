#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Check imagestorage structure
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'imagestorage'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    print('🔍 imagestorage الأعمدة:')
    for col in columns:
        print(f'   - {col[0]}: {col[1]}')
    
    # Check data
    cur.execute('SELECT COUNT(*) FROM imagestorage')
    count = cur.fetchone()[0]
    print(f'\n📊 عدد الصور: {count}')
    
    if count > 0:
        print('\n🖼️ الصور الموجودة:')
        cur.execute('SELECT imageid, filename, productid FROM imagestorage LIMIT 10')
        for row in cur.fetchall():
            print(f'   - ID: {row[0]}, الملف: {row[1]}, المنتج: {row[2]}')
    
    conn.close()
except Exception as e:
    print(f'❌ خطأ: {e}')
