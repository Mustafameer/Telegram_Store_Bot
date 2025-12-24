import os
import sqlite3

# Standalone DB Connection
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if db_url and 'postgresql' in db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except ImportError:
            print("psycopg2 not installed!")
            return None
    else:
        return sqlite3.connect('store.db')

IS_POSTGRES = os.environ.get('DATABASE_URL') is not None

def debug_order_65():
    print(f"Debug Order #65... (Mode: {'Cloud/Postgres' if IS_POSTGRES else 'Local/SQLite'})")
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB")
        return

    cursor = conn.cursor()
    
    # 1. Check Order Exist
    print("Checking Orders table...")
    sql = "SELECT * FROM Orders WHERE OrderID = 65" if IS_POSTGRES else "SELECT * FROM Orders WHERE OrderID = 65"
    cursor.execute(sql)
    
    order = cursor.fetchone()
    if not order:
        print("x Order #65 NOT FOUND in Orders table.")
    else:
        print(f"Order #65 Found: {order}")

    # 2. Check OrderItems
    print("\nChecking OrderItems for Order #65:")
    sql = "SELECT * FROM OrderItems WHERE OrderID = 65" if IS_POSTGRES else "SELECT * FROM OrderItems WHERE OrderID = 65"
    cursor.execute(sql)
        
    items = cursor.fetchall()
    if not items:
        print("x No items found in OrderItems table for Order #65.")
    else:
        for item in items:
            print(f"   - Item: {item}")

    conn.close()

if __name__ == "__main__":
    debug_order_65()
