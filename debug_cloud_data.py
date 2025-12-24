import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
print(f"Connecting to: {DB_URL}")

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print("\n--- Sellers Columns ---")
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sellers' ORDER BY ordinal_position")
    columns = cursor.fetchall()
    print([c[0] for c in columns])
    
    print("\n--- Orders Columns ---")
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders' ORDER BY ordinal_position")
    columns = cursor.fetchall()
    print([c[0] for c in columns])

    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
