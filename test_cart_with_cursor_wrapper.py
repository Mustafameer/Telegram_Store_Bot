#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت اختبار لمحاكاة سلوك البوت مع CursorWrapper
"""
import sys
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Simulate CursorWrapper behavior
class CursorWrapper:
    def __init__(self, cursor, is_postgres=False):
        self.cursor = cursor
        self.is_postgres = is_postgres
        self.lastrowid = None

    def execute(self, query, params=None):
        if self.is_postgres:
            # Replace ? with %s
            query = query.replace('?', '%s')
        try:
            if params is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, params)
        except Exception as e:
            raise e
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()
        
    def close(self):
        self.cursor.close()

# ====== معلومات الاتصال ======
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found!")
    sys.exit(1)

import urllib.parse
result = urllib.parse.urlparse(DATABASE_URL)
db_params = {
    "database": result.path[1:],
    "user": result.username,
    "password": result.password,
    "host": result.hostname,
    "port": result.port
}

def get_user(telegram_id):
    """محاكاة دالة get_user من البوت"""
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=True)
    
    try:
        cursor_wrapper.execute("SELECT * FROM Users WHERE TelegramID=?", (telegram_id,))
        user = cursor_wrapper.fetchone()
        return user
    except Exception as e:
        print(f"[ERROR] Error in get_user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def add_user(telegram_id, username, usertype, phone_number=None, full_name=None):
    """محاكاة دالة add_user من البوت"""
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=True)
    
    try:
        cursor_wrapper.execute("""
            INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (TelegramID) 
            DO UPDATE SET 
                UserName = EXCLUDED.UserName, 
                UserType = EXCLUDED.UserType, 
                PhoneNumber = COALESCE(EXCLUDED.PhoneNumber, Users.PhoneNumber), 
                FullName = COALESCE(EXCLUDED.FullName, Users.FullName)
        """, (telegram_id, username, usertype, phone_number, full_name))
        conn.commit()
        print(f"[SUCCESS] User {telegram_id} added/updated")
        return True
    except Exception as e:
        print(f"[ERROR] Error in add_user: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def add_to_cart_db(user_id, product_id, quantity=1, price=None):
    """محاكاة دالة add_to_cart_db من البوت"""
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=True)
    
    try:
        # Ensure user exists
        user = get_user(user_id)
        if not user:
            print(f"[INFO] User {user_id} not found. Creating...")
            user_created = add_user(user_id, None, 'buyer', None, None)
            if not user_created:
                print(f"[ERROR] Failed to create user {user_id}")
                conn.close()
                return False
            
            # Close and reopen connection
            cursor.close()
            conn.close()
            import time
            time.sleep(0.1)
            
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()
            cursor_wrapper = CursorWrapper(cursor, is_postgres=True)
            
            # Verify user
            user = get_user(user_id)
            if not user:
                print(f"[ERROR] User {user_id} still not found")
                conn.close()
                return False
        
        # Get product price if not provided
        if price is None:
            cursor_wrapper.execute("SELECT Price FROM Products WHERE ProductID=?", (product_id,))
            product = cursor_wrapper.fetchone()
            if not product:
                print(f"[ERROR] Product {product_id} not found")
                conn.close()
                return False
            price = product[0]
        
        # Check existing cart item
        cursor_wrapper.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
        existing = cursor_wrapper.fetchone()
        
        if existing:
            new_quantity = existing[0] + quantity
            cursor_wrapper.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", 
                          (new_quantity, price, user_id, product_id))
            print(f"[SUCCESS] Updated cart: Quantity={new_quantity}")
        else:
            cursor_wrapper.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                          (user_id, product_id, quantity, price))
            print(f"[SUCCESS] Added to cart: Quantity={quantity}")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Error in add_to_cart_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def test():
    """اختبار إضافة منتج للسلة"""
    print("=" * 60)
    print("[TEST] Testing Add to Cart with CursorWrapper")
    print("=" * 60)
    
    # Test with a new user ID (large number to test BIGINT)
    test_user_id = 9999999999  # Large Telegram ID
    test_product_id = 100008
    
    print(f"\n[TEST] UserID: {test_user_id} (BIGINT)")
    print(f"[TEST] ProductID: {test_product_id}")
    
    # First, delete user if exists
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID = %s", (test_user_id,))
        cursor.execute("DELETE FROM Users WHERE TelegramID = %s", (test_user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print("[INFO] Cleaned up test data")
    except:
        pass
    
    # Test add to cart
    success = add_to_cart_db(test_user_id, test_product_id, 1, None)
    
    if success:
        print("\n[SUCCESS] Test passed!")
        return True
    else:
        print("\n[FAIL] Test failed!")
        return False

if __name__ == "__main__":
    try:
        success = test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
