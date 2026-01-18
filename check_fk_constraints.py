"""
التحقق من Foreign Keys على جدول imagestorage
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def check_foreign_keys():
    """التحقق من الـ Foreign Keys"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔍 التحقق من Foreign Keys على جدول imagestorage")
        print("=" * 60)
        
        # البحث عن جميع الـ constraints
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'imagestorage'
        """)
        
        constraints = cursor.fetchall()
        print(f"\n📋 الـ Constraints الموجودة:")
        for name, ctype in constraints:
            print(f"  - {name}: {ctype}")
        
        # البحث عن Foreign Keys بطريقة مختلفة
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'imagestorage'
        """)
        
        fks = cursor.fetchall()
        if fks:
            print(f"\n🔗 Foreign Keys المكتشفة:")
            for constraint, col, ftable, fcol in fks:
                print(f"  - {constraint}: {col} → {ftable}.{fcol}")
        else:
            print(f"\n✅ لا توجد Foreign Keys على جدول imagestorage")
        
        # التحقق من Primary Key
        cursor.execute("""
            SELECT column_name
            FROM information_schema.constraint_column_usage
            WHERE table_name = 'imagestorage'
            AND constraint_name LIKE '%pkey'
        """)
        
        pk = cursor.fetchone()
        if pk:
            print(f"\n🔑 Primary Key: {pk[0]}")
        
        # التحقق من وجود جدول productimages
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'productimages'
            )
        """)
        
        productimages_exists = cursor.fetchone()[0]
        print(f"\n✅ جدول productimages موجود: {productimages_exists}")
        
        if productimages_exists:
            # التحقق من Foreign Keys على productimages
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'productimages'
            """)
            
            fks = cursor.fetchall()
            if fks:
                print(f"\n🔗 Foreign Keys على productimages:")
                for constraint, col, ftable, fcol in fks:
                    print(f"  - {constraint}: {col} → {ftable}.{fcol}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_foreign_keys()
