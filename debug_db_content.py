import sqlite3
import os

db_path = r'C:\Users\Hp\Desktop\TelegramStoreBot\data\store_local_new.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Data Inspection ---")

# Check Messages
print("\n[Messages Table]")
try:
    cursor.execute("SELECT MessageID, OrderID, MessageType, MessageText FROM Messages ORDER BY MessageID DESC LIMIT 5")
    msgs = cursor.fetchall()
    for m in msgs:
        print(f"MsgID: {m[0]}, OrderID: {m[1]}, Type: {m[2]}, Text: {m[3]}")
        if m[1]: # If OrderID exists, check items
             order_id = m[1]
             print(f"  -> Checking Items for Order {order_id}...")
             cursor.execute("SELECT * FROM OrderItems WHERE OrderID = ?", (order_id,))
             items = cursor.fetchall()
             if not items:
                 print("     [WARNING] No OrderItems found for this OrderID!")
             else:
                 for item in items:
                     print(f"     Item: {item}")
                     
except Exception as e:
    print(f"Error querying Messages: {e}")

# Check OrderItems schema
print("\n[OrderItems Schema]")
cursor.execute("PRAGMA table_info(OrderItems)")
for col in cursor.fetchall():
    print(col)

conn.close()
