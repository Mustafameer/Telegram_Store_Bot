
import os
import psycopg2
import sqlite3
import urllib.parse
from datetime import datetime

# Mock environment info if needed or use existing
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES = bool(DATABASE_URL)

def get_connection():
    if IS_POSTGRES:
        result = urllib.parse.urlparse(DATABASE_URL)
        return psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
    else:
        return sqlite3.connect("data/store_local_new.db")

def test_delete_logic():
    print(f"Connecting to {'Postgres' if IS_POSTGRES else 'SQLite'}...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Skipping test: Could not connect to DB: {e}")
        return

    # 1. Create Dummy Order
    print("Creating dummy order...")
    try:
        if IS_POSTGRES:
            cursor.execute("INSERT INTO Orders (Total) VALUES (100) RETURNING OrderID")
            order_id = cursor.fetchone()[0]
        else:
            cursor.execute("INSERT INTO Orders (Total) VALUES (100)")
            order_id = cursor.lastrowid
        conn.commit()
        print(f"Created Dummy Order #{order_id}")
    except Exception as e:
        print(f"Failed to create dummy order: {e}")
        conn.close()
        return

    # 2. Simulate Delete Logic
    print("Simulating deletion...")
    try:
        # Restore logic skipped (irrelevant for deletion failure check)
        
        # Deletion Statements
        if IS_POSTGRES:
            cursor.execute("DELETE FROM Messages WHERE OrderID = %s", (order_id,))
            print(f"Messages deleted: {cursor.rowcount}")
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = %s", (order_id,))
            print(f"OrderItems deleted: {cursor.rowcount}")
            cursor.execute("DELETE FROM Returns WHERE OrderID = %s", (order_id,))
            print(f"Returns deleted: {cursor.rowcount}")
            cursor.execute("DELETE FROM Orders WHERE OrderID = %s", (order_id,))
            print(f"Orders deleted: {cursor.rowcount}")
        else:
            cursor.execute("DELETE FROM Messages WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Returns WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Orders WHERE OrderID = ?", (order_id,))
            print("Deletion executed (rowcount not reliable in sqlite3 standard cursor often)")

        conn.commit()
        print("Commit executed.")

        # 3. Verify Deletion
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM Orders WHERE OrderID = %s", (order_id,))
        else:
            cursor.execute("SELECT * FROM Orders WHERE OrderID = ?", (order_id,))
        
        res = cursor.fetchone()
        if res:
            print("❌ FAILURE: Order still exists in DB!")
        else:
            print("✅ SUCCESS: Order verified deleted.")

    except Exception as e:
        print(f"❌ Error during deletion: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_delete_logic()
