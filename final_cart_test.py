#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت اختبار نهائي لجميع السيناريوهات المحتملة
"""
import sys
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

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

def test_all_scenarios():
    """اختبار جميع السيناريوهات المحتملة"""
    print("=" * 60)
    print("[TEST] Testing All Possible Scenarios")
    print("=" * 60)
    
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Scenario 1: User doesn't exist, Product exists
    print("\n[SCENARIO 1] User doesn't exist, Product exists")
    test_user_1 = 1111111111
    test_product_1 = 100008
    
    # Clean up
    cursor.execute("DELETE FROM Carts WHERE UserID = %s", (test_user_1,))
    cursor.execute("DELETE FROM Users WHERE TelegramID = %s", (test_user_1,))
    conn.commit()
    
    # Create user first
    try:
        cursor.execute("""
            INSERT INTO Users (TelegramID, UserName, UserType) 
            VALUES (%s, %s, %s)
        """, (test_user_1, 'test_user_1', 'buyer'))
        conn.commit()
        print(f"  [OK] User {test_user_1} created")
    except Exception as e:
        print(f"  [ERROR] Failed to create user: {e}")
        conn.rollback()
    
    # Try to add to cart
    try:
        cursor.execute("SELECT Price FROM Products WHERE ProductID = %s", (test_product_1,))
        price_result = cursor.fetchone()
        if price_result:
            price = price_result[0]
            cursor.execute("""
                INSERT INTO Carts (UserID, ProductID, Quantity, Price) 
                VALUES (%s, %s, %s, %s)
            """, (test_user_1, test_product_1, 1, price))
            conn.commit()
            print(f"  [SUCCESS] Added to cart successfully")
        else:
            print(f"  [ERROR] Product {test_product_1} not found")
    except psycopg2.IntegrityError as e:
        print(f"  [FAIL] Foreign Key Error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"  [ERROR] Other error: {e}")
        conn.rollback()
    
    # Scenario 2: User exists, Product doesn't exist
    print("\n[SCENARIO 2] User exists, Product doesn't exist")
    test_user_2 = 2222222222
    test_product_2 = 999999999  # Non-existent product
    
    # Create user
    try:
        cursor.execute("""
            INSERT INTO Users (TelegramID, UserName, UserType) 
            VALUES (%s, %s, %s)
            ON CONFLICT (TelegramID) DO NOTHING
        """, (test_user_2, 'test_user_2', 'buyer'))
        conn.commit()
        print(f"  [OK] User {test_user_2} exists")
    except Exception as e:
        print(f"  [ERROR] Failed to create user: {e}")
        conn.rollback()
    
    # Try to add non-existent product to cart
    try:
        cursor.execute("""
            INSERT INTO Carts (UserID, ProductID, Quantity, Price) 
            VALUES (%s, %s, %s, %s)
        """, (test_user_2, test_product_2, 1, 1000))
        conn.commit()
        print(f"  [FAIL] Should have failed but didn't!")
    except psycopg2.IntegrityError as e:
        print(f"  [SUCCESS] Correctly caught Foreign Key Error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"  [ERROR] Other error: {e}")
        conn.rollback()
    
    # Scenario 3: Large Telegram ID (BIGINT test)
    print("\n[SCENARIO 3] Large Telegram ID (BIGINT test)")
    test_user_3 = 9999999999  # Large number
    test_product_3 = 100008
    
    # Clean up
    cursor.execute("DELETE FROM Carts WHERE UserID = %s", (test_user_3,))
    cursor.execute("DELETE FROM Users WHERE TelegramID = %s", (test_user_3,))
    conn.commit()
    
    # Create user with large ID
    try:
        cursor.execute("""
            INSERT INTO Users (TelegramID, UserName, UserType) 
            VALUES (%s, %s, %s)
        """, (test_user_3, 'test_user_3', 'buyer'))
        conn.commit()
        print(f"  [OK] User {test_user_3} created")
    except Exception as e:
        print(f"  [ERROR] Failed to create user: {e}")
        conn.rollback()
        return False
    
    # Try to add to cart
    try:
        cursor.execute("SELECT Price FROM Products WHERE ProductID = %s", (test_product_3,))
        price_result = cursor.fetchone()
        if price_result:
            price = price_result[0]
            cursor.execute("""
                INSERT INTO Carts (UserID, ProductID, Quantity, Price) 
                VALUES (%s, %s, %s, %s)
            """, (test_user_3, test_product_3, 1, price))
            conn.commit()
            print(f"  [SUCCESS] Added to cart successfully with BIGINT UserID")
        else:
            print(f"  [ERROR] Product {test_product_3} not found")
    except psycopg2.IntegrityError as e:
        print(f"  [FAIL] Foreign Key Error: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"  [ERROR] Other error: {e}")
        conn.rollback()
        return False
    
    # Scenario 4: Check data types
    print("\n[SCENARIO 4] Checking data types")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='carts' AND column_name IN ('userid', 'productid')
    """)
    types = cursor.fetchall()
    for col_name, data_type in types:
        print(f"  {col_name}: {data_type}")
        if col_name == 'userid' and data_type not in ('bigint', 'int8'):
            print(f"    [WARNING] UserID should be BIGINT but is {data_type}")
        if col_name == 'productid' and data_type not in ('integer', 'int4'):
            print(f"    [WARNING] ProductID should be INTEGER but is {data_type}")
    
    # Scenario 5: Check Foreign Key constraints
    print("\n[SCENARIO 5] Checking Foreign Key constraints")
    cursor.execute("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'carts'
    """)
    fks = cursor.fetchall()
    for constraint_name, column_name, foreign_table, foreign_column in fks:
        print(f"  {constraint_name}: {column_name} -> {foreign_table}.{foreign_column}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All tests completed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_all_scenarios()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
