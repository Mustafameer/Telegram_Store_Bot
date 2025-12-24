import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

def check_all():
    try:
        print(f"Checking DB: {DB_URL.split('@')[1] if '@' in DB_URL else 'Unknown'}")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Count Orders
        cursor.execute("SELECT count(*) FROM Orders")
        orders = cursor.fetchone()[0]
        
        # Count Items
        cursor.execute("SELECT count(*) FROM OrderItems")
        items = cursor.fetchone()[0]
        
        print(f"Orders Count: {orders}")
        print(f"Items Count:  {items}")
        
        if orders > 0 and items == 0:
             print("ALERT: Orders exist but Items are missing. Sync Failure confirmed.")
             
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_all()
