import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print("Checking Triggers on OrderItems...")
    cursor.execute("""
        SELECT trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'orderitems'
    """)
    triggers = cursor.fetchall()
    
    if not triggers:
        print("No triggers found.")
    else:
        for t in triggers:
            print(f"Trigger: {t[0]}")
            print(f"Event: {t[1]}")
            print(f"Action: {t[2]}")
            print("-" * 20)

    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
