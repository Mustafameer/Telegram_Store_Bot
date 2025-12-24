import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

# Try loading .env and print result
loaded = load_dotenv()
print(f"DEBUG: .env loaded? {loaded}")

DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DEBUG: DATABASE_URL present? {DATABASE_URL is not None}")
if DATABASE_URL:
    print(f"DEBUG: DATABASE_URL length: {len(DATABASE_URL)}")

IS_POSTGRES = DATABASE_URL is not None

def get_db_connection():
    if IS_POSTGRES:
        print("Connecting to PostgreSQL...")
        try:
            return psycopg2.connect(DATABASE_URL)
        except Exception as e:
            print(f"Postgres Connection Failed: {e}")
            return None
    else:
        db_file = 'data/store_local_new.db'
        # if not os.path.exists(db_file):
        #      if os.path.exists('store_local_new.db'):
        #          db_file = 'store_local_new.db'
        #      else:
        #          print(f"WARNING: {db_file} not found and no alternative.")
        
        print(f"Connecting to SQLite ({db_file})...")
        return sqlite3.connect(db_file)

def debug_orders():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return

    cursor = conn.cursor()

    try:
        # A. Check Tables
        print("\n--- Checking Tables ---")
        if IS_POSTGRES:
             cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
             # List columns for Orders
             print("\n--- Columns in Orders (Postgres) ---")
             cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
             print([c[0] for c in cursor.fetchall()])
        else:
             cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
             tables = cursor.fetchall()
             print([t[0] for t in tables])
             
             print("\n--- Columns in Orders (SQLite) ---")
             cursor.execute("PRAGMA table_info(Orders)")
             columns = cursor.fetchall()
             print([c[1] for c in columns])

        # B. Check Sellers
        print("\n--- Sellers ---")
        try:
            cursor.execute("SELECT SellerID, TelegramID, UserName, StoreName FROM Sellers")
            sellers = cursor.fetchall()
            for s in sellers:
                print(s)
        except Exception as e:
            print(f"Error fetching sellers: {e}")
            sellers = []

        # C. Check specific Seller Orders
        if sellers:
            seller_id = sellers[0][0]
            print(f"\n--- Orders for SellerID: {seller_id} ---")
            
            # Simple Count
            cursor.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ?", (seller_id,)) # Wrapper usually handles ?, here we need explicit
            # Wait, sqlite uses ?, Postgres uses %s.
            # Local debug script doesn't have the wrapper.
            placeholder = "%s" if IS_POSTGRES else "?"
            
            query_count = f"SELECT COUNT(*) FROM Orders WHERE SellerID = {placeholder}"
            cursor.execute(query_count, (seller_id,))
            print(f"Total Orders: {cursor.fetchone()[0]}")

            # The Actual Query
            print("\n--- Testing Bot Query Logic ---")
            query = f"""
                SELECT o.OrderID, o.Total, o.Status, o.OrderDate, 
                       COALESCE(u.FullName, 'زائر') as BuyerName
                FROM Orders o
                LEFT JOIN Users u ON o.BuyerID = u.TelegramID
                WHERE o.SellerID = {placeholder}
                ORDER BY 
                    CASE WHEN o.Status = 'Pending' THEN 0 ELSE 1 END,
                    o.OrderDate DESC
                LIMIT 10
            """
            cursor.execute(query, (seller_id,))
            results = cursor.fetchall()
            if not results:
                print("No orders returned by Bot Query.")
                
                # Debug: Why? Show ALL orders for this seller without Sort/Limit
                print("DEBUG: Fetching ALL orders for this seller (Raw):")
                cursor.execute(f"SELECT OrderID, Status, OrderDate FROM Orders WHERE SellerID = {placeholder}", (seller_id,))
                raw_orders = cursor.fetchall()
                for ro in raw_orders:
                    print(ro)
            else:
                for r in results:
                    print(r)

    except Exception as e:
        print(f"General Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    debug_orders()
