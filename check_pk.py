import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')

def check_pk():
    try:
        print("Connecting...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        print("\nChecking Constraints for 'orderitems':")
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'orderitems'
        """)
        
        constraints = cursor.fetchall()
        for c in constraints:
            print(f" - {c[0]} ({c[1]})")
            
        if not any(c[1] == 'PRIMARY KEY' for c in constraints):
            print("\n⚠️ WARNING: NO PRIMARY KEY FOUND!")
        else:
            print("\n✅ Primary Key Exists.")

        # Check orderitemid specific usage
        print("\nChecking Usage of 'orderitemid':")
        cursor.execute("""
            SELECT kcu.column_name, tc.constraint_type
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc 
              ON kcu.constraint_name = tc.constraint_name
            WHERE kcu.table_name = 'orderitems' 
              AND kcu.column_name = 'orderitemid'
        """)
        usage = cursor.fetchall()
        for u in usage:
             print(f" - Used in {u[1]}")

        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_pk()
