
import psycopg2
import urllib.parse
DATABASE_URL = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def check_db():
    print(f"Connecting to: {DATABASE_URL}")
    result = urllib.parse.urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    
    try:
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        print("Connected successfully!")
        cursor = conn.cursor()

        print("\n--- SELLERS ---")
        cursor.execute("SELECT SellerID, TelegramID, UserName, StoreName, Status FROM Sellers")
        sellers = cursor.fetchall()
        for s in sellers:
            print(f"ID: {s[0]}, TG_ID: {s[1]}, User: {s[2]}, Store: {s[3]}, Status: {s[4]}")

        print("\n--- ORDERS COLUMNS ---")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
        columns = cursor.fetchall()
        print([c[0] for c in columns])

        print("\n--- ORDERS DATA ---")
        # Use * to see what we get if we can't guess columns
        cursor.execute("SELECT * FROM Orders LIMIT 1")
        print(cursor.fetchone())
            
        print("\n--- USERS ---")
        cursor.execute("SELECT TelegramID, FullName, UserType FROM Users")
        users = cursor.fetchall()
        for u in users:
            print(f"TG_ID: {u[0]} | Name: {u[1]} | Type: {u[2]}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

import sys
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

if __name__ == "__main__":
    check_db()
