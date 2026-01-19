"""
🧹 تنظيف الصور القديمة والمحذوفة
للتشغيل الدوري (مرة في الأسبوع أو الشهر)
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES, IMAGES_FOLDER

def cleanup_orphaned_images():
    """
    حذف الصور التي لا تنتمي إلى أي منتج
    (المنتجات المحذوفة لكن صورها بقيت)
    """
    print("🧹 جاري البحث عن صور يتيمة...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن صور لمنتجات محذوفة
        if IS_POSTGRES:
            cursor.execute("""
                SELECT filename FROM imagestorage 
                WHERE productid NOT IN (SELECT productid FROM products WHERE productid IS NOT NULL)
                AND productid IS NOT NULL
            """)
        else:
            cursor.execute("""
                SELECT filename FROM imagestorage 
                WHERE productid NOT IN (SELECT ProductID FROM Products WHERE ProductID IS NOT NULL)
                AND productid IS NOT NULL
            """)
        
        orphaned = cursor.fetchall()
        deleted_count = 0
        freed_space = 0
        
        for (filename,) in orphaned:
            try:
                img_path = os.path.join(IMAGES_FOLDER, filename)
                if os.path.exists(img_path):
                    size = os.path.getsize(img_path)
                    os.remove(img_path)
                    freed_space += size
                    deleted_count += 1
                    print(f"  ✓ حذف {filename} ({size/1024:.1f} KB)")
                
                # حذف من قاعدة البيانات
                if IS_POSTGRES:
                    cursor.execute("DELETE FROM imagestorage WHERE filename = %s", (filename,))
                else:
                    cursor.execute("DELETE FROM imagestorage WHERE filename = ?", (filename,))
                    
            except Exception as e:
                print(f"  ❌ خطأ في حذف {filename}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ تم حذف {deleted_count} صورة يتيمة ({freed_space/1024/1024:.2f} MB)")
        return deleted_count, freed_space
        
    except Exception as e:
        print(f"❌ خطأ في التنظيف: {e}")
        return 0, 0


def cleanup_old_images(days=90):
    """
    حذف صور قديمة جداً (غير مستخدمة)
    
    Args:
        days: عدد أيام عدم الاستخدام (افتراضي: 90 يوم)
    """
    print(f"\n🧹 جاري البحث عن صور أقدم من {days} يوم...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حساب التاريخ
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # البحث عن الصور القديمة
        if IS_POSTGRES:
            cursor.execute("""
                SELECT filename FROM imagestorage 
                WHERE uploadedby = 'legacy'
                AND uploaddate < %s
            """, (cutoff_date,))
        else:
            cursor.execute("""
                SELECT filename FROM imagestorage 
                WHERE uploadedby = 'legacy'
                AND uploaddate < ?
            """, (cutoff_date.isoformat(),))
        
        old_images = cursor.fetchall()
        deleted_count = 0
        freed_space = 0
        
        for (filename,) in old_images:
            try:
                img_path = os.path.join(IMAGES_FOLDER, filename)
                if os.path.exists(img_path):
                    size = os.path.getsize(img_path)
                    os.remove(img_path)
                    freed_space += size
                    deleted_count += 1
                    print(f"  ✓ حذف {filename} ({size/1024:.1f} KB)")
                
                # حذف من قاعدة البيانات
                if IS_POSTGRES:
                    cursor.execute("DELETE FROM imagestorage WHERE filename = %s", (filename,))
                else:
                    cursor.execute("DELETE FROM imagestorage WHERE filename = ?", (filename,))
                    
            except Exception as e:
                print(f"  ❌ خطأ في حذف {filename}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ تم حذف {deleted_count} صورة قديمة ({freed_space/1024/1024:.2f} MB)")
        return deleted_count, freed_space
        
    except Exception as e:
        print(f"❌ خطأ في التنظيف: {e}")
        return 0, 0


def cleanup_duplicate_images():
    """
    البحث عن صور مكررة (نفس الاسم)
    والإبقاء على نسخة واحدة فقط
    """
    print("\n🧹 جاري البحث عن صور مكررة...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن الصور المكررة
        if IS_POSTGRES:
            cursor.execute("""
                SELECT filename, COUNT(*) as count
                FROM imagestorage
                GROUP BY filename
                HAVING COUNT(*) > 1
            """)
        else:
            cursor.execute("""
                SELECT filename, COUNT(*) as count
                FROM imagestorage
                GROUP BY filename
                HAVING COUNT(*) > 1
            """)
        
        duplicates = cursor.fetchall()
        deleted_count = 0
        
        for filename, count in duplicates:
            # الإبقاء على النسخة الأولى وحذف الباقي
            if IS_POSTGRES:
                cursor.execute("""
                    DELETE FROM imagestorage
                    WHERE filename = %s
                    AND imageid NOT IN (
                        SELECT imageid FROM imagestorage 
                        WHERE filename = %s
                        ORDER BY imageid
                        LIMIT 1
                    )
                """, (filename, filename))
            else:
                # SQLite version
                cursor.execute("""
                    DELETE FROM imagestorage
                    WHERE filename = ?
                    AND imageid NOT IN (
                        SELECT imageid FROM imagestorage 
                        WHERE filename = ?
                        ORDER BY imageid
                        LIMIT 1
                    )
                """, (filename, filename))
            
            deleted_count += count - 1
            print(f"  ✓ حذفت {count-1} نسخ مكررة من {filename}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ تم حذف {deleted_count} نسخة مكررة")
        return deleted_count
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن المكررات: {e}")
        return 0


def get_database_stats():
    """الحصول على إحصائيات قاعدة البيانات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # عدد الصور
        if IS_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM imagestorage")
        else:
            cursor.execute("SELECT COUNT(*) FROM imagestorage")
        
        total_images = cursor.fetchone()[0]
        
        # حجم المجلد
        folder_size = 0
        if os.path.exists(IMAGES_FOLDER):
            for filename in os.listdir(IMAGES_FOLDER):
                filepath = os.path.join(IMAGES_FOLDER, filename)
                if os.path.isfile(filepath):
                    folder_size += os.path.getsize(filepath)
        
        conn.close()
        
        return total_images, folder_size
        
    except Exception as e:
        print(f"❌ خطأ في الحصول على الإحصائيات: {e}")
        return 0, 0


def main():
    """تشغيل جميع عمليات التنظيف"""
    print("=" * 50)
    print("🧹 تنظيف الصور من قاعدة البيانات")
    print("=" * 50)
    
    # الإحصائيات قبل التنظيف
    before_images, before_size = get_database_stats()
    print(f"\n📊 قبل التنظيف:")
    print(f"   • عدد الصور: {before_images}")
    print(f"   • حجم المجلد: {before_size/1024/1024:.2f} MB")
    
    # تشغيل التنظيف
    orphaned_count, orphaned_space = cleanup_orphaned_images()
    old_count, old_space = cleanup_old_images(days=90)
    duplicate_count = cleanup_duplicate_images()
    
    # الإحصائيات بعد التنظيف
    after_images, after_size = get_database_stats()
    print(f"\n📊 بعد التنظيف:")
    print(f"   • عدد الصور: {after_images}")
    print(f"   • حجم المجلد: {after_size/1024/1024:.2f} MB")
    
    # ملخص النتائج
    total_deleted = orphaned_count + old_count + duplicate_count
    total_freed = orphaned_space + old_space
    
    print(f"\n✨ ملخص التنظيف:")
    print(f"   • الصور المحذوفة: {total_deleted}")
    print(f"   • المساحة المحررة: {total_freed/1024/1024:.2f} MB")
    print(f"   • نسبة التحسن: {(before_size - after_size)/before_size*100:.1f}%" if before_size > 0 else "")
    
    print("\n" + "=" * 50)
    print("✅ تم إكمال التنظيف بنجاح!")
    print("=" * 50)


if __name__ == '__main__':
    main()
