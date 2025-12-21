
import sqlite3
import os

DB_FILE = r"c:\Users\Hp\Desktop\TelegramStoreBot\data\store_local_new.db"

def inspect_db():
    if not os.path.exists(DB_FILE):
        print(f"DB File not found at {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("--- Sellers Table Schema ---")
    try:
        cursor.execute("PRAGMA table_info(Sellers)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(f"Error reading schema: {e}")

    print("\n--- Users (Admins) ---")
    try:
        cursor.execute("SELECT * FROM Users WHERE UserType = 'bot_admin'")
        admins = cursor.fetchall()
        print(f"Found {len(admins)} admins.")
        for admin in admins:
            print(admin)
    except Exception as e:
        print(f"Error reading users: {e}")

    print("\n--- Sellers ---")
    try:
        cursor.execute("SELECT * FROM Sellers LIMIT 5")
        sellers = cursor.fetchall()
        print(f"Found {len(sellers)} sellers.")
        for seller in sellers:
            print(seller)
    except Exception as e:
        print(f"Error reading sellers: {e}")

    conn.close()

if __name__ == "__main__":
    inspect_db()
