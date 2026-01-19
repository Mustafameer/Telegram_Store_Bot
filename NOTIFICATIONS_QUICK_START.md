# 🚀 دليل البدء السريع - نظام الإشعارات

## 3 خطوات فقط لتشغيل نظام الإشعارات

### الخطوة 1️⃣: تحديث Bot

```bash
# تثبيت Flask (إذا لم يكن مثبتاً)
pip install Flask

# أو تحديث كل المتطلبات
pip install -r requirements.txt
```

### الخطوة 2️⃣: تشغيل Bot مع API

```bash
python bot.py
```

**الإخراج المتوقع:**
```
[INFO] Starting Flask API server in background...
✅ Flask API started successfully
🌐 Starting Flask API on port 5000...
[INFO] Starting polling...
```

### الخطوة 3️⃣: تشغيل تطبيق Flutter

```bash
cd flutter_store_app
flutter run
```

---

## ✨ كيفية الاختبار

### 1. اختبر API مباشرة

في نافذة terminal جديدة:
```bash
python test_notifications_api.py
```

### 2. اختبر من المتصفح

افتح المتصفح وانتقل إلى:
```
http://localhost:5000/api/health
```

يجب أن تري:
```json
{"status": "ok", "service": "telegram-store-bot"}
```

### 3. احصل على إشعارات عميل معين

استبدل `TELEGRAM_ID` برقم حقيقي:
```
http://localhost:5000/api/notifications?customer_id=TELEGRAM_ID
```

---

## 🎯 تدفق الاستخدام

### سيناريو: عميل يشتري من متجر مقفول

1. العميل يختار منتجات ويضغط "شراء"
2. Bot يتحقق من صحة الطلب
3. Bot يحفظ إشعار في قاعدة البيانات
4. Bot يحذف صور المنتجات المشتراة
5. Bot يرسل صور للعميل عبر Telegram
6. تطبيق Flutter يُحدّث الإشعارات تلقائياً
7. العميل يرى الإشعار في تبويب "الإشعارات"

---

## 📱 مكان الإشعارات في التطبيق

```
Home Screen (الشاشة الرئيسية)
│
├─ 📊 لوحة التحكم
├─ 🛒 سلة المشتريات
├─ 📬 الإشعارات ← جديد!
├─ ⚙️ الإعدادات
├─ 📦 الطلبات
└─ 💬 الرسائل
```

اضغط على **الإشعارات 📬** لفتح شاشة الإشعارات.

---

## 🧪 أمثلة API

### احصل على الإشعارات غير المقروءة

```bash
curl "http://localhost:5000/api/notifications?customer_id=123456789&unread_only=true"
```

**الرد:**
```json
{
    "success": true,
    "count": 2,
    "notifications": [
        {
            "notificationId": 1,
            "type": "closed_store_purchase",
            "title": "✅ تم تأكيد طلبك",
            "message": "تم شراء 3 منتجات بنجاح!",
            "totalAmount": 150.50,
            "isRead": false,
            "createdAt": "2024-01-15T10:30:00"
        }
    ]
}
```

### علّم إشعار كمقروء

```bash
curl -X POST http://localhost:5000/api/notifications/1/read
```

**الرد:**
```json
{
    "success": true,
    "message": "تم وضع علامة على الإشعار"
}
```

---

## ⚙️ الإعدادات المتقدمة

### تغيير رقم منفذ API

```bash
# Windows
set API_PORT=8000
python bot.py

# Linux/Mac
export API_PORT=8000
python bot.py
```

### تحديث تكرار تحديث الإشعارات في التطبيق

**في `notification_service.dart`:**
```dart
streamUnreadNotifications(
    customerId: widget.currentUserId,
    refreshInterval: 15,  // كل 15 ثانية بدلاً من 30
)
```

---

## 🐛 حل المشاكل الشائعة

### المشكلة: "Address already in use"
```
Error: [Errno 48] Address already in use
```

**الحل:**
```bash
# غيّر رقم المنفذ
set API_PORT=5001
python bot.py
```

### المشكلة: "flask not found"
```
ModuleNotFoundError: No module named 'flask'
```

**الحل:**
```bash
pip install flask
```

### المشكلة: لا تظهر الإشعارات في التطبيق

**الحل:**
1. تأكد من معرف التليجرام صحيح
2. تحقق من وجود إشعارات في قاعدة البيانات
3. افحص سجلات Flutter
4. تأكد من أن API يعمل

---

## 📊 الإحصائيات

| المكون | الحالة | الملاحظات |
|------|------|----------|
| Bot Python | ✅ جاهز | Flask API يعمل |
| قاعدة البيانات | ✅ جاهز | Notifications table موجود |
| Flutter Service | ✅ جاهز | NotificationService جاهز |
| Flutter UI | ✅ جاهز | NotificationsScreen موجود |
| التوثيق | ✅ جاهز | شامل وسهل الفهم |

---

## 🎓 قراءة إضافية

- [دليل النظام الشامل](NOTIFICATIONS_SYSTEM_GUIDE.md)
- [تفاصيل التطبيق](NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md)
- [اختبار API](test_notifications_api.py)

---

## ✅ تم!

نظام الإشعارات مثبّت وجاهز للاستخدام!

**الخطوات التالية:**
1. شغّل Bot: `python bot.py`
2. شغّل التطبيق: `flutter run`
3. اختبر من خلال شراء في متجر مقفول
4. شاهد الإشعار يظهر في التطبيق!

---

**تم التحديث:** [اليوم]
**الإصدار:** 1.0 Production Ready ✅
