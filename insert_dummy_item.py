import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
ORDER_ID = 74 # Targeting the order from the screenshot

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Check if products exist first
    cursor.execute("SELECT ProductID FROM Products LIMIT 1")
    prod = cursor.fetchone()
    
    prod_id = prod[0] if prod else None
    
    if not prod_id:
        print("Creating dummy product...")
        cursor.execute("INSERT INTO Products (SellerID, Name, Price, CategoryID) VALUES (10, 'قميص', 17500, 1) RETURNING ProductID")
        prod_id = cursor.fetchone()[0]
        conn.commit()
        
    print(f"Using ProductID: {prod_id} for Order {ORDER_ID}")
    
    # Insert Item
    cursor.execute("""
        INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price)
        VALUES (%s, %s, %s, %s)
    """, (ORDER_ID, prod_id, 1, 17500))
    
    conn.commit()
    print("✅ Dummy item inserted successfully!")
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
