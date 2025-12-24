
import psycopg2
import os

# Set Envs from run_cloud.bat (Verification)
os.environ['DATABASE_URL'] = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def test_insert():
    db_url = os.environ.get('DATABASE_URL')
    print(f"Connecting to DB...")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # 1. Clean up test data
        print("Cleaning up test data...")
        try:
            cursor.execute("DELETE FROM OrderItems WHERE OrderItemID = 99999")
            cursor.execute("DELETE FROM Orders WHERE OrderID = 99999")
            cursor.execute("DELETE FROM Sellers WHERE SellerID = 99999")
            conn.commit()
        except:
            conn.rollback()

        # 1.5 Insert Parent Seller
        print("Inserting Parent Seller...")
        cursor.execute("""
            INSERT INTO Sellers (SellerID, TelegramID, StoreName, Status)
            VALUES (99999, 99999, 'Test Store', 'active')
            ON CONFLICT (SellerID) DO NOTHING
        """)

        # 2. Insert Parent Order
        print("Inserting Parent Order...")
        cursor.execute("""
            INSERT INTO Orders (OrderID, SellerID, Total, Status, CreatedAt)
            VALUES (99999, 99999, 100, 'Test', NOW())
            ON CONFLICT (OrderID) DO NOTHING
        """)
        conn.commit()

        # 2.5 Insert Parent Product
        print("Inserting Parent Product...")
        cursor.execute("""
            INSERT INTO Products (ProductID, SellerID, Name, Price, Quantity)
            VALUES (99999, 99999, 'Test Product', 10.0, 100)
            ON CONFLICT (ProductID) DO NOTHING
        """)
        conn.commit()

        # 3. Insert OrderItem
        print("Inserting OrderItem INVALID...")
        sql = """
            INSERT INTO OrderItems (ItemID, OrderID, ProductID, Quantity, Price) 
            VALUES (99999, 99999, 99999, 1, 10.0) 
            ON CONFLICT (ItemID) DO UPDATE SET 
            ItemID = EXCLUDED.ItemID
        """
        cursor.execute(sql)
        conn.commit()
        print("SUCCESS! Inserted OrderItem.")
        
        # 4. Clean up
        cursor.execute("DELETE FROM OrderItems WHERE OrderItemID = 99999")
        cursor.execute("DELETE FROM Products WHERE ProductID = 99999")
        cursor.execute("DELETE FROM Orders WHERE OrderID = 99999")
        cursor.execute("DELETE FROM Sellers WHERE SellerID = 99999")
        conn.commit()
        
    except Exception as e:
        print(f"Insert FAILED: {e}") # Removed emoji
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_insert()
