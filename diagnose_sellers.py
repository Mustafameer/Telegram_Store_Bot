import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "store.db")

def check_sellers():
    if not os.path.exists(DB_FILE):
        print(f"Database file not found at {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("--- Sellers ---")
    try:
        cursor.execute("SELECT SellerID, TelegramID, StoreName, Status FROM Sellers")
        sellers = cursor.fetchall()
        for seller in sellers:
            print(f"ID: {seller[0]}, TG: {seller[1]}, Name: {seller[2]}, Status: {seller[3]}")
    except Exception as e:
        print(f"Error reading Sellers: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_sellers()
