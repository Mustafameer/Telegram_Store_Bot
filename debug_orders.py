
import sqlite3
import os

def check_db():
    base_path = os.getcwd()
    potential_paths = [
        os.path.join(base_path, 'data', 'store_local_new.db'),
        os.path.join(base_path, 'flutter_store_app', 'data', 'store_local_new.db'),
        os.path.join(base_path, 'flutter_store_app', 'build', 'windows', 'x64', 'runner', 'Debug', 'data', 'store_local_new.db'),
    ]

    for db_path in potential_paths:
        if not os.path.exists(db_path):
            continue
            
        print(f"\n------------------------------------------------")
        print(f"Checking Database at: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # 1. Get Latest Order (Limit 5 to see #34)
            print("Latest 5 Orders:")
            rows = cursor.execute("SELECT OrderID, CreatedAt, Total, Status FROM Orders ORDER BY OrderID DESC LIMIT 5").fetchall()
            for row in rows:
                print(f"   [#{row['OrderID']}] {row['CreatedAt']} | Total: {row['Total']} | Status: {row['Status']}")
                
                # 2. Check Items for this Order
                items = cursor.execute("SELECT * FROM OrderItems WHERE OrderID = ?", (row['OrderID'],)).fetchall()
                if items:
                    print(f"      ITEMS ({len(items)}):")
                    for item in items:
                         print(f"         - ProductID: {item['ProductID']} | Qty: {item['Quantity']} | Price: {item['Price']}")
                else:
                     print(f"      NO ITEMS FOUND (0 rows in OrderItems)")

        except Exception as e:
            print(f"Error reading {db_path}: {e}")
        finally:
            conn.close()
            
    return

if __name__ == "__main__":
    check_db()
