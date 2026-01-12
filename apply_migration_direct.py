#!/usr/bin/env python3
"""
سكريبت لتطبيق Migration بشكل مباشر على قاعدة البيانات PostgreSQL
يمكن تشغيله محلياً أو على Railway
"""
import os
import sys
import psycopg2
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migration():
    """تطبيق Migration بشكل إجباري"""
    
    # Try to get DATABASE_URL from environment first
    database_url = os.environ.get('DATABASE_URL')
    
    # If not found, ask user for connection details or use provided defaults
    if not database_url:
        print("=" * 60)
        print("🔧 Manual Database Connection")
        print("=" * 60)
        
        # Default Railway connection info
        default_host = "switchback.proxy.rlwy.net"
        default_port = "20266"
        default_database = "railway"
        
        print(f"\nمعلومات الاتصال الافتراضية (Railway):")
        print(f"Host: {default_host}")
        print(f"Port: {default_port}")
        print(f"Database: {default_database}")
        print("\nيرجى إدخال معلومات الاتصال:")
        
        host = input(f"Host (default: {default_host}): ").strip() or default_host
        port = input(f"Port (default: {default_port}): ").strip() or default_port
        database = input(f"Database (default: {default_database}): ").strip() or default_database
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        if not username or not password:
            print("❌ Username and Password are required!")
            return False
        
        try:
            print(f"\n🔄 Connecting to {host}:{port}/{database}...")
            conn = psycopg2.connect(
                host=host,
                port=int(port),
                database=database,
                user=username,
                password=password
            )
            print("✅ Connected successfully!")
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        # Parse DATABASE_URL
        try:
            result = urllib.parse.urlparse(database_url)
            username = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port or 5432
            
            print("=" * 60)
            print("🔧 Connecting using DATABASE_URL from environment")
            print(f"Host: {hostname}")
            print(f"Database: {database}")
            print("=" * 60)
            
            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                port=port
            )
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🔄 APPLYING BIGINT MIGRATIONS")
    print("=" * 60)
    
    migrations = [
        ("Users", "TelegramID"),
        ("Sellers", "TelegramID"),
        ("CreditCustomers", "TelegramID"),
        ("Orders", "BuyerID"),
        ("Carts", "UserID"),
    ]
    
    results = []
    for table_name, column_name in migrations:
        try:
            # Check current type
            cursor.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name=%s AND column_name=%s
            """, (table_name.lower(), column_name.lower()))
            result = cursor.fetchone()
            
            if result:
                current_type = result[0].upper()
                print(f"\n📊 {table_name}.{column_name}: {current_type}")
                
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"   🔄 Migrating to BIGINT...")
                    cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                    conn.commit()
                    print(f"   ✅ Successfully migrated to BIGINT")
                    results.append(f"✅ {table_name}.{column_name}: {current_type} → BIGINT")
                else:
                    print(f"   ✅ Already BIGINT")
                    results.append(f"✅ {table_name}.{column_name}: Already BIGINT")
            else:
                print(f"⚠️ Column not found!")
                results.append(f"⚠️ {table_name}.{column_name}: Column not found")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append(f"❌ {table_name}.{column_name}: {str(e)}")
            try:
                conn.rollback()
            except:
                pass
    
    # Verify all migrations
    print("\n" + "=" * 60)
    print("📋 VERIFICATION - Current Column Types:")
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
    
    verification_results = cursor.fetchall()
    for table_name, column_name, data_type in verification_results:
        status = "✅" if data_type.upper() in ('BIGINT', 'INT8') else "❌"
        print(f"{status} {table_name}.{column_name}: {data_type}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETED")
    print("=" * 60)
    print("\n📊 Summary:")
    for result in results:
        print(f"  {result}")
    
    # Check if all migrations succeeded
    all_bigint = all(
        data_type.upper() in ('BIGINT', 'INT8') 
        for _, _, data_type in verification_results
    )
    
    if all_bigint:
        print("\n🎉 All columns are now BIGINT! Migration successful!")
        return True
    else:
        print("\n⚠️ Some columns may not be BIGINT. Please check the results above.")
        return False

if __name__ == "__main__":
    try:
        success = apply_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
