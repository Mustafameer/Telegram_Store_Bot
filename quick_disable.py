#!/usr/bin/env python3
"""
Disable polling on Railway by setting feature flag
"""
import sys
sys.path.insert(0, '/c/Users/Hp/Desktop/TelegramStoreBot')

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Now import bot to use get_db_connection
from bot import get_db_connection

print("🔧 Disabling polling on Railway...")

try:
    conn = get_db_connection()
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
    print("✅ Successfully disabled polling on Railway!")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
