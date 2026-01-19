#!/usr/bin/env python3
"""
Script to add image storage columns to Categories table in PostgreSQL
This allows category images to be stored directly in the database
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def add_image_columns():
    """Add ImageFileName, ImageUrl, and ImageData columns to Categories table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if columns already exist
        print("🔍 Checking for existing columns...")
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'Categories' AND column_name IN ('ImageFileName', 'ImageUrl', 'ImageData')
        """)
        existing = [row[0] for row in cursor.fetchall()]
        
        if 'ImageFileName' in existing:
            print("⚠️  ImageFileName column already exists")
        else:
            print("📝 Adding ImageFileName column...")
            cursor.execute('ALTER TABLE "Categories" ADD COLUMN "ImageFileName" VARCHAR(255)')
            print("✅ ImageFileName column added")
        
        if 'ImageUrl' in existing:
            print("⚠️  ImageUrl column already exists")
        else:
            print("📝 Adding ImageUrl column...")
            cursor.execute('ALTER TABLE "Categories" ADD COLUMN "ImageUrl" VARCHAR(1000)')
            print("✅ ImageUrl column added")
        
        if 'ImageData' in existing:
            print("⚠️  ImageData column already exists")
        else:
            print("📝 Adding ImageData column...")
            cursor.execute('ALTER TABLE "Categories" ADD COLUMN "ImageData" BYTEA')
            print("✅ ImageData column added")
        
        conn.commit()
        print("✅ All category image columns added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔧 Adding image storage columns to Categories table...\n")
    success = add_image_columns()
    if not success:
        print("\n❌ Migration failed")
        exit(1)
    print("\n✅ Migration completed successfully!")
