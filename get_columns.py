#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار بسيط جداً
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

conn = get_db_connection()
cursor = conn.cursor()

try:
    if IS_POSTGRES:
        # احصل على أسماء الأعمدة
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='sellers'
        """)
        cols = [row[0] for row in cursor.fetchall()]
        print("Sellers columns:", cols)
    else:
        cursor.execute("PRAGMA table_info(sellers)")
        cols = [row[1] for row in cursor.fetchall()]
        print("Sellers columns:", cols)
except Exception as e:
    print(f"Error: {e}")
finally:
    cursor.close()
    conn.close()
