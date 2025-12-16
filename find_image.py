import os
import sqlite3

# Force Local SQLite for Diagnostics
DATABASE_URL = None 

def get_db_connection():
    return sqlite3.connect('store_local_new.db')

def find_image_reference(filename_part):
    print(f"[*] Searching for image containing: '{filename_part}'...")
    
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    cursor = conn.cursor()
    
    found = False
    
    queries = [
        ("Products", "ProductID", "Name"),
        ("Categories", "CategoryID", "Name"),
        ("Sellers", "SellerID", "StoreName")
    ]

    for table, id_col, name_col in queries:
        try:
            sql = f"SELECT {id_col}, {name_col}, ImagePath FROM {table} WHERE ImagePath LIKE ?"
            param = (f"%{filename_part}%",)
                
            cursor.execute(sql, param)
            for row in cursor.fetchall():
                print(f"[+] Found in {table.upper()}: ID={row[0]}, Name='{row[1]}'")
                found = True
        except Exception as e:
            print(f"Error checking {table}: {e}")

    if not found:
        print("[-] Image not found in any active table.")
    
    conn.close()

if __name__ == "__main__":
    # filename without path, just unique part
    target = "1765905718549" 
    find_image_reference(target)
