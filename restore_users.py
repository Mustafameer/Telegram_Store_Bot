
import sys
import os
import sqlite3

# Set Token to avoid exit
os.environ['TELEGRAM_BOT_TOKEN'] = "8562406465:AAEudEf_n6ZDnMlVy_UTwJ7eG1hBdDb1Tgw"

# DB Path
DB_FILE = r"c:\Users\Hp\Desktop\TelegramStoreBot\data\store_local_new.db"
BOT_ADMIN_ID = 1041977029

def restore_users():
    if not os.path.exists(DB_FILE):
        print(f"DB not found: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Get Sellers
        cursor.execute("SELECT TelegramID, UserName, StoreName FROM Sellers")
        sellers = cursor.fetchall()
        print(f"Found {len(sellers)} sellers to restore.")

        count = 0
        for telegram_id, username, store_name in sellers:
            user_type = 'seller'
            if telegram_id == BOT_ADMIN_ID:
                user_type = 'bot_admin'
            
            # Check if user exists
            cursor.execute("SELECT UserID FROM Users WHERE TelegramID = ?", (telegram_id,))
            exists = cursor.fetchone()
            
            if not exists:
                print(f"Restoring User: {username} ({telegram_id}) as {user_type}")
                full_name = username or "Restored User"
                cursor.execute("""
                    INSERT INTO Users (TelegramID, UserName, UserType, FullName)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, username, user_type, full_name))
                count += 1
            else:
                # Update type if needed
                cursor.execute("UPDATE Users SET UserType = ? WHERE TelegramID = ?", (user_type, telegram_id))
                print(f"Updated User: {username} ({telegram_id}) to {user_type}")

        conn.commit()
        print(f"[OK] Restored {count} users.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    restore_users()
