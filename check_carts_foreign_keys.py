#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت للتحقق من Foreign Keys في جدول Carts والمشاكل المحتملة
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

def check_foreign_keys():
    """التحقق من Foreign Keys في جدول Carts"""
    
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
        
        # 1. Check Foreign Key constraints on Carts table
        print("\n" + "=" * 60)
        print("[CHECK] Foreign Key Constraints on Carts table:")
        print("=" * 60)
        
        cursor.execute("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'carts'
        """)
        
        fk_constraints = cursor.fetchall()
        if fk_constraints:
            for constraint_name, table_name, column_name, foreign_table, foreign_column in fk_constraints:
                print(f"\n[FK] {constraint_name}:")
                print(f"     Column: {table_name}.{column_name}")
                print(f"     References: {foreign_table}.{foreign_column}")
        else:
            print("[WARNING] No Foreign Key constraints found on Carts table!")
        
        # 2. Check data types
        print("\n" + "=" * 60)
        print("[CHECK] Column Types in Carts table:")
        print("=" * 60)
        
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='carts'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        for col_name, data_type in columns:
            print(f"  {col_name}: {data_type}")
        
        # 3. Check for orphaned records (UserID not in Users)
        print("\n" + "=" * 60)
        print("[CHECK] Orphaned Records in Carts (UserID not in Users):")
        print("=" * 60)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Carts c
            LEFT JOIN Users u ON c.UserID = u.TelegramID
            WHERE u.TelegramID IS NULL
        """)
        
        orphaned_users = cursor.fetchone()[0]
        print(f"  Orphaned UserID records: {orphaned_users}")
        
        if orphaned_users > 0:
            cursor.execute("""
                SELECT DISTINCT c.UserID 
                FROM Carts c
                LEFT JOIN Users u ON c.UserID = u.TelegramID
                WHERE u.TelegramID IS NULL
                LIMIT 10
            """)
            orphaned_user_ids = cursor.fetchall()
            print(f"  Example orphaned UserIDs:")
            for user_id in orphaned_user_ids:
                print(f"    - {user_id[0]}")
        
        # 4. Check for orphaned records (ProductID not in Products)
        print("\n" + "=" * 60)
        print("[CHECK] Orphaned Records in Carts (ProductID not in Products):")
        print("=" * 60)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Carts c
            LEFT JOIN Products p ON c.ProductID = p.ProductID
            WHERE p.ProductID IS NULL
        """)
        
        orphaned_products = cursor.fetchone()[0]
        print(f"  Orphaned ProductID records: {orphaned_products}")
        
        if orphaned_products > 0:
            cursor.execute("""
                SELECT DISTINCT c.ProductID 
                FROM Carts c
                LEFT JOIN Products p ON c.ProductID = p.ProductID
                WHERE p.ProductID IS NULL
                LIMIT 10
            """)
            orphaned_product_ids = cursor.fetchall()
            print(f"  Example orphaned ProductIDs:")
            for product_id in orphaned_product_ids:
                print(f"    - {product_id[0]}")
        
        # 5. Check recent Carts entries
        print("\n" + "=" * 60)
        print("[CHECK] Recent Carts Entries (Last 10):")
        print("=" * 60)
        
        cursor.execute("""
            SELECT CartID, UserID, ProductID, Quantity, Price, AddedAt
            FROM Carts
            ORDER BY AddedAt DESC
            LIMIT 10
        """)
        
        recent_carts = cursor.fetchall()
        for cart_id, user_id, product_id, quantity, price, added_at in recent_carts:
            # Check if user exists
            cursor.execute("SELECT TelegramID FROM Users WHERE TelegramID = %s", (user_id,))
            user_exists = cursor.fetchone() is not None
            
            # Check if product exists
            cursor.execute("SELECT ProductID FROM Products WHERE ProductID = %s", (product_id,))
            product_exists = cursor.fetchone() is not None
            
            user_status = "[OK]" if user_exists else "[MISSING]"
            product_status = "[OK]" if product_exists else "[MISSING]"
            
            print(f"  CartID: {cart_id}, UserID: {user_id} {user_status}, ProductID: {product_id} {product_status}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Check completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = check_foreign_keys()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
