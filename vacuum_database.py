#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🧹 جاري تنظيف قاعدة البيانات...\n")
    
    # Run VACUUM FULL to reclaim space
    print("1️⃣ تشغيل VACUUM FULL...")
    cur.execute("VACUUM FULL")
    
    # Check database size
    cur.execute("""
        SELECT pg_size_pretty(pg_database_size(current_database()))
    """)
    db_size = cur.fetchone()[0]
    print(f"   ✅ تم تنظيف قاعدة البيانات")
    print(f"   📦 الحجم الجديد: {db_size}")
    
    # Analyze tables for better query planning
    print("\n2️⃣ تحديث إحصائيات الجداول...")
    cur.execute("ANALYZE")
    print("   ✅ تم تحديث الإحصائيات")
    
    conn.close()
    print("\n✅ اكتملت عملية التنظيف!")
except Exception as e:
    print(f'❌ خطأ: {e}')
    import traceback
    traceback.print_exc()
