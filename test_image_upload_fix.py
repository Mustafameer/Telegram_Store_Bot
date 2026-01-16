#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify image upload to cloud works correctly
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from urllib.parse import urlparse

def test_image_storage():
    """Test ImageStorage table operations"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set. Cannot test cloud upload.")
        return False
    
    print(f"🔗 Testing database connection...")
    
    try:
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'
        )
        cursor = conn.cursor()
        print("✅ Connected to PostgreSQL")
        
        # Create table
        print("\n📋 Creating ImageStorage table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage (
                FileName TEXT PRIMARY KEY,
                FileData BYTEA,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✅ ImageStorage table ready")
        
        # Test insert
        print("\n📤 Testing image insert...")
        test_filename = f"test_{int(time.time())}.jpg"
        test_data = b"FAKE_JPG_DATA_HERE"
        
        cursor.execute(
            "INSERT INTO ImageStorage (FileName, FileData) VALUES (%s, %s) ON CONFLICT (FileName) DO NOTHING",
            (test_filename, test_data)
        )
        conn.commit()
        print(f"✅ Inserted test image: {test_filename}")
        
        # Test select
        print("\n📥 Testing image retrieve...")
        cursor.execute("SELECT FileData FROM ImageStorage WHERE FileName = %s", (test_filename,))
        result = cursor.fetchone()
        
        if result:
            retrieved_data = result[0]
            if isinstance(retrieved_data, memoryview):
                retrieved_data = retrieved_data.tobytes()
            
            if retrieved_data == test_data:
                print(f"✅ Retrieved image data matches: {len(retrieved_data)} bytes")
            else:
                print(f"❌ Data mismatch!")
                return False
        else:
            print("❌ Image not found after insert!")
            return False
        
        # Check total count
        print("\n📊 Checking table statistics...")
        cursor.execute("SELECT COUNT(*) FROM ImageStorage")
        count = cursor.fetchone()[0]
        print(f"✅ Total images in storage: {count}")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        cursor.execute("DELETE FROM ImageStorage WHERE FileName = %s", (test_filename,))
        conn.commit()
        print(f"✅ Removed test image")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED - Image upload should work!")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_image_storage()
    sys.exit(0 if success else 1)
