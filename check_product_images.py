import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print("Checking Product Images...")
    cursor.execute("SELECT ProductID, Name, ImagePath FROM Products WHERE Name='قميص'")
    products = cursor.fetchall()
    
    for p in products:
        # Safe print
        pid = p[0]
        name = str(p[1]).encode('ascii', 'ignore').decode()
        img = str(p[2]).encode('ascii', 'ignore').decode()
        print(f"ID: {pid}, Name: {name}, Path: {img}")
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
