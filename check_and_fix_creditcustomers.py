#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت للتحقق من CreditCustomers وإضافة TelegramID إذا لزم
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

def check_and_fix():
    """التحقق من CreditCustomers وإضافة TelegramID إذا لزم"""
    
    try:
        print("=" * 60)
        print("[INFO] Connecting to Railway PostgreSQL...")
        print("=" * 60)
        
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Check if table exists
        print("\n[CHECK] Checking if CreditCustomers table exists...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'creditcustomers'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("[ERROR] CreditCustomers table does not exist!")
            print("[INFO] Creating CreditCustomers table...")
            cursor.execute("""
                CREATE TABLE CreditCustomers(
                    CustomerID SERIAL PRIMARY KEY,
                    SellerID INTEGER,
                    FullName TEXT NOT NULL,
                    PhoneNumber TEXT,
                    TelegramID BIGINT,
                    CustomerType TEXT DEFAULT 'CreditCustomer',
                    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(SellerID, PhoneNumber),
                    FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
                )
            """)
            conn.commit()
            print("[SUCCESS] CreditCustomers table created with TelegramID BIGINT")
        else:
            print("[OK] CreditCustomers table exists")
            
            # Check if TelegramID column exists
            print("\n[CHECK] Checking if TelegramID column exists...")
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='creditcustomers' AND column_name='telegramid'
            """)
            result = cursor.fetchone()
            
            if not result:
                print("[INFO] TelegramID column does not exist. Adding it...")
                cursor.execute("ALTER TABLE CreditCustomers ADD COLUMN TelegramID BIGINT")
                conn.commit()
                print("[SUCCESS] TelegramID column added as BIGINT")
            else:
                col_name, data_type = result
                print(f"[CHECK] TelegramID column exists: {data_type}")
                
                if data_type.upper() not in ('BIGINT', 'INT8'):
                    print(f"[MIGRATE] Migrating TelegramID from {data_type} to BIGINT...")
                    cursor.execute("ALTER TABLE CreditCustomers ALTER COLUMN TelegramID TYPE BIGINT")
                    conn.commit()
                    print("[SUCCESS] TelegramID migrated to BIGINT")
                else:
                    print("[OK] TelegramID is already BIGINT")
        
        # Final verification
        print("\n" + "=" * 60)
        print("[VERIFY] Final Check:")
        print("=" * 60)
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='creditcustomers' 
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col_name, data_type in columns:
            print(f"  {col_name}: {data_type}")
        
        cursor.close()
        conn.close()
        
        print("\n[SUCCESS] Check and fix completed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = check_and_fix()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
