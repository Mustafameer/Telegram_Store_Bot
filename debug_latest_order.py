import os
import sys
import psycopg2

# Adjust path to import bot modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def debug_latest_order():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"🔌 Database: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    
    # 1. Get Latest Order
    cursor.execute("SELECT * FROM Orders ORDER BY OrderID DESC LIMIT 1")
    order = cursor.fetchone()
    
    if not order:
        print("❌ No orders found in DB.")
        return

    order_id = order[0]
    buyer_id = order[1]
    total = order[3]
    print(f"📦 Latest Order ID: {order_id}")
    print(f"👤 BuyerID: {buyer_id} (Type: {type(buyer_id)})")
    print(f"💰 Total: {total}")
    
    # 2. Check OrderItems (Raw)
    print(f"\n🔍 Checking OrderItems for OrderID {order_id}...")
    cursor.execute("SELECT * FROM OrderItems WHERE OrderID = %s" if IS_POSTGRES else "SELECT * FROM OrderItems WHERE OrderID = ?", (order_id,))
    items = cursor.fetchall()
    
    if not items:
        print(f"❌ No items found in OrderItems table for Order #{order_id}.")
        
        # DEBUG: Check if maybe OrderID was mismatched?
        # Show last 5 items added globally
        print("\nLast 5 items added to ANY order:")
        cursor.execute("SELECT * FROM OrderItems ORDER BY OrderItemID DESC LIMIT 5")
        last_items = cursor.fetchall()
        for li in last_items:
            print(li)
            
    else:
        print(f"✅ Found {len(items)} items in OrderItems:")
        for item in items:
            print(item)
            
    # 3. Check Join with Products
    print(f"\n🔗 Checking Join with Products...")
    cursor.execute("""
        SELECT oi.*, p.Name 
        FROM OrderItems oi
        JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = %s
    """ if IS_POSTGRES else """
        SELECT oi.*, p.Name 
        FROM OrderItems oi
        JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = ?
    """, (order_id,))
    
    joined_items = cursor.fetchall()
    if not joined_items:
        print("⚠️ Join failed (Items exist but Products might be missing/deleted?)")
    else:
        print(f"✅ Join Successful. Retrieved {len(joined_items)} items with details.")

    # 4. Check Orders Table Schema for BuyerID
    if IS_POSTGRES:
        print("\n📊 Checking Orders Table Schema (BuyerID):")
        try:
             cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'buyerid'")
             res = cursor.fetchone()
             print(f"   BuyerID DataType: {res}")
             
             print("\n📊 Checking OrderItems Table Schema:")
             cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orderitems'")
             cols = cursor.fetchall()
             for c in cols:
                 print(f"   {c[0]}: {c[1]}")
        except Exception as e:
            print(f"   Error checking schema: {e}")

    conn.close()

if __name__ == "__main__":
    try:
        debug_latest_order()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
