#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Check database size
    cur.execute("""
        SELECT pg_size_pretty(pg_database_size(current_database()))
    """)
    db_size = cur.fetchone()[0]
    print(f"📦 حجم قاعدة البيانات: {db_size}")
    
    # Check imagestorage table size
    cur.execute("""
        SELECT pg_size_pretty(pg_total_relation_size('imagestorage'))
    """)
    img_size = cur.fetchone()[0]
    print(f"🖼️ حجم جدول imagestorage: {img_size}")
    
    conn.close()
except Exception as e:
    print(f'❌ خطأ: {e}')
