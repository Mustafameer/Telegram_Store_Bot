#!/usr/bin/env python3
"""اختبر إذا كان جدول Notifications موجود وبيانات صحيحة"""

import os
from dotenv import load_dotenv

load_dotenv()

# Check if PostgreSQL is available
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set - using SQLite")
    import sqlite3
    conn = sqlite3.connect('data/store.db')
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Notifications'")
    result = cursor.fetchone()
    
    if result:
        print("✅ جدول Notifications موجود في SQLite")
        
        # Count notifications
        cursor.execute("SELECT COUNT(*) FROM Notifications")
        count = cursor.fetchone()[0]
        print(f"📊 عدد الإشعارات: {count}")
        
        # Show latest notifications
        cursor.execute("SELECT * FROM Notifications ORDER BY CreatedAt DESC LIMIT 5")
        rows = cursor.fetchall()
        
        print("\n📋 آخر 5 إشعارات:")
        for row in rows:
            print(f"  - {row}")
    else:
        print("❌ جدول Notifications لا يوجد في SQLite!")
    
    conn.close()

else:
    print("✅ استخدام PostgreSQL (Railway Cloud)")
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse DATABASE_URL
        url = urlparse(DATABASE_URL)
        
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port or 5432
        )
        
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'Notifications'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✅ جدول Notifications موجود في PostgreSQL")
            
            # Count notifications
            cursor.execute('SELECT COUNT(*) FROM "Notifications"')
            count = cursor.fetchone()[0]
            print(f"📊 عدد الإشعارات: {count}")
            
            # Show latest notifications
            cursor.execute('SELECT * FROM "Notifications" ORDER BY "CreatedAt" DESC LIMIT 5')
            rows = cursor.fetchall()
            
            print("\n📋 آخر 5 إشعارات:")
            for row in rows:
                print(f"  - ID: {row[0]}, CustomerID: {row[1]}, Type: {row[3]}, Title: {row[4]}")
        else:
            print("❌ جدول Notifications لا يوجد في PostgreSQL!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
