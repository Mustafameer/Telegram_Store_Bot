"""
🔍 فحص الصور من قاعدة البيانات المحلية
اختبار سريع بدون اتصال إلى الـ Cloud
"""

import sqlite3
import os
from base64 import b64encode, b64decode

def check_local_images():
    """فحص صور SQLite المحلية"""
    print("=" * 60)
    print("🔍 فحص صور قاعدة البيانات المحلية")
    print("=" * 60)
    
    db_path = 'data/telegram_bot.db'
    
    if not os.path.exists(db_path):
        print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # الحصول على عدد الصور
        cursor.execute("SELECT COUNT(*) FROM imagestorage")
        count = cursor.fetchone()[0]
        print(f"\n📊 عدد الصور في قاعدة البيانات: {count}")
        
        if count == 0:
            print("⚠️  لا توجد صور في قاعدة البيانات")
            conn.close()
            return
        
        # الحصول على أول صورة
        cursor.execute("""
            SELECT imageid, filename, productid, 
                   length(filedata) as size
            FROM imagestorage 
            ORDER BY imageid 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            image_id, filename, product_id, size = result
            
            print(f"\n📝 معلومات أول صورة:")
            print(f"   • ID: {image_id}")
            print(f"   • الاسم: {filename}")
            print(f"   • ID المنتج: {product_id}")
            print(f"   • حجم البيانات: {size} bytes")
            
            # الحصول على البيانات الفعلية
            cursor.execute("""
                SELECT filedata 
                FROM imagestorage 
                WHERE imageid = ?
            """, (image_id,))
            
            file_data = cursor.fetchone()
            if file_data:
                filedata = file_data[0]
                
                if isinstance(filedata, bytes):
                    print(f"\n✅ البيانات من نوع bytes")
                    print(f"   • الـ 20 بايت الأول (hex): {filedata[:20].hex()}")
                    
                    # فحص التوقيع
                    if filedata[:4] == b'\x89PNG':
                        print(f"   • ✅ توقيع PNG صحيح!")
                    elif filedata[:2] == b'\xff\xd8':
                        print(f"   • ✅ توقيع JPEG صحيح!")
                    else:
                        print(f"   • ⚠️  توقيع غير معروف: {filedata[:4]}")
                    
                    # محاولة التحويل إلى base64
                    try:
                        b64_data = b64encode(filedata).decode('utf-8')
                        print(f"\n✅ تحويل إلى base64 نجح!")
                        print(f"   • الـ 50 حرف الأول: {b64_data[:50]}")
                        
                        # محاولة فك التشفير
                        decoded = b64decode(b64_data)
                        print(f"   • ✅ فك التشفير نجح! ({len(decoded)} bytes)")
                        
                        # تحقق من التطابق
                        if decoded == filedata:
                            print(f"   • ✅ البيانات المفكوكة تطابق الأصلية!")
                        
                    except Exception as e:
                        print(f"\n❌ خطأ في التحويل: {e}")
                else:
                    print(f"\n⚠️  البيانات ليست bytes: {type(filedata)}")
                    
                    # ربما تكون hex string
                    if isinstance(filedata, str):
                        print(f"   • البيانات نص (hex string): {filedata[:50]}")
                        
                        # محاولة التحويل من hex
                        try:
                            decoded_bytes = bytes.fromhex(filedata)
                            print(f"   • ✅ تحويل من hex نجح! ({len(decoded_bytes)} bytes)")
                            print(f"   • الـ 20 بايت الأول: {decoded_bytes[:20].hex()}")
                        except Exception as e:
                            print(f"   • ❌ خطأ في التحويل من hex: {e}")
        
        # مقارنة مع الملف المحلي
        print(f"\n📁 مقارنة مع الملف المحلي:")
        local_path = os.path.join('data', 'Images', filename)
        
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                local_data = f.read()
            
            print(f"   • ✅ وجدت الملف المحلي")
            print(f"   • حجم الملف: {len(local_data)} bytes")
            
            if isinstance(filedata, bytes) and local_data == filedata:
                print(f"   • ✅ البيانات متطابقة تماماً!")
            else:
                print(f"   • ⚠️  البيانات مختلفة")
        else:
            print(f"   • ⚠️  الملف المحلي غير موجود: {local_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_local_images()
