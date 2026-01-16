#!/usr/bin/env python3
"""
Script to check what tables exist in the cloud PostgreSQL database
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'switchback.proxy.rlwy.net')
DB_PORT = int(os.getenv('DB_PORT', '20266'))
DB_NAME = os.getenv('DB_NAME', 'railway')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_SSL = os.getenv('DB_SSL', 'true').lower() == 'true'

def check_tables():
    try:
        print('📡 Connecting to PostgreSQL...')
        sslmode = 'require' if DB_SSL else 'disable'
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=sslmode
        )
        
        cursor = conn.cursor()
        print('✅ Connected')
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        
        if tables:
            print(f'\n📊 Found {len(tables)} tables:')
            for (table_name,) in tables:
                print(f'   - {table_name}')
        else:
            print('❌ No tables found in the database')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    check_tables()
