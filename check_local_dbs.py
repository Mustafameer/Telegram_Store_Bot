import sqlite3
import os

paths = [
    r"C:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app\data\store_local_new.db",
    r"C:\Users\Hp\Desktop\TelegramStoreBot\data\store_local_new.db"
]

for p in paths:
    print(f"Checking: {p}")
    if os.path.exists(p):
        try:
            conn = sqlite3.connect(p)
            cursor = conn.cursor()
            cursor.execute("SELECT Count(*) FROM Sellers")
            count = cursor.fetchone()[0]
            print(f"  -> Found {count} Sellers")
            
            cursor.execute("SELECT StoreName FROM Sellers")
            names = cursor.fetchall()
            print(f"  -> Names: {names}")
            conn.close()
        except Exception as e:
            print(f"  -> Error: {e}")
    else:
        print("  -> File NOT FOUND")
