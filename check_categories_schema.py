#!/usr/bin/env python3
"""
التحقق من schema جدول Categories
"""

import sys
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# محاولة الاتصال بـ PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        # عرض schema جدول Categories
        cursor.execute("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'categories'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print("📊 Schema جدول Categories في PostgreSQL:")
        print("=" * 80)
        
        if columns:
            for col_name, data_type, default, nullable in columns:
                default_str = str(default) if default else "NULL"
                print(f"  {col_name:20} | {data_type:15} | Default: {default_str:30} | Nullable: {nullable}")
        else:
            print("❌ جدول Categories غير موجود!")
        
        # عرض جميع الأعمدة
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        print(f"\n📈 عدد الصفوف: {count}")
        
        # عرض أول 5 صفوف
        cursor.execute("SELECT categoryid, sellerid, name FROM categories LIMIT 5")
        rows = cursor.fetchall()
        print("\n📋 أول 5 فئات:")
        for row in rows:
            print(f"  ID: {row[0]:3} | SellerID: {row[1]:3} | Name: {row[2]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️ DATABASE_URL غير محدد")
