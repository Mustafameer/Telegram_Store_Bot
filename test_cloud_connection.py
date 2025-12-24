import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
print(f"Checking URL: {DB_URL}")

try:
    conn = psycopg2.connect(DB_URL)
    print("Connection Successful!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"Version: {cursor.fetchone()[0]}")
    
    # Check Tables
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cursor.fetchall()
    print(f"Tables found: {[t[0] for t in tables]}")
    
    conn.close()
    
except Exception as e:
    print(f"Connection Failed: {e}")
