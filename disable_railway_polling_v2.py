#!/usr/bin/env python3
"""
Disable polling on Railway PostgreSQL
"""
import os
from dotenv import load_dotenv
import psycopg2

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
print(f"Connecting to: {DATABASE_URL}")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FeatureFlags (
            FlagName TEXT PRIMARY KEY,
            FlagValue INTEGER DEFAULT 0,
            Description TEXT
        )
    """)
    
    # Set polling disabled flag
    cursor.execute("""
        INSERT INTO FeatureFlags (FlagName, FlagValue, Description) 
        VALUES (%s, %s, %s)
        ON CONFLICT(FlagName) DO UPDATE SET FlagValue=%s
    """, ('DISABLE_POLLING', 1, 'Disable bot polling when Railway instance is running', 1))
    
    conn.commit()
    print("✅ Set DISABLE_POLLING=1 in Railway PostgreSQL database")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
