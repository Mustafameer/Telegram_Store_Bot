#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت سريع لتطبيق Migration على Railway PostgreSQL
استخدم هذا السكريبت إذا كان لديك معلومات الاتصال
"""
import sys
import psycopg2

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ====== معلومات الاتصال ======
HOST = "switchback.proxy.rlwy.net"
PORT = 20266
DATABASE = "railway"
USERNAME = "postgres"
PASSWORD = "bqcTJxNXLgwOftDoarrtmjmjYWurEIEh"

def apply_migration():
    """تطبيق Migration بشكل إجباري"""
    
    if not PASSWORD:
        print("[ERROR] يرجى إدخال PASSWORD في السكريبت أولاً!")
        print("   افتح ملف apply_migration_railway.py وأدخل كلمة المرور في السطر 12")
        return False
    
    try:
        print("=" * 60)
        print("[INFO] Connecting to Railway PostgreSQL...")
        print(f"Host: {HOST}")
        print(f"Port: {PORT}")
        print(f"Database: {DATABASE}")
        print("=" * 60)
        
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD,
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("[MIGRATION] APPLYING BIGINT MIGRATIONS")
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
                    print(f"\n[CHECK] {table_name}.{column_name}: {current_type}")
                    
                    if current_type not in ('BIGINT', 'INT8'):
                        print(f"   [MIGRATE] Migrating to BIGINT...")
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                        conn.commit()
                        print(f"   [SUCCESS] Successfully migrated to BIGINT")
                        results.append(f"[OK] {table_name}.{column_name}: {current_type} -> BIGINT")
                    else:
                        print(f"   [SKIP] Already BIGINT")
                        results.append(f"[OK] {table_name}.{column_name}: Already BIGINT")
                else:
                    print(f"[WARNING] Column not found!")
                    results.append(f"[WARN] {table_name}.{column_name}: Column not found")
            except Exception as e:
                print(f"[ERROR] Error: {e}")
                import traceback
                traceback.print_exc()
                results.append(f"[FAIL] {table_name}.{column_name}: {str(e)}")
                try:
                    conn.rollback()
                except:
                    pass
        
        # Verify all migrations
        print("\n" + "=" * 60)
        print("[VERIFY] Current Column Types:")
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
            status = "[OK]" if data_type.upper() in ('BIGINT', 'INT8') else "[FAIL]"
            print(f"{status} {table_name}.{column_name}: {data_type}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] MIGRATION COMPLETED")
        print("=" * 60)
        print("\n[SUMMARY] Results:")
        for result in results:
            print(f"  {result}")
        
        # Check if all migrations succeeded
        all_bigint = all(
            data_type.upper() in ('BIGINT', 'INT8') 
            for _, _, data_type in verification_results
        )
        
        if all_bigint:
            print("\n[SUCCESS] All columns are now BIGINT! Migration successful!")
            return True
        else:
            print("\n[WARNING] Some columns may not be BIGINT. Please check the results above.")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = apply_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
