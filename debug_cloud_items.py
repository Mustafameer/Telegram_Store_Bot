import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

def check_items():
    try:
        print("Connecting to Cloud DB...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 1. Check Schema
        print("\nChecking OrderItems Columns:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'orderitems'
        """)
        cols = cursor.fetchall()
        for c in cols:
            print(f" - {c[0]}: {c[1]}")
            
        # 2. Count Rows
        print("\nCounting Rows:")
        cursor.execute("SELECT count(*) FROM OrderItems")
        count = cursor.fetchone()[0]
        print(f"Total OrderItems: {count}")
        
        # 3. Test Insert (if empty)
        if count == 0:
            print("\nAttempting Dummy Insert...")
            try:
                # Assuming standard columns based on my code
                cursor.execute("""
                    INSERT INTO OrderItems (OrderItemID, OrderID, ProductID, Quantity, Price)
                    VALUES (99999, 99999, 99999, 1, 1000)
                """) # Intentionally omitting 'itemid'
                conn.commit()
                print("INSERT SUCCESS! (Table works)")
                
                # Cleanup
                cursor.execute("DELETE FROM OrderItems WHERE OrderItemID = 99999")
                conn.commit()
            except Exception as e:
                print(f"INSERT FAILED: {e}")
                conn.rollback()

        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_items()
