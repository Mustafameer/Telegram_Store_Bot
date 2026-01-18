#!/usr/bin/env python3
"""
ترحيل البيانات من categories إلى Categories بالأسماء الصحيحة
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🔄 ترحيل البيانات إلى جدول Categories بالأسماء الصحيحة")
print("="*70)

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Step 1: Drop the old table if exists
    print("\n📍 الخطوة 1️⃣: حذف الجدول القديم إذا كان موجوداً")
    cursor.execute('DROP TABLE IF EXISTS "categories" CASCADE;')
    print("   ✅ تم حذف الجدول القديم")
    
    # Step 2: Create Categories table with proper column names
    print("\n📍 الخطوة 2️⃣: إنشاء جدول Categories بالأسماء الصحيحة")
    
    cursor.execute('''
        CREATE TABLE "Categories" (
            "CategoryID" SERIAL PRIMARY KEY,
            "SellerID" INTEGER NOT NULL,
            "Name" TEXT NOT NULL,
            "OrderIndex" INTEGER DEFAULT 0,
            "ImagePath" TEXT
        );
    ''')
    print("   ✅ تم إنشاء جدول Categories")
    
    # Step 3: Create sequence for CategoryID
    print("\n📍 الخطوة 3️⃣: إنشاء Sequence للـ CategoryID")
    try:
        cursor.execute('DROP SEQUENCE IF EXISTS categories_categoryid_seq;')
        cursor.execute('''
            CREATE SEQUENCE categories_categoryid_seq
            START 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;
        ''')
        cursor.execute('ALTER TABLE "Categories" ALTER COLUMN "CategoryID" SET DEFAULT nextval(\'categories_categoryid_seq\'::regclass);')
        print("   ✅ تم إنشاء الـ Sequence")
    except Exception as e:
        print(f"   ⚠️  تحذير: {e}")
    
    # Step 4: Create Products table if needed (same fix)
    print("\n📍 الخطوة 4️⃣: التحقق من جدول Products")
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'products'
        );
    """)
    
    if cursor.fetchone()[0]:
        print("   ⚠️  جدول Products الأقدم موجود")
        cursor.execute('DROP TABLE IF EXISTS "products" CASCADE;')
        print("   ✅ تم حذفه")
    
    # Create Products table with proper names
    cursor.execute('''
        CREATE TABLE "Products" (
            "ProductID" SERIAL PRIMARY KEY,
            "SellerID" INTEGER NOT NULL,
            "CategoryID" INTEGER NOT NULL,
            "Name" TEXT NOT NULL,
            "Description" TEXT,
            "Price" NUMERIC,
            "WholesalePrice" NUMERIC,
            "Quantity" INTEGER,
            "ImagePath" TEXT,
            "Status" TEXT DEFAULT 'active',
            FOREIGN KEY ("CategoryID") REFERENCES "Categories"("CategoryID") ON DELETE CASCADE,
            FOREIGN KEY ("SellerID") REFERENCES "sellers"("sellerid")
        );
    ''')
    print("   ✅ تم إنشاء جدول Products")
    
    conn.commit()
    
    print("\n✅ تم الترحيل بنجاح!")
    print("   الآن التطبيق سيتمكن من قراءة الفئات بشكل صحيح")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
        conn.close()

print("\n" + "="*70)
