"""
🔥 Firebase Storage Service
خدمة رفع الصور إلى Firebase بدلاً من PostgreSQL
"""

import firebase_admin
from firebase_admin import storage, credentials
import os
import time
import uuid
from pathlib import Path

class FirebaseImageService:
    """خدمة تحميل الصور إلى Firebase Storage"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """تهيئة Firebase مرة واحدة فقط"""
        if self._initialized:
            return
        
        try:
            # تحقق من وجود firebase-key.json
            if not os.path.exists('firebase-key.json'):
                print("⚠️  firebase-key.json غير موجود")
                print("📍 تأكد من وجود الملف في: " + os.path.abspath('firebase-key.json'))
                self._bucket = None
                self._initialized = True
                return
            
            # تهيئة Firebase
            try:
                app = firebase_admin.get_app()
            except ValueError:
                # التطبيق غير مهيأ بعد
                cred = credentials.Certificate('firebase-key.json')
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'telegram-store-bot.appspot.com'
                })
            
            self._bucket = storage.bucket()
            self._initialized = True
            print("✅ Firebase تم تهيئتها بنجاح")
            
        except Exception as e:
            print(f"❌ خطأ في تهيئة Firebase: {e}")
            self._bucket = None
            self._initialized = True
    
    def upload_image(self, file_bytes, filename, folder='telegram-images'):
        """
        رفع صورة إلى Firebase Storage
        
        Args:
            file_bytes: بيانات الملف (bytes)
            filename: اسم الملف
            folder: المجلد (تنظيمي)
        
        Returns:
            dict: {'success': bool, 'url': str, 'filename': str}
        """
        try:
            if self._bucket is None:
                return {'success': False, 'error': 'Firebase not initialized'}
            
            # توليد اسم فريد
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            ext = Path(filename).suffix or '.jpg'
            unique_filename = f"{timestamp}_{unique_id}{ext}"
            
            # رفع الملف
            blob = self._bucket.blob(f'{folder}/{unique_filename}')
            blob.upload_from_string(
                file_bytes,
                content_type='image/jpeg'
            )
            
            # جعل الملف عام (public)
            blob.make_public()
            
            # الحصول على الرابط
            url = blob.public_url
            
            print(f"✅ تم رفع الصورة: {unique_filename}")
            print(f"   الرابط: {url}")
            
            return {
                'success': True,
                'filename': unique_filename,
                'url': url,
                'size': len(file_bytes),
                'folder': folder
            }
            
        except Exception as e:
            print(f"❌ خطأ في رفع الصورة: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def delete_image(self, blob_path):
        """
        حذف صورة من Firebase Storage
        
        Args:
            blob_path: المسار الكامل (folder/filename)
        
        Returns:
            bool: نجاح العملية
        """
        try:
            if self._bucket is None:
                return False
            
            blob = self._bucket.blob(blob_path)
            blob.delete()
            
            print(f"✅ تم حذف الصورة: {blob_path}")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في حذف الصورة: {e}")
            return False
    
    def get_image_url(self, filename, folder='telegram-images'):
        """
        الحصول على رابط صورة موجودة
        
        Args:
            filename: اسم الملف
            folder: المجلد
        
        Returns:
            str: رابط الصورة أو None
        """
        try:
            if self._bucket is None:
                return None
            
            blob = self._bucket.blob(f'{folder}/{filename}')
            blob.make_public()
            return blob.public_url
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return None
    
    def list_images(self, folder='telegram-images'):
        """
        عرض قائمة الصور في مجلد معين
        
        Args:
            folder: المجلد
        
        Returns:
            list: قائمة أسماء الملفات
        """
        try:
            if self._bucket is None:
                return []
            
            blobs = self._bucket.list_blobs(prefix=folder + '/')
            filenames = [blob.name.replace(folder + '/', '') for blob in blobs]
            
            print(f"📁 الصور في مجلد '{folder}': {len(filenames)}")
            return filenames
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return []


# Singleton instance
_firebase_service = FirebaseImageService()

def get_firebase_service():
    """الحصول على instance من Firebase Service"""
    return _firebase_service
