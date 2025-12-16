import os
import sqlite3
import unicodedata

# Force local DB path as per bot.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "store.db")

print(f"Checking DB at: {DB_FILE}")

def check_stores():
    if not os.path.exists(DB_FILE):
        print("DB file not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("\n--- Running Query from browse_stores ---")
    try:
        cursor.execute("SELECT TelegramID, UserName, StoreName FROM Sellers WHERE Status = 'active' ORDER BY StoreName")
        sellers = cursor.fetchall()
        
        if not sellers:
            print("No active sellers found.")
        else:
            print(f"Found {len(sellers)} sellers:")
            for s in sellers:
                tid, uname, sname = s
                print(f"RAW: ID={tid}, User={uname}, Store='{sname}'")
                
                # Check for hidden characters
                if sname:
                    print(f"Hex: {sname.encode('utf-8').hex()}")
                
                # Check label generation
                try:
                    display_name = f"@{uname}" if uname else ""
                    label = f"Store: {sname} - {display_name}"
                    print(f"Label would be: {label}")
                except Exception as e:
                    print(f"Error creating label: {e}")
                    
    except Exception as e:
        print(f"Query Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_stores()
