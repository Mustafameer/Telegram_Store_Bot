"""
🔍 فحص سريع لصور PostgreSQL
التحقق من صحة البيانات المحفوظة
"""

import psycopg2
import os
from base64 import b64decode, b64encode
import sys

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES

def check_images_in_database():
    """فحص صور PostgreSQL"""
    print("=" * 60)
    print("🔍 فحص صور قاعدة البيانات")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على أول صورة
        cursor.execute("SELECT imageid, filename, filedata FROM imagestorage LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("❌ لا توجد صور في قاعدة البيانات")
            conn.close()
            return
        
        image_id, filename, filedata = result
        
        print(f"\n📝 معلومات الصورة:")
        print(f"   • ID: {image_id}")
        print(f"   • الاسم: {filename}")
        print(f"   • نوع البيانات الخام: {type(filedata)}")
        print(f"   • طول البيانات: {len(filedata) if filedata else 0}")
        
        if filedata:
            # فحص البيانات الخام
            if isinstance(filedata, bytes):
                print(f"\n✅ البيانات من نوع bytes (صحيح!)")
                print(f"   • الـ 20 بايت الأول: {filedata[:20].hex()}")
                
                # فحص توقيع PNG
                if filedata[:4] == b'\x89PNG':
                    print(f"   • ✅ توقيع PNG صحيح!")
                elif filedata[:2] == b'\xff\xd8':
                    print(f"   • ✅ توقيع JPEG صحيح!")
                else:
                    print(f"   • ⚠️  التوقيع غير معروف: {filedata[:4]}")
            else:
                print(f"\n⚠️  البيانات ليست bytes، بل: {type(filedata)}")
                print(f"   • المحتوى: {str(filedata)[:100]}")
        
        # فحص encode() function
        print(f"\n🔄 اختبار encode(filedata, 'base64'):")
        cursor.execute(
            "SELECT encode(filedata, 'base64') as b64_data FROM imagestorage WHERE imageid = %s",
            (image_id,)
        )
        result2 = cursor.fetchone()
        
        if result2:
            b64_string = result2[0]
            print(f"   • نوع البيانات المرجعة: {type(b64_string)}")
            print(f"   • الـ 50 حرف الأول: {str(b64_string)[:50]}")
            
            # محاولة فك التشفير
            try:
                decoded = b64decode(b64_string)
                print(f"   • ✅ تم فك التشفير بنجاح!")
                print(f"   • طول البيانات المفكوكة: {len(decoded)}")
                print(f"   • التوقيع: {decoded[:4].hex()}")
            except Exception as e:
                print(f"   • ❌ خطأ في فك التشفير: {e}")
        
        # مقارنة مع الملف المحلي
        print(f"\n📁 مقارنة مع الملف المحلي:")
        local_path = os.path.join('data', 'Images', filename)
        
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                local_data = f.read()
            
            print(f"   • وجدت الملف المحلي!")
            print(f"   • حجم الملف المحلي: {len(local_data)} bytes")
            
            if isinstance(filedata, bytes):
                if local_data == filedata:
                    print(f"   • ✅ البيانات متطابقة تماماً!")
                else:
                    print(f"   • ⚠️  البيانات مختلفة!")
                    print(f"      - حجم البيانات من الـ DB: {len(filedata)}")
                    print(f"      - حجم الملف المحلي: {len(local_data)}")
        else:
            print(f"   • ⚠️  الملف المحلي غير موجود: {local_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_images_in_database()
