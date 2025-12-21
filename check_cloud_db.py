
import os
import psycopg2
import sys

# Set Envs from run_cloud.bat
os.environ['DATABASE_URL'] = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def check_postgres():
    db_url = os.environ.get('DATABASE_URL')
    print(f"Connecting to: {db_url.split('@')[1]}")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("\n--- Sellers Data ---")
        try:
            cursor.execute("SELECT SellerID, TelegramID, UserName, StoreName, Status FROM Sellers")
            sellers = cursor.fetchall()
            if not sellers:
                print("No sellers found.")
            else:
                for s in sellers:
                    print(s)
        except Exception as e:
            print(f"Error fetching sellers: {e}")

        print("\n--- Users (Admins) ---")
        try:
            cursor.execute("SELECT * FROM Users WHERE UserType = 'bot_admin'")
            admins = cursor.fetchall()
            print(f"Found {len(admins)} admins.")
            for admin in admins:
                print(admin)
        except Exception as e:
            print(f"Error checking users: {e}")

        conn.close()
        
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    check_postgres()
