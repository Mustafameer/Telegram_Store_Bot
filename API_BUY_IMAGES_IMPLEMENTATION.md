# 🎉 تطبيق API جديد لشراء الصور من التطبيق Flutter

## 📋 الملخص

تم إضافة **endpoint جديد** في Flask API لمعالجة شراء الصور من التطبيق Flutter. هذا الـ endpoint يقوم بنفس العمليات التي تحدث عند شراء صور من البوت:

1. ✅ إضافة معاملة ائتمانية
2. ✅ تحديث كمية المنتج
3. ✅ حذف الصور المشتراة من قاعدة البيانات
4. ✅ حفظ إشعار للعميل في الـ App

---

## 🔧 التغييرات المطبقة

### 1️⃣ إضافة Endpoint جديد في `bot.py`

**الملف:** `bot.py`  
**الموقع:** بعد `/api/health` endpoint  
**الـ Endpoint:** `POST /api/buy-images`

#### الوظائف:
```python
@app.route('/api/buy-images', methods=['POST'])
def api_buy_images():
    """
    شراء صور من التطبيق - نفس عملية شراء الصور من البوت
    
    Parameters (JSON):
        - product_id: معرف المنتج
        - quantity: عدد الصور المراد شراؤها
        - customer_id: معرف العميل (من قاعدة البيانات)
        - seller_id: معرف البائع
        - customer_telegram_id: معرف التليجرام للعميل (لحفظ الإشعار)
    
    Returns:
        JSON: نتائج العملية
    """
```

#### العمليات التي يقوم بها:
1. **التحقق من البيانات:** يتحقق من وجود جميع الحقول المطلوبة
2. **التحقق من المنتج:** يتأكد من وجود المنتج والكمية المطلوبة متاحة
3. **إضافة معاملة ائتمانية:** يضيف المبلغ لحساب العميل الآجل
4. **تحديث الكمية:** ينقص الكمية المتاحة من المنتج
5. **حذف الصور:** يحذف الصور المشتراة من:
   - قاعدة البيانات (جدول imagestorage)
   - القرص المحلي (IMAGES_FOLDER)
6. **حفظ إشعار:** ينشئ إشعار للعميل في التطبيق
7. **ترجع النتائج:** JSON مع حالة العملية

---

### 2️⃣ تحديث `select_images_screen.dart`

**الملف:** `flutter_store_app/lib/screens/select_images_screen.dart`

#### التغييرات:

##### أ) إضافة Imports
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
```

##### ب) استبدال `_buyImages()` Method
- **قبل:** كانت تضيف معاملة ائتمانية محلياً فقط
- **بعد:** تستدعي API endpoint في البوت

#### العملية الجديدة:
```
1. التحقق من الكمية والعميل
2. استدعاء _callBotBuyImagesAPI() 
   ↓
3. الـ API يقوم بـ:
   - إضافة معاملة ائتمانية
   - حذف الصور من قاعدة البيانات والقرص
   - حفظ إشعار
4. عرض رسالة نجاح للمستخدم
```

##### ج) إضافة Method جديد `_callBotBuyImagesAPI()`
```dart
Future<Map<String, dynamic>> _callBotBuyImagesAPI({
  required int productId,
  required int quantity,
  required int customerId,
  required int sellerId,
  required int customerTelegramId,
}) async
```

**المميزات:**
- تصل إلى `http://localhost:5000/api/buy-images`
- ترسل بيانات JSON
- timeout 15 ثانية
- تعالج الأخطاء بشكل صحيح
- تطبع معلومات التصحيح (debug logs)

---

## 📊 سير العملية الكاملة

### السيناريو: شراء صور من التطبيق

```
┌─────────────────────────────────────┐
│  Flutter App - Select Images Screen │
└─────────────────────────────────────┘
           ↓ (يضغط زر "شراء الصور")
┌─────────────────────────────────────┐
│  _buyImages() Method                │
│  ✓ التحقق من الكمية                │
│  ✓ جلب بيانات العميل               │
│  ✓ استدعاء API                     │
└─────────────────────────────────────┘
           ↓
        HTTP POST
    (json with product_id, 
     quantity, customer_id, etc)
           ↓
┌─────────────────────────────────────┐
│  Bot - /api/buy-images Endpoint     │
│  ✓ التحقق من البيانات               │
│  ✓ إضافة معاملة ائتمانية            │
│  ✓ تحديث كمية المنتج               │
│  ✓ حذف الصور من DB                 │
│  ✓ حذف ملفات الصور                  │
│  ✓ حفظ إشعار                        │
└─────────────────────────────────────┘
           ↓
      JSON Response
    (success: true,
     notification_saved: true)
           ↓
┌─────────────────────────────────────┐
│  Flutter App                        │
│  ✓ عرض رسالة نجاح                  │
│  ✓ العودة للشاشة السابقة            │
│  ✓ يمكن للعميل جلب الإشعار لاحقاً    │
└─────────────────────────────────────┘
```

---

## 🔌 API Endpoint Details

### Request

**URL:** `POST http://localhost:5000/api/buy-images`

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "product_id": 1,
  "quantity": 3,
  "customer_id": 5,
  "seller_id": 10,
  "customer_telegram_id": 1041977029
}
```

### Response (Success)

**Status:** 200

**Body:**
```json
{
  "success": true,
  "message": "تم شراء 3 صورة بنجاح",
  "total_amount": 150000,
  "deleted_images": 3,
  "notification_saved": true
}
```

### Response (Error)

**Status:** 400 / 404 / 500

**Body:**
```json
{
  "success": false,
  "error": "Not enough images available"
}
```

---

## 🗑️ حذف الصور

### الخطوات:

1. **جلب الصور:** يجلب أول N صورة من قاعدة البيانات (حيث N = الكمية المشتراة)
2. **الحذف المحلي:** يحذف الملفات من `IMAGES_FOLDER`
3. **حذف قاعدة البيانات:** يحذف السجلات من جدول `imagestorage`
4. **Commit:** يحفظ التغييرات على قاعدة البيانات

### الكود:
```python
for image_id, filename in images_to_delete:
    # حذف من قاعدة البيانات
    cursor.execute('DELETE FROM imagestorage WHERE imageid = %s', (image_id,))
    
    # حذف الملف من القرص المحلي
    img_path = os.path.join(IMAGES_FOLDER, filename)
    if os.path.exists(img_path):
        os.remove(img_path)
```

---

## 💾 حفظ الإشعار

### الدالة:
```python
save_notification(
    customer_telegram_id=customer_telegram_id,
    notification_type='image_purchase',
    title='✅ تم شراء الصور',
    message=f'تم شراء {quantity} صورة من {product_name} بنجاح! المبلغ: {total_amount:,.0f} د.ع',
    product_names=product_name,
    total_amount=total_amount,
    seller_id=seller_id,
    data=None
)
```

### الإشعار سيظهر في:
- `/api/notifications` endpoint
- تطبيق Flutter (عند جلب الإشعارات)

---

## ✅ الحالة الجاهزة

### ✓ Backend (Python/Bot)
- ✅ Flask API endpoint مضاف
- ✅ معالجة خطأ شاملة
- ✅ حذف الصور يعمل
- ✅ حفظ الإشعار يعمل
- ✅ تحديث الكمية يعمل

### ✓ Frontend (Flutter)
- ✅ Imports مضافة
- ✅ `_buyImages()` محدثة لاستدعاء API
- ✅ `_callBotBuyImagesAPI()` مضافة
- ✅ معالجة الأخطاء مضافة
- ✅ رسائل النجاح/الفشل مضافة

### ✓ Database
- ✅ جدول Notifications موجود
- ✅ جدول imagestorage موجود
- ✅ جدول Products موجود
- ✅ جدول CustomerCredit موجود

---

## 🚀 خطوات الاختبار

### 1. بدء البوت
```bash
python bot.py
```
- يجب أن ترى: "🌐 Starting Flask API on port 5000..."
- ويجب أن ترى: "✅ Flask API started successfully"

### 2. فتح التطبيق
- سجّل دخول كعميل
- اختر متجر مغلق
- اختر منتج يحتوي على صور

### 3. شراء الصور
- اضغط "اختر عدد الصور"
- اختر كمية
- اضغط "شراء الصور"

### 4. التحقق
```
✅ يجب أن ترى:
- رسالة نجاح في التطبيق
- معاملة ائتمانية في كشف الحساب
- إشعار في البوت (إن وجد endpoint للعميل)
- الصور لم تعد موجودة في المنتج
- الكمية قلّت في المتجر
```

---

## 🔍 معلومات التصحيح (Debug Logs)

### في Terminal (البوت):
```
📱 API: Buying 3 images for product 1 by customer 5
✅ Image purchase completed: 3 images, 3 deleted, notification saved: True
```

### في Flutter:
```
📡 API Response: 200
📡 Response Body: {"success":true,"message":"تم شراء 3 صورة بنجاح",...}
```

---

## 📝 ملاحظات مهمة

1. **الـ URL:** يجب أن يكون `http://localhost:5000` - إذا كان البوت على سيرفر آخر، غيّر الـ URL
2. **CORS:** إذا كان Flask يرفض الطلبات من Flutter، قد تحتاج لإضافة CORS support
3. **Timeout:** إذا كانت العملية بطيئة جداً، غيّر `timeout: 15 seconds`
4. **Notifications:** العميل سيحصل على إشعار - يمكنه رؤيته عبر `/api/notifications?customer_id=...`

---

## ✨ الفوائد

✅ **توحيد العملية:** نفس الكود يعمل للبوت والتطبيق  
✅ **الصور تُحذف تلقائياً:** لا حاجة لحذفها يدوياً  
✅ **الإشعارات تصل:** العميل يعرف أن الشراء نجح  
✅ **الكمية تتحدث تلقائياً:** لا حاجة للتحديث اليدوي  
✅ **معاملة آمنة:** معاملة ائتمانية موثقة بشكل صحيح  

