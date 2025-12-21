import os
import psycopg2
import sys

# Hardcoded from run_cloud.bat for convenience
DATABASE_URL = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def clear_orders():
    print("🚀 Connecting to Cloud Database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Count current orders
        cursor.execute("SELECT COUNT(*) FROM Orders")
        order_count = cursor.fetchone()[0]
        
        print(f"\n⚠️ WARNING: You are about to DELETE ALL {order_count} ORDERS from the CLOUD database.")
        print("This action cannot be undone.")
        
        confirm = input("Type 'DELETE' to confirm: ")
        
        if confirm == 'DELETE':
            print("\n🗑️ Clearing OrderItems...")
            cursor.execute("TRUNCATE TABLE OrderItems CASCADE")
            
            print("🗑️ Clearing Orders...")
            cursor.execute("TRUNCATE TABLE Orders RESTART IDENTITY CASCADE")
            
            # Optional: Clear Sync Queue logic to prevent re-upload? 
            # Actually, if we clear cloud, local DeletedSync is irrelevant for these IDs since they are gone.
            
            conn.commit()
            print("✅ All Cloud Orders have been cleared.")
        else:
            print("❌ Operation Cancelled.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Ensure you have internet connection and psycopg2 installed.")

if __name__ == "__main__":
    clear_orders()
