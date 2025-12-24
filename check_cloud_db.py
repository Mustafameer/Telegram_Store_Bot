
import os
import psycopg2
import sys

# Set Envs from run_cloud.bat
os.environ['DATABASE_URL'] = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

# Fix Encoding
sys.stdout.reconfigure(encoding='utf-8')

def check_postgres():
    db_url = os.environ.get('DATABASE_URL')
    print(f"Connecting to: {db_url.split('@')[1]}")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("\n--- OrderItems Data ---")
        try:
             cursor.execute("SELECT * FROM OrderItems")
             items = cursor.fetchall()
             if not items:
                 print("⚠️ OrderItems Table is EMPTY!")
             else:
                 for i in items:
                     print(f"✅ Item: {i}")
        except Exception as e:
            print(f"Error fetching items: {e}")

        print("\n--- ALL User Functions ---")
        try:
             cursor.execute("""
                SELECT routine_name, routine_definition 
                FROM information_schema.routines 
                WHERE routine_schema = 'public'
             """)
             routines = cursor.fetchall()
             for r in routines:
                 print(f"📜 Function {r[0]}:\n{r[1]}\n----------------")
        except Exception as e:
             print(f"Error fetching functions: {e}")

        conn.close()
        
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    check_postgres()
