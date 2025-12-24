import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
# This file exists locally as per find_by_name result
LOCAL_IMAGE_PATH = r"c:\Users\Hp\Desktop\TelegramStoreBot\data\Images\1766153746_cc861a5bdeff48049169565c730582d0.jpg"

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print(f"Updating Product Image to: {LOCAL_IMAGE_PATH}")
    
    # Update the dummy product 'قميص' (which we know is ProductID 25 from previous logs)
    # We can update all products with this name or just the specific ID.
    cursor.execute("UPDATE Products SET ImagePath = %s WHERE Name = 'قميص'", (LOCAL_IMAGE_PATH,))
    
    conn.commit()
    print(f"✅ Updated {cursor.rowcount} products.")
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
