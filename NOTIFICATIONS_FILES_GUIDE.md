# 📁 دليل الملفات والمسارات - نظام الإشعارات

## 🎯 الملفات الرئيسية للنظام

### Backend Files (Python)

#### 1. bot.py (الملف الرئيسي)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\bot.py
📊 الحجم: ~14,700 سطر
🔧 الوظيفة: Bot الرئيسي + Flask API + دوال الإشعارات
```

**الأقسام المضافة:**
- **السطر 26**: `from flask import Flask, request, jsonify`
- **السطور 97-166**: Flask app initialization و API endpoints
- **السطور 3832-3877**: `save_notification()` function
- **السطور 3879-3970**: `get_customer_notifications()` function
- **السطور 3972-4002**: `mark_notification_as_read()` function
- **السطور 14680-14685**: Flask thread startup

#### 2. requirements.txt (المتطلبات)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\requirements.txt
✅ التغيير: إضافة Flask
```

**المحتوى:**
```
Flask
psycopg2-binary
pyTelegramBotAPI
...
```

#### 3. test_notifications_api.py (أداة الاختبار)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\test_notifications_api.py
🎯 الوظيفة: اختبار API endpoints
```

**الدوال:**
- `test_health()` - فحص صحة API
- `test_get_notifications()` - اختبار الحصول على الإشعارات
- `test_mark_as_read()` - اختبار وضع العلامة

---

### Frontend Files (Flutter)

#### 1. notification_service.dart (الخدمة)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app\lib\services\notification_service.dart
✨ جديد تماماً
🎯 الوظيفة: التواصل مع API
```

**الدوال:**
- `getNotifications()` - احصل على الإشعارات
- `markAsRead()` - علّم كمقروء
- `streamUnreadNotifications()` - تحديث مستمر
- `getApiUrl()` - اختيار الـ API

#### 2. notification_model.dart (النموذج)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app\lib\models\notification_model.dart
✨ جديد تماماً
🎯 الوظيفة: نموذج بيانات الإشعار
```

**الفئة:**
- `AppNotification` - نموذج الإشعار
  - `fromJson()` - من JSON
  - `toJson()` - إلى JSON
  - `getFormattedTime()` - وقت قراء
  - `getIcon()` - أيقونة
  - `getColor()` - لون

#### 3. notifications_screen.dart (الشاشة)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app\lib\screens\notifications_screen.dart
✨ جديد تماماً
🎯 الوظيفة: عرض الإشعارات
```

**الفئات:**
- `NotificationsScreen` - الشاشة الرئيسية
- `_NotificationCard` - بطاقة الإشعار

#### 4. home_screen.dart (التعديل)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app\lib\screens\home_screen.dart
🔧 معدّل
🎯 إضافة: notifications destination و screen
```

**التعديلات:**
- **السطر 14**: إضافة import للـ notifications_screen
- **السطور 120-130**: إضافة notifications في destinations
- **السطور 353-365**: إضافة notifications في _buildContent

---

### Documentation Files

#### 1. NOTIFICATIONS_SYSTEM_GUIDE.md (الدليل الشامل)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\NOTIFICATIONS_SYSTEM_GUIDE.md
📖 النوع: دليل شامل (300+ سطر)
🎯 المحتوى:
   - نظرة عامة
   - البنية الفنية
   - دوال Python
   - API endpoints
   - تطبيق Flutter
   - الإعداد والتشغيل
   - حالات الاستخدام
   - الاختبار
   - استكشاف الأخطاء
```

#### 2. NOTIFICATIONS_QUICK_START.md (دليل سريع)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\NOTIFICATIONS_QUICK_START.md
📖 النوع: دليل للبدء السريع (15 دقيقة)
🎯 المحتوى:
   - 3 خطوات فقط للتشغيل
   - أمثلة API
   - حل المشاكل الشائعة
```

#### 3. NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md (التفاصيل الفنية)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md
📖 النوع: تفاصيل تقنية شاملة
🎯 المحتوى:
   - ملخص الإنجاز
   - الملفات المعدّلة
   - التدفق التقني
   - الأداء
   - الأمان
   - الإحصائيات
```

#### 4. NOTIFICATIONS_SUMMARY.md (ملخص تنفيذي)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\NOTIFICATIONS_SUMMARY.md
📖 النوع: ملخص تنفيذي
🎯 المحتوى:
   - الملخص التنفيذي
   - قائمة التغييرات
   - البنية التقنية
   - الاستخدام
   - Checklist
```

#### 5. NOTIFICATIONS_FILES_GUIDE.md (هذا الملف)
```
📍 المسار: c:\Users\Hp\Desktop\TelegramStoreBot\NOTIFICATIONS_FILES_GUIDE.md
📖 النوع: دليل الملفات
🎯 المحتوى:
   - مسارات جميع الملفات
   - شرح كل ملف
   - ارتباطات الملفات
```

---

## 📊 خريطة الملفات الكاملة

```
TelegramStoreBot/
│
├─ 📄 bot.py ← [MAIN BOT + API]
│  ├─ Flask app (السطر 97)
│  ├─ API endpoints (السطور 99-157)
│  ├─ save_notification() (السطر 3832)
│  ├─ get_customer_notifications() (السطر 3879)
│  ├─ mark_notification_as_read() (السطر 3972)
│  └─ Flask startup (السطر 14680)
│
├─ 📄 requirements.txt ← [DEPENDENCIES]
│  └─ Flask (مضاف جديد)
│
├─ 📄 test_notifications_api.py ← [TEST TOOL]
│  ├─ test_health()
│  ├─ test_get_notifications()
│  └─ test_mark_as_read()
│
├─ 📚 NOTIFICATIONS_SYSTEM_GUIDE.md ← [FULL GUIDE]
├─ 📚 NOTIFICATIONS_QUICK_START.md ← [QUICK START]
├─ 📚 NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md ← [TECHNICAL DETAILS]
├─ 📚 NOTIFICATIONS_SUMMARY.md ← [EXECUTIVE SUMMARY]
├─ 📚 NOTIFICATIONS_FILES_GUIDE.md ← [THIS FILE]
│
└─ flutter_store_app/
   │
   └─ lib/
      │
      ├─ services/
      │  ├─ notification_service.dart ← [NEW SERVICE]
      │  │  ├─ getNotifications()
      │  │  ├─ markAsRead()
      │  │  └─ streamUnreadNotifications()
      │  │
      │  ├─ postgres_service.dart (unchanged)
      │  └─ ...
      │
      ├─ models/
      │  ├─ notification_model.dart ← [NEW MODEL]
      │  │  └─ AppNotification class
      │  │
      │  ├─ database_models.dart (unchanged)
      │  └─ ...
      │
      ├─ screens/
      │  ├─ notifications_screen.dart ← [NEW SCREEN]
      │  │  ├─ NotificationsScreen
      │  │  └─ _NotificationCard
      │  │
      │  ├─ home_screen.dart ← [MODIFIED]
      │  │  └─ Added notifications destination & screen
      │  │
      │  ├─ cart_screen.dart (unchanged)
      │  ├─ orders_screen.dart (unchanged)
      │  └─ ...
      │
      └─ ...
```

---

## 🔗 العلاقات بين الملفات

### Flow الديناميكي للبيانات

```
Bot Event (e.g., closed_store_purchase)
    ↓
bot.py: save_notification()
    ↓
PostgreSQL: Notifications table
    ↓
Flutter: NotificationService.getNotifications()
    ↓
API: GET /api/notifications?customer_id=X
    ↓
bot.py: get_customer_notifications()
    ↓
PostgreSQL: SELECT * FROM Notifications
    ↓
Flask: jsonify(notifications)
    ↓
Flutter: AppNotification.fromJson()
    ↓
NotificationsScreen: ListView.builder()
    ↓
User: يرى الإشعار في التطبيق
```

---

## 🚀 الترتيب الصحيح للقراءة

### للمبتدئين:
1. **NOTIFICATIONS_QUICK_START.md** ← ابدأ هنا! (15 دقيقة)
2. **NOTIFICATIONS_SUMMARY.md** ← فهم سريع (5 دقائق)

### للمطورين:
1. **bot.py** ← اقرأ الأقسام المضافة (السطور المذكورة)
2. **notification_service.dart** ← خدمة الـ HTTP
3. **notification_model.dart** ← نموذج البيانات
4. **notifications_screen.dart** ← واجهة المستخدم

### للإداريين:
1. **NOTIFICATIONS_SYSTEM_GUIDE.md** ← الدليل الكامل
2. **NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md** ← التفاصيل
3. **NOTIFICATIONS_SUMMARY.md** ← الملخص

---

## 🔍 البحث عن أشياء محددة

### أبحث عن: تعريف save_notification
**الملف:** bot.py
**السطر:** 3832
**الدالة:** `def save_notification(...)`

### أبحث عن: API endpoints
**الملف:** bot.py
**السطور:** 99-157
**الدوال:** `@app.route(...)`

### أبحث عن: واجهة الإشعارات
**الملف:** notifications_screen.dart
**الفئة:** `NotificationsScreen`

### أبحث عن: نموذج الإشعار
**الملف:** notification_model.dart
**الفئة:** `AppNotification`

### أبحث عن: الخدمة
**الملف:** notification_service.dart
**الفئة:** `NotificationService`

---

## 💾 حفظ ومراجعة

### إذا احتجت مراجعة:
- bot.py: الأسطر **26, 97-166, 3832-4002, 14680-14685**
- home_screen.dart: الأسطر **14, 120-130, 353-365**

### إذا احتجت تعديل API:
- bot.py: السطور **99-157**
- notification_service.dart: السطور **15-35, 45-80, 95-115**

### إذا احتجت تغيير الـ UI:
- notifications_screen.dart: كاملاً

---

## 📱 المسارات المهمة للتطبيق

```
flutter_store_app/
├─ lib/
│  ├─ services/notification_service.dart    ← الخدمة
│  ├─ models/notification_model.dart        ← النموذج
│  ├─ screens/notifications_screen.dart     ← الشاشة
│  └─ screens/home_screen.dart              ← التكامل
│
└─ pubspec.yaml                             ← http package موجود
```

---

## ⚡ التشغيل السريع

### خطوة 1: افتح ملف bot.py
```
قم بـ Ctrl+G واذهب للسطر 26 لرؤية Flask import
```

### خطوة 2: افتح ملف home_screen.dart
```
اضغط Ctrl+F وابحث عن "notifications_screen"
```

### خطوة 3: اختبر الـ API
```
اقرأ test_notifications_api.py
```

---

## 🎯 الملفات التي تحتاج اهتماماً

### CRITICAL (يجب أن تعمل):
- ✅ bot.py - main bot
- ✅ notification_service.dart - HTTP service
- ✅ notifications_screen.dart - UI

### IMPORTANT (يجب أن تكون صحيحة):
- ✅ notification_model.dart - data model
- ✅ home_screen.dart - integration
- ✅ requirements.txt - dependencies

### DOCUMENTATION (للمرجعية):
- 📚 جميع ملفات NOTIFICATIONS_*.md

---

## 🔄 تحديث الملفات

### إذا احتجت تحديث:

**البوت:**
```
تعديل bot.py → اختبر مع test_notifications_api.py
```

**التطبيق:**
```
تعديل Flutter files → اختبر مع flutter run
```

**الوثائق:**
```
تحديث NOTIFICATIONS_*.md مع التغييرات
```

---

## ✅ Checklist للملفات

### Backend
- [x] bot.py - Flask app مُضاف
- [x] bot.py - API endpoints مُضافة
- [x] bot.py - دوال الإشعارات مُضافة
- [x] requirements.txt - Flask مُضاف
- [x] test_notifications_api.py - أداة اختبار جاهزة

### Frontend
- [x] notification_service.dart - خدمة مُنشأة
- [x] notification_model.dart - نموذج مُنشأ
- [x] notifications_screen.dart - شاشة مُنشأة
- [x] home_screen.dart - معدّل بالشكل صحيح

### Documentation
- [x] NOTIFICATIONS_SYSTEM_GUIDE.md
- [x] NOTIFICATIONS_QUICK_START.md
- [x] NOTIFICATIONS_IMPLEMENTATION_COMPLETE.md
- [x] NOTIFICATIONS_SUMMARY.md
- [x] NOTIFICATIONS_FILES_GUIDE.md (هذا الملف)

---

**آخر تحديث:** [اليوم]
**الحالة:** ✅ كاملة
**النسخة:** 1.0
