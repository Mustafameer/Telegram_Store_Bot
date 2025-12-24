import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bot import get_db_connection, IS_POSTGRES

def debug_products():
    print(f"🔌 Database: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Count Products
    cursor.execute("SELECT COUNT(*) FROM Products")
    count = cursor.fetchone()[0]
    print(f"📦 Total Products in DB: {count}")
    
    # 2. List First 10 Products
    print("\n📋 First 10 Products:")
    cursor.execute("SELECT ProductID, Name, Price, Quantity FROM Products LIMIT 10")
    products = cursor.fetchall()
    for p in products:
        print(f"   ID: {p[0]} | Name: {p[1]} | Price: {p[2]} | Qty: {p[3]}")
        
    conn.close()

if __name__ == "__main__":
    debug_products()
