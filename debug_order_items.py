import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
# IDs seen in previous logs: 72, 73, 74
ORDER_IDS = [72, 73, 74]

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print(f"Checking OrderItems for Orders: {ORDER_IDS}")
    
    placeholders = ',' .join(['%s'] * len(ORDER_IDS))
    query = f"""
        SELECT oi.*, p.Name 
        FROM OrderItems oi 
        LEFT JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID IN ({placeholders})
    """
    
    cursor.execute(query, tuple(ORDER_IDS))
    items = cursor.fetchall()
    
    print(f"Found {len(items)} items:")
    for i in items:
        # Safe print (ascii)
        print(str(i).encode('ascii', 'ignore').decode())
        
    if not items:
        print("!! NO ITEMS FOUND !!")
        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM OrderItems")
        count = cursor.fetchone()[0]
        print(f"Total rows in OrderItems table: {count}")

    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
