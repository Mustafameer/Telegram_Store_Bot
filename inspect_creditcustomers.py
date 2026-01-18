#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='creditcustomers' ORDER BY ordinal_position")
cols = [row[0] for row in cur.fetchall()]
print(f"Columns: {cols}\n")

# Get all data
cur.execute("SELECT * FROM creditcustomers")
rows = cur.fetchall()
print(f"Total records: {len(rows)}")
for row in rows:
    print(row)

cur.close()
conn.close()
