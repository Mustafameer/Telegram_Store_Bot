import os
import psycopg2
from urllib.parse import urlparse

# Hardcoded for diagnosis
DB_URL = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def check_images():
    try:
        print("[*] Connecting to Railway Postgres...")
        result = urlparse(DB_URL)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cur = conn.cursor()
        
        # Check Table Existence
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'imagestorage');")
        exists = cur.fetchone()[0]
        
        if not exists:
            print("[!] Table 'ImageStorage' DOES NOT EXIST in Cloud DB.")
            return
            
        # Count Images
        cur.execute("SELECT COUNT(*) FROM ImageStorage;")
        count = cur.fetchone()[0]
        print(f"[+] Table 'ImageStorage' found.")
        print(f"[*] Total Images in Cloud: {count}")
        
        if count > 0:
            cur.execute("SELECT FileName, length(FileData) FROM ImageStorage LIMIT 5;")
            print("[*] First 5 files:")
            for row in cur.fetchall():
                print(f"   - {row[0]} ({row[1]} bytes)")
                
        conn.close()
        
    except Exception as e:
        print(f"[!] Connection Failed: {e}")

if __name__ == "__main__":
    check_images()
