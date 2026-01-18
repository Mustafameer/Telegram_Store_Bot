#!/usr/bin/env python3
import psycopg2
import time
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🔍 فحص قاعدة البيانات في Railway:\n")
    
    # List all tables with row counts
    cur.execute("""
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND t.table_name = table_name) as col_count
        FROM information_schema.tables t
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    print(f"📊 الجداول الموجودة ({len(tables)}):")
    
    for table_name, col_count in tables:
        start = time.time()
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cur.fetchone()[0]
            elapsed = time.time() - start
            status = "⚡ سريع" if elapsed < 0.5 else "⏱️ بطيء" if elapsed < 2 else "🐢 جداً بطيء"
            print(f"   - {table_name}: {count} صف ({elapsed:.2f}s) {status}")
        except Exception as e:
            print(f"   - {table_name}: ❌ خطأ في العد - {str(e)[:50]}")
    
    # Check connection status
    print("\n📡 معلومات الاتصال:")
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"   PostgreSQL: {version[:50]}...")
    
    # Check database size
    cur.execute("SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) as size FROM pg_database WHERE datname = current_database()")
    db_info = cur.fetchone()
    if db_info:
        print(f"   Database: {db_info[0]} - Size: {db_info[1]}")
    
    conn.close()
    print("\n✅ الاتصال سليم")
except Exception as e:
    print(f'❌ خطأ في الاتصال: {e}')
    import traceback
    traceback.print_exc()
