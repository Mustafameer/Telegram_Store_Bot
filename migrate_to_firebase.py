"""
🗄️ تحديث قاعدة البيانات لـ Firebase
إضافة أعمدة لتخزين روابط Firebase بدلاً من BYTEA
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def add_firebase_columns():
    """إضافة أعمدة Firebase إلى جدول imagestorage"""
    
    print("=" * 60)
    print("🗄️  تحديث قاعدة البيانات - إضافة أعمدة Firebase")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            print("\n📝 تحديث PostgreSQL...")
            
            # فحص الأعمدة الموجودة
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='imagestorage'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # إضافة عمود url إذا لم يكن موجوداً
            if 'url' not in existing_columns:
                print("   • إضافة عمود url...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN url TEXT")
                print("     ✅ تم")
            else:
                print("   ✓ عمود url موجود بالفعل")
            
            # إضافة عمود firebase_filename
            if 'firebase_filename' not in existing_columns:
                print("   • إضافة عمود firebase_filename...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN firebase_filename TEXT")
                print("     ✅ تم")
            else:
                print("   ✓ عمود firebase_filename موجود بالفعل")
            
            # إضافة عمود firebase_folder
            if 'firebase_folder' not in existing_columns:
                print("   • إضافة عمود firebase_folder...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN firebase_folder TEXT DEFAULT 'telegram-images'")
                print("     ✅ تم")
            else:
                print("   ✓ عمود firebase_folder موجود بالفعل")
            
            # إضافة عمود migrated_to_firebase
            if 'migrated_to_firebase' not in existing_columns:
                print("   • إضافة عمود migrated_to_firebase...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN migrated_to_firebase BOOLEAN DEFAULT FALSE")
                print("     ✅ تم")
            else:
                print("   ✓ عمود migrated_to_firebase موجود بالفعل")
        
        else:
            print("\n📝 تحديث SQLite...")
            
            # SQLite - check if columns exist by trying to access them
            cursor.execute("PRAGMA table_info(imagestorage)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'url' not in columns:
                print("   • إضافة عمود url...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN url TEXT")
                print("     ✅ تم")
            else:
                print("   ✓ عمود url موجود بالفعل")
            
            if 'firebase_filename' not in columns:
                print("   • إضافة عمود firebase_filename...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN firebase_filename TEXT")
                print("     ✅ تم")
            else:
                print("   ✓ عمود firebase_filename موجود بالفعل")
            
            if 'firebase_folder' not in columns:
                print("   • إضافة عمود firebase_folder...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN firebase_folder TEXT DEFAULT 'telegram-images'")
                print("     ✅ تم")
            else:
                print("   ✓ عمود firebase_folder موجود بالفعل")
            
            if 'migrated_to_firebase' not in columns:
                print("   • إضافة عمود migrated_to_firebase...")
                cursor.execute("ALTER TABLE imagestorage ADD COLUMN migrated_to_firebase BOOLEAN DEFAULT 0")
                print("     ✅ تم")
            else:
                print("   ✓ عمود migrated_to_firebase موجود بالفعل")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ تم التحديث بنجاح!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()


def verify_columns():
    """التحقق من وجود الأعمدة"""
    
    print("\n" + "=" * 60)
    print("🔍 التحقق من الأعمدة")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='imagestorage'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            print(f"\n📊 الأعمدة الموجودة ({len(columns)}):")
            for col_name, col_type in columns:
                print(f"   • {col_name}: {col_type}")
        
        else:
            cursor.execute("PRAGMA table_info(imagestorage)")
            columns = cursor.fetchall()
            print(f"\n📊 الأعمدة الموجودة ({len(columns)}):")
            for col_id, col_name, col_type, notnull, default, pk in columns:
                print(f"   • {col_name}: {col_type}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")


if __name__ == '__main__':
    add_firebase_columns()
    verify_columns()
