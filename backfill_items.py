import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
# Orders from the screenshot
TARGET_ORDERS = [72, 73] 

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Get the dummy product we created/found earlier
    cursor.execute("SELECT ProductID FROM Products WHERE Name='قميص' LIMIT 1")
    prod = cursor.fetchone()
    
    if not prod:
        # Should exist from previous step, but just in case
        cursor.execute("SELECT ProductID FROM Products LIMIT 1")
        prod = cursor.fetchone()
        
    if prod:
        prod_id = prod[0]
        print(f"Using ProductID: {prod_id}")
        
        for oid in TARGET_ORDERS:
            # Check if item already exists to avoid duplicates
            cursor.execute("SELECT COUNT(*) FROM OrderItems WHERE OrderID = %s", (oid,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"Inserting item for Order {oid}...")
                cursor.execute("""
                    INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price)
                    VALUES (%s, %s, %s, %s)
                """, (oid, prod_id, 1, 17500))
            else:
                print(f"Order {oid} already has items.")
                
        conn.commit()
        print("✅ Backfill complete!")
    else:
        print("❌ No products found to map!")
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
