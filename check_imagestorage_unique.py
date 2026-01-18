"""
فحص بيانات imagestorage وحل مشكلة UNIQUE constraint
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def check_and_fix():
    """فحص وإصلاح مشكلة UNIQUE"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔍 فحص بيانات imagestorage")
        print("=" * 60)
        
        # عرض جميع البيانات
        cursor.execute("SELECT filename, imageid, updatedat FROM imagestorage ORDER BY imageid")
        rows = cursor.fetchall()
        
        print(f"\n📊 عدد الصور: {len(rows)}")
        for filename, imageid, updatedat in rows:
            print(f"  - {imageid}: {filename} ({updatedat})")
        
        # البحث عن imageids المكررة
        cursor.execute("""
            SELECT imageid, COUNT(*) as count
            FROM imagestorage
            GROUP BY imageid
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n⚠️ صور مكررة (imageid):")
            for imageid, count in duplicates:
                print(f"  - imageid {imageid}: {count} نسخ")
        
        # تحقق من الـ constraints
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'imagestorage'
        """)
        
        constraints = cursor.fetchall()
        print(f"\n📋 الـ Constraints:")
        for name, ctype in constraints:
            print(f"  - {name}: {ctype}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_fix()
