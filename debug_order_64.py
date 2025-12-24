import os
import sqlite3

# Standalone DB Connection (Copied from bot.py logic)
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
        # Local SQLite
        return sqlite3.connect('store.db')

IS_POSTGRES = os.environ.get('DATABASE_URL') is not None

def debug_order_64():
    print(f"Debug Order #64... (Mode: {'Cloud/Postgres' if IS_POSTGRES else 'Local/SQLite'})")
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB")
        return

    cursor = conn.cursor()
    
    # 1. Check Order Exist
    print("Checking Orders table...")
    sql = "SELECT * FROM Orders WHERE OrderID = 64" if IS_POSTGRES else "SELECT * FROM Orders WHERE OrderID = 64"
    cursor.execute(sql)
    
    order = cursor.fetchone()
    if not order:
        print("x Order #64 NOT FOUND in Orders table.")
    else:
        print(f"Order #64 Found: {order}")

    # 2. Check OrderItems
    print("\nChecking OrderItems for Order #64:")
    sql = "SELECT * FROM OrderItems WHERE OrderID = 64" if IS_POSTGRES else "SELECT * FROM OrderItems WHERE OrderID = 64"
    cursor.execute(sql)
        
    items = cursor.fetchall()
    if not items:
        print("x No items found in OrderItems table for Order #64.")
    else:
        for item in items:
            print(f"   - Item: {item}")
            # Try to identify ProductID
            # Usually structure: OrderItemID, OrderID, ProductID, Quantity, Price
            # Let's adjust based on typical schema (index 2 might be ProductID)
            
            if len(item) > 2:
                pid = item[2] 
                print(f"     Checking ProductID {pid}...")
                sql_prod = "SELECT * FROM Products WHERE ProductID = %s" if IS_POSTGRES else "SELECT * FROM Products WHERE ProductID = ?"
                cursor.execute(sql_prod, (pid,))
                prod = cursor.fetchone()
                if prod:
                    print(f"     Product Found: {prod}")
                else:
                     print(f"     ProductID {pid} NOT FOUND in Products table.")

    conn.close()

if __name__ == "__main__":
    debug_order_64()
