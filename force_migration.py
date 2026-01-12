#!/usr/bin/env python3
"""
سكريبت لتطبيق Migration بشكل إجباري على قاعدة البيانات PostgreSQL
يجب تشغيله مرة واحدة فقط بعد تحديث الكود
"""
import os
from dotenv import load_dotenv
import psycopg2
import urllib.parse

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment variables!")
    print("⚠️ This script only works with PostgreSQL (Cloud)")
    exit(1)

try:
    result = urllib.parse.urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    
    conn = psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔄 Applying BIGINT Migration to PostgreSQL Database")
    print("=" * 60)
    
    migrations = [
        ("Users", "TelegramID"),
        ("Sellers", "TelegramID"),
        ("CreditCustomers", "TelegramID"),
        ("Orders", "BuyerID"),
        ("Carts", "UserID"),
    ]
    
    for table_name, column_name in migrations:
        try:
            # Check current type
            cursor.execute(f"""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='{table_name.lower()}' AND column_name='{column_name.lower()}'
            """)
            result = cursor.fetchone()
            
            if result:
                current_type = result[0].upper()
                print(f"\n📊 {table_name}.{column_name}: {current_type}")
                
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"   🔄 Migrating to BIGINT...")
                    cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                    conn.commit()
                    print(f"   ✅ Successfully migrated to BIGINT")
                else:
                    print(f"   ✅ Already BIGINT")
            else:
                print(f"\n⚠️ {table_name}.{column_name}: Column not found!")
        except Exception as e:
            print(f"\n❌ Error migrating {table_name}.{column_name}: {e}")
            try:
                conn.rollback()
            except:
                pass
    
    # Verify all migrations
    print("\n" + "=" * 60)
    print("📋 Verification - Current Column Types:")
    print("=" * 60)
    
    cursor.execute("""
        SELECT 
            table_name, 
            column_name, 
            data_type 
        FROM information_schema.columns 
        WHERE column_name IN ('telegramid', 'buyerid', 'userid')
            AND table_name IN ('users', 'sellers', 'creditcustomers', 'orders', 'carts')
        ORDER BY table_name, column_name
    """)
    
    results = cursor.fetchall()
    for table_name, column_name, data_type in results:
        status = "✅" if data_type.upper() in ('BIGINT', 'INT8') else "❌"
        print(f"{status} {table_name}.{column_name}: {data_type}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Migration completed!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
