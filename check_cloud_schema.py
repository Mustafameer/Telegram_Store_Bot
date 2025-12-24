import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print("Checking OrderItems columns in Cloud DB...")
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orderitems'")
    cols = cursor.fetchall()
    
    print("Columns found:")
    for c in cols:
        print(f"- {c[0]}")
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
