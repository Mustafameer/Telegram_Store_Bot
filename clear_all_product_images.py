"""
حذف جميع الصور من قاعدة البيانات
"""
import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
IS_POSTGRES = DATABASE_URL and 'postgres' in DATABASE_URL.lower()

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect('data/telegram_store.db')

def clear_all_product_images():
    """حذف جميع صور المنتجات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🗑️ جاري حذف جميع الصور من قاعدة البيانات...")
        
        if IS_POSTGRES:
            # حذف جميع الصور
            cursor.execute('DELETE FROM productimages')
            print(f"✅ تم حذف {cursor.rowcount} صورة من productimages")
            
            # إعادة تعيين العدادات إذا لزم الأمر
            cursor.execute('ALTER SEQUENCE productimages_imageid_seq RESTART WITH 1')
            print("✅ تم إعادة تعيين العداد")
            
        else:
            # حذف جميع الصور (SQLite)
            cursor.execute('DELETE FROM ProductImages')
            print(f"✅ تم حذف {cursor.rowcount} صورة من ProductImages")
            
            # إعادة تعيين العداد (SQLite)
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="ProductImages"')
            cursor.execute('INSERT INTO sqlite_sequence (name, seq) VALUES ("ProductImages", 0)')
            print("✅ تم إعادة تعيين العداد")
        
        conn.commit()
        conn.close()
        
        print("\n✅ تم حذف جميع الصور بنجاح!")
        print("🎯 جاهز لحفظ الصور الجديدة")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print(f"نوع قاعدة البيانات: {'PostgreSQL (Railway)' if IS_POSTGRES else 'SQLite'}")
    print("\n⚠️ جاري حذف جميع الصور...")
    clear_all_product_images()
