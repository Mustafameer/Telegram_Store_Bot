import os
import sys

try:
    import psycopg2
except ImportError:
    print("❌ Error: 'psycopg2' library is missing.")
    print("Please run: pip install psycopg2-binary")
    input("Press Enter to exit...")
    sys.exit(1)

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        try:
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"Error connecting: {e}")
            return None
    return None

def clear_images():
    print("Connecting to Cloud DB...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect.")
        return

    cursor = conn.cursor()
    try:
        print("Clearing ImageStorage table...")
        cursor.execute("DELETE FROM ImageStorage")
        print(f"Deleted {cursor.rowcount} images.")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.environ.get('DATABASE_URL'):
        print("Error: DATABASE_URL not set. Run this with run_cloud.bat")
    else:
        confirm = input("Are you sure you want to DELETE ALL IMAGES from Cloud? (yes/no): ")
        if confirm.lower() == 'yes':
            clear_images()
        else:
            print("Cancelled.")
