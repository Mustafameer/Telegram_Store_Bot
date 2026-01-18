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
    
    print("🔍 فحص صحة قاعدة البيانات:\n")
    
    # 1. Check for slow queries
    print("📊 1. فحص الـ slow queries:")
    cur.execute("""
        SELECT pid, usename, query, query_start, state
        FROM pg_stat_activity
        WHERE state != 'idle'
        ORDER BY query_start ASC
        LIMIT 10
    """)
    
    active_queries = cur.fetchall()
    if active_queries:
        print(f"   ⚠️ عدد الـ active queries: {len(active_queries)}")
        for pid, user, query, start, state in active_queries:
            if start:
                elapsed = (time.time() - start.timestamp())
                print(f"      - PID {pid}: {elapsed:.1f}s - {query[:50]}...")
    else:
        print("   ✅ لا توجد queries فعّالة")
    
    # 2. Check table sizes and indexes
    print("\n📦 2. أحجام الجداول والـ indexes:")
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 15
    """)
    
    tables = cur.fetchall()
    for schema, table, size in tables:
        print(f"   - {table}: {size}")
    
    # 3. Check for locks
    print("\n🔒 3. فحص الـ locks:")
    cur.execute("""
        SELECT l.pid, l.mode, a.usename, a.query
        FROM pg_locks l
        JOIN pg_stat_activity a ON l.pid = a.pid
        WHERE l.mode != 'AccessShareLock'
        LIMIT 10
    """)
    
    locks = cur.fetchall()
    if locks:
        print(f"   ⚠️ وجدت {len(locks)} locks:")
        for pid, mode, user, query in locks:
            print(f"      - PID {pid}: {mode}")
    else:
        print("   ✅ لا توجد locks مشبوهة")
    
    # 4. Check database connections
    print("\n📡 4. عدد الاتصالات:")
    cur.execute("SELECT COUNT(*) FROM pg_stat_activity")
    conn_count = cur.fetchone()[0]
    print(f"   {conn_count} اتصال نشط")
    
    # 5. Check cache hit ratio
    print("\n💾 5. نسبة الـ cache:")
    cur.execute("""
        SELECT 
            ROUND(sum(heap_blks_read)::numeric / (sum(heap_blks_read) + sum(heap_blks_hit)) * 100, 2) as cache_hit_ratio
        FROM pg_statio_user_tables
    """)
    
    ratio = cur.fetchone()[0]
    if ratio:
        print(f"   Cache Hit Ratio: {ratio}% (يجب أن يكون > 90%)")
        if float(ratio) < 90:
            print("   ⚠️ نسبة الـ cache منخفضة!")
    
    conn.close()
    print("\n✅ الفحص اكتمل")
except Exception as e:
    print(f'❌ خطأ: {e}')
    import traceback
    traceback.print_exc()
