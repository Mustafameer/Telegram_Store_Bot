import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
PRODUCT_NAME = 'بدلة كلاسيكية رجالية'

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print(f"Checking Product: {PRODUCT_NAME}")
    cursor.execute("SELECT ProductID, Name, ImagePath FROM Products WHERE Name = %s", (PRODUCT_NAME,))
    products = cursor.fetchall()
    
    if not products:
        print("❌ Product not found!")
        # List all products to see if there's a typo or encoding issue
        cursor.execute("SELECT Name FROM Products LIMIT 5")
        print("First 5 products in DB:")
        for p in cursor.fetchall():
            print(str(p).encode('utf-8', 'replace').decode())
    
    for p in products:
        pid = p[0]
        name = p[1]
        img = p[2]
        print(f"ID: {pid}")
        print(f"Name: {name}")
        print(f"ImagePath: {img}")
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
