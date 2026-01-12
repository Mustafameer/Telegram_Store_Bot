#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت اختبار لإضافة منتج للسلة وتحديد المشكلة
"""
import sys
import psycopg2

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ====== معلومات الاتصال ======
HOST = "switchback.proxy.rlwy.net"
PORT = 20266
DATABASE = "railway"
USERNAME = "postgres"
PASSWORD = "bqcTJxNXLgwOftDoarrtmjmjYWurEIEh"

def test_add_to_cart():
    """اختبار إضافة منتج للسلة"""
    
    try:
        print("=" * 60)
        print("[TEST] Testing Add to Cart Functionality")
        print("=" * 60)
        
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD
        )
        
        cursor = conn.cursor()
        
        # 1. Get a test user (or create one)
        test_user_id = 1041977029  # BOT_ADMIN_ID
        print(f"\n[STEP 1] Checking if user {test_user_id} exists...")
        
        cursor.execute("SELECT TelegramID FROM Users WHERE TelegramID = %s", (test_user_id,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            print(f"[INFO] User {test_user_id} not found. Creating user...")
            cursor.execute("""
                INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (TelegramID) DO NOTHING
            """, (test_user_id, 'test_user', 'buyer', None, None))
            conn.commit()
            print(f"[SUCCESS] User {test_user_id} created")
        else:
            print(f"[OK] User {test_user_id} exists")
        
        # 2. Get a test product
        print(f"\n[STEP 2] Getting a test product...")
        cursor.execute("SELECT ProductID FROM Products LIMIT 1")
        product_result = cursor.fetchone()
        
        if not product_result:
            print("[ERROR] No products found in database!")
            cursor.close()
            conn.close()
            return False
        
        test_product_id = product_result[0]
        print(f"[OK] Found product {test_product_id}")
        
        # 3. Get product price
        cursor.execute("SELECT Price FROM Products WHERE ProductID = %s", (test_product_id,))
        price_result = cursor.fetchone()
        test_price = price_result[0] if price_result else 1000
        
        # 4. Try to add to cart
        print(f"\n[STEP 3] Attempting to add product {test_product_id} to cart for user {test_user_id}...")
        
        try:
            # Check if item already exists in cart
            cursor.execute("SELECT Quantity FROM Carts WHERE UserID = %s AND ProductID = %s", 
                          (test_user_id, test_product_id))
            existing = cursor.fetchone()
            
            if existing:
                new_quantity = existing[0] + 1
                cursor.execute("""
                    UPDATE Carts 
                    SET Quantity = %s, Price = %s 
                    WHERE UserID = %s AND ProductID = %s
                """, (new_quantity, test_price, test_user_id, test_product_id))
                print(f"[SUCCESS] Updated cart: Quantity = {new_quantity}")
            else:
                cursor.execute("""
                    INSERT INTO Carts (UserID, ProductID, Quantity, Price) 
                    VALUES (%s, %s, %s, %s)
                """, (test_user_id, test_product_id, 1, test_price))
                print(f"[SUCCESS] Added to cart: Quantity = 1")
            
            conn.commit()
            print("[SUCCESS] Cart operation completed successfully!")
            
        except psycopg2.IntegrityError as e:
            print(f"[ERROR] Foreign Key Constraint Violation: {e}")
            print("\n[DEBUG] Checking Foreign Key constraints...")
            
            # Check if user exists
            cursor.execute("SELECT TelegramID FROM Users WHERE TelegramID = %s", (test_user_id,))
            user_check = cursor.fetchone()
            print(f"  User {test_user_id} exists: {user_check is not None}")
            
            # Check if product exists
            cursor.execute("SELECT ProductID FROM Products WHERE ProductID = %s", (test_product_id,))
            product_check = cursor.fetchone()
            print(f"  Product {test_product_id} exists: {product_check is not None}")
            
            # Check data types
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='carts' AND column_name IN ('userid', 'productid')
            """)
            types = cursor.fetchall()
            for col_name, data_type in types:
                print(f"  Carts.{col_name}: {data_type}")
            
            conn.rollback()
            return False
        
        # 5. Verify the cart entry
        print(f"\n[STEP 4] Verifying cart entry...")
        cursor.execute("""
            SELECT CartID, UserID, ProductID, Quantity, Price 
            FROM Carts 
            WHERE UserID = %s AND ProductID = %s
        """, (test_user_id, test_product_id))
        
        cart_entry = cursor.fetchone()
        if cart_entry:
            print(f"[SUCCESS] Cart entry verified:")
            print(f"  CartID: {cart_entry[0]}")
            print(f"  UserID: {cart_entry[1]}")
            print(f"  ProductID: {cart_entry[2]}")
            print(f"  Quantity: {cart_entry[3]}")
            print(f"  Price: {cart_entry[4]}")
        else:
            print("[ERROR] Cart entry not found after insert!")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Test completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_add_to_cart()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
