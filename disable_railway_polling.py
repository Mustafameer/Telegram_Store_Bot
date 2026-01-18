#!/usr/bin/env python3
"""
Quick script to disable polling on the Railway bot instance by setting a feature flag
"""
import os
import psycopg2
from psycopg2.extras import DictCursor

def disable_railway_polling():
    # Always use PostgreSQL when DATABASE_URL is available
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        print("Using cloud PostgreSQL database...")
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
            print("✅ Set DISABLE_POLLING=1 in PostgreSQL cloud database")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ Error connecting to PostgreSQL: {e}")
    else:
        print("DATABASE_URL not set. Using local SQLite fallback...")
        import sqlite3
        conn = sqlite3.connect('data/telegramstorebot.db')
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
            VALUES ('DISABLE_POLLING', 1, 'Disable bot polling when Railway instance is running')
            ON CONFLICT(FlagName) DO UPDATE SET FlagValue=1
        """)
        
        conn.commit()
        print("✅ Set DISABLE_POLLING=1 in local SQLite database")
        conn.close()

if __name__ == '__main__':
    disable_railway_polling()
