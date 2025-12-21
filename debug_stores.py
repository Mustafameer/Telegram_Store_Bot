import os
import sqlite3
import unicodedata

# Force local DB path as per bot.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")

print(f"Checking DB at: {DB_FILE}")

def check_stores():
    if not os.path.exists(DB_FILE):
        print("DB file not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("\n--- Running Query from browse_stores ---")
    try:
        cursor.execute("SELECT SellerID, TelegramID, UserName, StoreName, CreatedAt, Status FROM Sellers ORDER BY CreatedAt DESC")
        sellers = cursor.fetchall()
        
        if not sellers:
            print("No active sellers found.")
        else:
            print(f"Found {len(sellers)} sellers:")
            for s in sellers:
                sid, tid, uname, sname, created, status = s
                status_icon = "✅" if status == 'active' else "⏸️"
                print(f"{status_icon} Store: {sname}, Owner: {uname} ({tid}), Status: {status}")

    except Exception as e:
        print(f"Query Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_stores()
