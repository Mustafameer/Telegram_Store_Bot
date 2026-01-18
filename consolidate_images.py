"""
دمج جداول الصور: productimages مع imagestorage
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def consolidate_images():
    """دمج الجداول"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔄 دمج جداول الصور")
        print("=" * 60)
        
        # 1️⃣ إضافة أعمدة جديدة إلى imagestorage
        print("\n1️⃣ إضافة أعمدة productid و imageorder إلى imagestorage...")
        try:
            cursor.execute("""
                ALTER TABLE imagestorage
                ADD COLUMN productid INTEGER,
                ADD COLUMN imageorder INTEGER DEFAULT 0
            """)
            print("   ✅ تم إضافة الأعمدة")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("   ⚠️ الأعمدة موجودة بالفعل")
            else:
                raise
        
        # 2️⃣ نسخ البيانات من productimages
        print("\n2️⃣ نسخ البيانات من productimages...")
        cursor.execute("""
            UPDATE imagestorage
            SET productid = pi.productid,
                imageorder = pi.imageorder
            FROM productimages pi
            WHERE imagestorage.imageid = pi.imageid
        """)
        print(f"   ✅ تم تحديث {cursor.rowcount} صورة")
        
        # 3️⃣ إضافة Foreign Key لـ products
        print("\n3️⃣ إضافة Foreign Key...")
        try:
            cursor.execute("""
                ALTER TABLE imagestorage
                ADD CONSTRAINT fk_imagestorage_productid
                FOREIGN KEY (productid) REFERENCES products(productid) ON DELETE CASCADE
            """)
            print("   ✅ تم إضافة Foreign Key")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("   ⚠️ Foreign Key موجود بالفعل")
            else:
                raise
        
        # 4️⃣ عرض عدد الصور
        print("\n4️⃣ التحقق من البيانات:")
        cursor.execute("SELECT COUNT(*) FROM imagestorage WHERE productid IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"   📸 عدد الصور مع productid: {count}")
        
        # 5️⃣ حذف productimages
        print("\n5️⃣ حذف جدول productimages...")
        cursor.execute("DROP TABLE IF EXISTS productimages CASCADE")
        print("   ✅ تم حذف جدول productimages")
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ اكتمل الدمج بنجاح!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()

if __name__ == "__main__":
    confirm = input("⚠️  هذه عملية ستغير هيكل قاعدة البيانات. هل أنت متأكد؟ (yes/no): ")
    if confirm.lower() == 'yes':
        consolidate_images()
    else:
        print("❌ تم الإلغاء")
