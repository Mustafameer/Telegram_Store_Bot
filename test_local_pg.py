import psycopg2
import sys

def test_connection(password):
    try:
        print(f"Testing with password: '{password}'")
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password=password,
            connect_timeout=3
        )
        print(f"SUCCESS: Connected with password '{password}'")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILED with password '{password}': {e}")
        return False

if test_connection("123"):
    sys.exit(0)
else:
    sys.exit(1)
