"""
التحقق من هيكل جدول imagestorage والمشاكل
"""
import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
IS_POSTGRES = DATABASE_URL and 'postgres' in DATABASE_URL.lower()

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect('data/telegram_store.db')

def check_imagestorage():
    """التحقق من جدول imagestorage"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("=" * 50)
        if IS_POSTGRES:
            print("📊 PostgreSQL - جدول imagestorage")
            print("=" * 50)
            
            # البحث عن جدول imagestorage
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'imagestorage'
            """)
            table_exists = cursor.fetchone()
            print(f"✅ وجود الجدول: {bool(table_exists)}")
            
            if table_exists:
                # الأعمدة
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'imagestorage'
                    ORDER BY ordinal_position
                """)
                print("\n📋 الأعمدة:")
                for col_name, data_type, nullable in cursor.fetchall():
                    print(f"  - {col_name}: {data_type} (nullable: {nullable})")
                
                # الـ Foreign Keys
                cursor.execute("""
                    SELECT constraint_name, column_name, foreign_table_name, foreign_column_name
                    FROM information_schema.key_column_usage
                    WHERE table_name = 'imagestorage' AND foreign_table_name IS NOT NULL
                """)
                fks = cursor.fetchall()
                if fks:
                    print("\n🔗 Foreign Keys:")
                    for fk, col, ftable, fcol in fks:
                        print(f"  - {fk}: {col} → {ftable}.{fcol}")
                else:
                    print("\n⚠️ لا توجد Foreign Keys")
                
                # عدد الصور
                cursor.execute("SELECT COUNT(*) FROM imagestorage")
                count = cursor.fetchone()[0]
                print(f"\n📸 عدد الصور المحفوظة: {count}")
                
                # عينة من البيانات
                cursor.execute("SELECT * FROM imagestorage LIMIT 3")
                rows = cursor.fetchall()
                if rows:
                    print("\n📝 عينة من البيانات:")
                    for row in rows:
                        print(f"  {row}")
        
        else:
            print("📊 SQLite - جدول ImageStorage")
            print("=" * 50)
            
            # البحث عن جدول ImageStorage
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='ImageStorage'
            """)
            table_exists = cursor.fetchone()
            print(f"✅ وجود الجدول: {bool(table_exists)}")
            
            if table_exists:
                # الأعمدة
                cursor.execute("PRAGMA table_info(ImageStorage)")
                print("\n📋 الأعمدة:")
                for row in cursor.fetchall():
                    cid, name, type_, notnull, dflt, pk = row
                    print(f"  - {name}: {type_} (not null: {bool(notnull)}, PK: {bool(pk)})")
                
                # الـ Foreign Keys
                cursor.execute("PRAGMA foreign_key_list(ImageStorage)")
                fks = cursor.fetchall()
                if fks:
                    print("\n🔗 Foreign Keys:")
                    for row in fks:
                        print(f"  {row}")
                else:
                    print("\n⚠️ لا توجد Foreign Keys")
                
                # عدد الصور
                cursor.execute("SELECT COUNT(*) FROM ImageStorage")
                count = cursor.fetchone()[0]
                print(f"\n📸 عدد الصور المحفوظة: {count}")
                
                # عينة من البيانات
                cursor.execute("SELECT * FROM ImageStorage LIMIT 3")
                rows = cursor.fetchall()
                if rows:
                    print("\n📝 عينة من البيانات:")
                    for row in rows:
                        print(f"  {row}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_imagestorage()
