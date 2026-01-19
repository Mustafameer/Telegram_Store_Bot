# 🚀 Firebase Setup - خطوة بخطوة

## المرحلة 1: إعداد Firebase Console

### 1.1: الدخول والتسجيل
```
1. افتح https://console.firebase.google.com
2. اختر حساب Google (أنشئ واحد إذا لم يكن لديك)
3. اضغط "Create Project"
```

### 1.2: بيانات المشروع
```
Project Name: telegram-store-bot
Analytics: OFF (غير مهم للآن)
Location: (أي واحد)
```

### 1.3: تفعيل Firebase Storage
```
في Firebase Console:
  ├─ Storage (الجانب الأيسر)
  ├─ Create bucket
  └─ Location: us-central1
     Bucket name: telegram-store-bot.appspot.com
     Security: Start in test mode (للآن)
```

---

## المرحلة 2: تحميل Service Account Key

### 2.1: الذهاب للـ Keys
```
في Firebase Console:
  ├─ Project Settings (⚙️ الترس العلوي)
  ├─ Service Accounts
  ├─ Generate Key (تحت Python)
  └─ حفظ الملف باسم: firebase-key.json
```

### 2.2: تثبيت الملف
```
انسخ firebase-key.json إلى:
  C:\Users\Hp\Desktop\TelegramStoreBot\firebase-key.json
```

**⚠️ مهم: لا تشارك هذا الملف مع أحد!**

---

## المرحلة 3: تثبيت المكتبات

```bash
pip install firebase-admin Pillow python-dotenv
```

---

## المرحلة 4: تحديث Bot.py

### أ. استيراد Firebase
```python
import firebase_admin
from firebase_admin import storage, credentials
```

### ب. تهيئة Firebase
```python
# في بداية bot.py بعد الاستيرادات
try:
    if not firebase_admin.get_app():
        cred = credentials.Certificate('firebase-key.json')
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'telegram-store-bot.appspot.com'
        })
except ValueError:
    pass  # التطبيق موجود بالفعل
```

### ج. دالة رفع الصور
```python
def upload_image_to_firebase(file_bytes, filename, folder='telegram-images'):
    """رفع صورة إلى Firebase Storage"""
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f'{folder}/{filename}')
        blob.upload_from_string(file_bytes, content_type='image/jpeg')
        
        # الحصول على رابط عام
        blob.make_public()
        url = blob.public_url
        
        print(f"✅ تم رفع الصورة: {url}")
        return url
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return None
```

---

## المرحلة 5: تحديث قاعدة البيانات

```sql
-- إضافة عمود الرابط
ALTER TABLE imagestorage ADD COLUMN url TEXT;
ALTER TABLE imagestorage ADD COLUMN firebase_id TEXT;

-- مثال لإدراج صورة جديدة
INSERT INTO imagestorage (filename, productid, url, uploadedby)
VALUES ('image.png', 1, 'https://storage.googleapis.com/...', 'firebase');
```

---

## ✅ التحقق

بعد الانتهاء:
1. جرّب تحميل صورة من Telegram
2. تحقق من Firebase Console → Storage
3. يجب أن ترى الملف مرفوع بنجاح

---

## 🎯 الخطوات التالية

بعد الانتهاء من هنا:
- تحديث Flutter لقراءة الروابط
- اختبار شامل
- هجرة الصور القديمة

---

**هل انتهيت من الخطوات 1-3؟ أم تريد مساعدة؟** 🤔
