#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🗑️ جاري حذف الصور من قاعدة البيانات...\n")
    
    # Check current size
    cur.execute("SELECT COUNT(*) FROM imagestorage")
    old_count = cur.fetchone()[0]
    print(f"📊 عدد الصور الحالية: {old_count}")
    
    # Delete all images
    cur.execute("DELETE FROM imagestorage")
    conn.commit()
    
    # Check new size
    cur.execute("SELECT COUNT(*) FROM imagestorage")
    new_count = cur.fetchone()[0]
    
    # Check database size
    cur.execute("""
        SELECT pg_size_pretty(pg_database_size(current_database()))
    """)
    db_size = cur.fetchone()[0]
    
    print(f"✅ تم حذف {old_count - new_count} صورة")
    print(f"📦 حجم قاعدة البيانات الآن: {db_size}")
    print("\n💡 النصيحة: في المستقبل، استخدم cloud storage (S3, etc) بدلاً من تخزين الصور في قاعدة البيانات")
    
    conn.close()
except Exception as e:
    print(f'❌ خطأ: {e}')
    import traceback
    traceback.print_exc()
