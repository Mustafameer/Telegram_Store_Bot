"""
خطة دمج productimages مع imagestorage
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def check_and_plan():
    """فحص وتخطيط الدمج"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("📊 فحص جداول الصور")
        print("=" * 60)
        
        # معلومات productimages
        print("\n1️⃣ جدول productimages:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'productimages'
            ORDER BY ordinal_position
        """)
        for col_name, data_type in cursor.fetchall():
            print(f"  - {col_name}: {data_type}")
        
        # عدد الصور في productimages
        cursor.execute("SELECT COUNT(*) FROM productimages")
        count_pi = cursor.fetchone()[0]
        print(f"\n  📸 عدد الصور: {count_pi}")
        
        # معلومات imagestorage
        print("\n2️⃣ جدول imagestorage:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'imagestorage'
            ORDER BY ordinal_position
        """)
        for col_name, data_type in cursor.fetchall():
            print(f"  - {col_name}: {data_type}")
        
        # عدد الصور في imagestorage
        cursor.execute("SELECT COUNT(*) FROM imagestorage")
        count_is = cursor.fetchone()[0]
        print(f"\n  📸 عدد الصور: {count_is}")
        
        # عينة من البيانات
        print("\n3️⃣ عينة من productimages:")
        cursor.execute("SELECT imageid, productid, imageorder FROM productimages LIMIT 3")
        for img_id, prod_id, order in cursor.fetchall():
            print(f"  - imageid={img_id}, productid={prod_id}, order={order}")
        
        print("\n" + "=" * 60)
        print("✅ الخطة:")
        print("=" * 60)
        print("""
1. إضافة أعمدة productid و imageorder إلى imagestorage
2. نسخ البيانات من productimages إلى imagestorage
3. تحديث جميع الاستعلامات للاستخدام من imagestorage فقط
4. حذف جدول productimages

الفوائد:
- جدول واحد بدلاً من اثنين
- بيانات الصور (filedata) في نفس الجدول
- تبسيط الكود والاستعلامات
        """)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_plan()
