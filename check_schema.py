#!/usr/bin/env python3
"""
فحص أسماء الجداول والأعمدة في قاعدة البيانات
Check table and column names in the database
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_database_schema():
    """فحص المخطط الأساسي للقاعدة"""
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    try:
        conn = psycopg2.connect(db_url, sslmode='require')
        cur = conn.cursor()
        print("✅ Connected to database\n")
        
        # 1. جلب جميع الجداول
        print("📋 All Tables:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        for table in tables:
            table_name = table[0]
            print(f"\n📊 Table: {table_name}")
            
            # جلب الأعمدة
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            for col in columns:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"    - {col[0]} ({col[1]}) {nullable}")
            
            # عدد الصفوف
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cur.fetchone()[0]
            print(f"    Rows: {row_count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_database_schema()
