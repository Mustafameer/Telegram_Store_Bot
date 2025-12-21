import psycopg2
from urllib.parse import urlparse
import os

DB_URL = "postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway"

def clean():
    try:
        result = urlparse(DB_URL)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM ImageStorage WHERE FileName = 'test_upload_dummy.jpg'")
        conn.commit()
        print(f"Deleted {cur.rowcount} rows.")
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    clean()
    if os.path.exists(r"c:\Users\Hp\Desktop\TelegramStoreBot\data\Images\test_upload_dummy.jpg"):
        os.remove(r"c:\Users\Hp\Desktop\TelegramStoreBot\data\Images\test_upload_dummy.jpg")
        print("Deleted local file.")
