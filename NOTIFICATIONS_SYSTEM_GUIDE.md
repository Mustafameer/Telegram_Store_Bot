# 📬 نظام الإشعارات للتطبيق - التطبيق الكامل

## 🎯 نظرة عامة

تم بناء نظام إشعارات شامل للعميل يشمل:
1. **قاعدة البيانات**: جدول `Notifications` في PostgreSQL
2. **محرك التحفيز**: دالة `save_notification()` في bot.py
3. **API**: نقاط نهاية REST للحصول على الإشعارات وتحديثها
4. **تطبيق Flutter**: خدمة وشاشة كاملة لعرض الإشعارات

---

## 📊 البنية الفنية

### 1. قاعدة البيانات (PostgreSQL)

**جدول Notifications:**
```sql
CREATE TABLE "Notifications" (
    "NotificationID" SERIAL PRIMARY KEY,
    "CustomerTelegramID" BIGINT NOT NULL,
    "SellerID" INTEGER,
    "Type" VARCHAR(100),                      -- closed_store_purchase, refund, new_product, etc
    "Title" VARCHAR(255),                     -- عنوان الإشعار
    "Message" TEXT,                           -- محتوى الإشعار
    "ProductNames" VARCHAR(500),              -- أسماء المنتجات المشتراة
    "TotalAmount" NUMERIC(10,2),             -- المبلغ الإجمالي
    "IsRead" BOOLEAN DEFAULT FALSE,           -- هل تم قراءة الإشعار
    "CreatedAt" TIMESTAMP DEFAULT NOW(),      -- وقت الإنشاء
    "ReadAt" TIMESTAMP,                       -- وقت القراءة
    "Data" JSONB                              -- بيانات إضافية
);

-- Indexes للأداء:
CREATE INDEX idx_notifications_customer ON "Notifications"("CustomerTelegramID");
CREATE INDEX idx_notifications_created ON "Notifications"("CreatedAt" DESC);
CREATE INDEX idx_notifications_unread ON "Notifications"("CustomerTelegramID", "IsRead") 
    WHERE "IsRead" = FALSE;
```

### 2. دوال Python في bot.py

#### save_notification()
```python
save_notification(
    customer_telegram_id: int,
    notification_type: str,
    title: str,
    message: str,
    product_names: str = None,
    total_amount: float = None,
    seller_id: int = None,
    data: dict = None
) -> bool
```

**الاستخدام:**
```python
save_notification(
    customer_telegram_id=123456789,
    notification_type='closed_store_purchase',
    title='✅ تم تأكيد طلبك',
    message='تم شراء 3 منتجات بنجاح',
    product_names='منتج 1, منتج 2, منتج 3',
    total_amount=150.50,
    seller_id=45
)
```

#### get_customer_notifications()
```python
get_customer_notifications(
    customer_telegram_id: int,
    unread_only: bool = True
) -> List[Dict]
```

#### mark_notification_as_read()
```python
mark_notification_as_read(notification_id: int) -> bool
```

### 3. API Endpoints

#### GET /api/notifications
احصل على إشعارات العميل

**المعاملات:**
- `customer_id` (مطلوب): معرف التليجرام للعميل
- `unread_only` (اختياري): true/false (default: true)

**مثال:**
```
GET http://localhost:5000/api/notifications?customer_id=123456789&unread_only=true
```

**الرد:**
```json
{
    "success": true,
    "count": 3,
    "notifications": [
        {
            "notificationId": 1,
            "customerTelegramId": 123456789,
            "sellerId": 45,
            "type": "closed_store_purchase",
            "title": "✅ تم تأكيد طلبك",
            "message": "تم شراء 3 منتجات بنجاح",
            "productNames": "منتج 1, منتج 2, منتج 3",
            "totalAmount": 150.50,
            "isRead": false,
            "createdAt": "2024-01-15T10:30:00",
            "readAt": null,
            "data": null
        }
    ]
}
```

#### POST /api/notifications/{id}/read
ضع علامة على إشعار كمقروء

**مثال:**
```
POST http://localhost:5000/api/notifications/1/read
```

**الرد:**
```json
{
    "success": true,
    "message": "تم وضع علامة على الإشعار"
}
```

#### GET /api/health
تحقق من أن API يعمل

---

## 📱 تطبيق Flutter

### 1. NotificationService

**الملف:** `lib/services/notification_service.dart`

**الدوال الرئيسية:**

```dart
// احصل على الإشعارات
Future<List<AppNotification>> getNotifications({
    required int customerId,
    bool unreadOnly = true,
})

// ضع علامة على إشعار كمقروء
Future<bool> markAsRead(int notificationId)

// احصل على تحديث مستمر للإشعارات
Stream<List<AppNotification>> streamUnreadNotifications({
    required int customerId,
    int refreshInterval = 30,
})
```

### 2. AppNotification Model

**الملف:** `lib/models/notification_model.dart`

**الخصائص:**
- `notificationId`: معرف فريد
- `type`: نوع الإشعار (مثل 'closed_store_purchase')
- `title`: عنوان الإشعار
- `message`: محتوى الإشعار
- `productNames`: أسماء المنتجات
- `totalAmount`: المبلغ الإجمالي
- `isRead`: هل تم قراءة الإشعار
- `createdAt`: وقت الإنشاء
- `data`: بيانات JSON إضافية

**الدوال المساعدة:**
- `getFormattedTime()`: وقت قراء (مثل "قبل 5 دقائق")
- `getIcon()`: أيقونة بناء على النوع
- `getColor()`: لون بناء على النوع

### 3. NotificationsScreen

**الملف:** `lib/screens/notifications_screen.dart`

**الميزات:**
- 📋 قائمة الإشعارات مع التفاصيل
- ✅ تصفية الإشعارات (مقروءة/غير مقروءة)
- 🔄 تحديث اليدوي
- 📊 عرض معلومات الطلب والمبلغ
- ⏰ عرض الوقت بشكل قراء

### 4. تكامل التطبيق

تم إضافة الإشعارات إلى شاشة Home:

```dart
// في home_screen.dart
_getDestinations() {
  return [
    ...
    {'icon': Icons.notifications, 'label': 'الإشعارات 📬', 'count': _counts['notifications'] ?? 0},
    ...
  ];
}

// في _buildContent()
if (_selectedIndex == 3) {
  return NotificationsScreen(customerId: widget.currentUserId);
}
```

---

## 🔧 الإعداد والتشغيل

### 1. متطلبات Python

**requirements.txt:**
```
Flask                  # لـ API endpoints
psycopg2-binary       # PostgreSQL
...
```

**تثبيت:**
```bash
pip install -r requirements.txt
```

### 2. متطلبات Flutter

**pubspec.yaml:**
```yaml
dependencies:
  http: ^1.6.0          # للـ HTTP requests
  intl: ^0.20.2         # لتنسيق التاريخ/الوقت
  ...
```

**تحديث:**
```bash
cd flutter_store_app
flutter pub get
```

### 3. تشغيل Bot مع API

```bash
python bot.py
```

**الإخراج:**
```
[INFO] Starting Flask API server in background...
✅ Flask API started successfully
🌐 Starting Flask API on port 5000...
[INFO] Starting polling...
```

---

## 💡 حالات الاستخدام

### 1. شراء منتجات من متجر مقفول
```python
save_notification(
    customer_telegram_id=buyer_id,
    notification_type='closed_store_purchase',
    title='✅ تم تأكيد طلبك',
    message=f'تم شراء {count} منتج(ات) بنجاح!',
    product_names=', '.join(product_names),
    total_amount=total,
    seller_id=seller_id
)
```

### 2. استرجاع أموال
```python
save_notification(
    customer_telegram_id=buyer_id,
    notification_type='refund',
    title='💰 تم استرجاع أموالك',
    message=f'تم استرجاع {amount} د.ع',
    total_amount=amount
)
```

### 3. منتج جديد
```python
save_notification(
    customer_telegram_id=follower_id,
    notification_type='new_product',
    title='🆕 منتج جديد!',
    message=f'أضاف البائع منتج جديد: {product_name}',
    seller_id=seller_id
)
```

---

## 🧪 اختبار API

### استخدام curl:

```bash
# احصل على الإشعارات
curl "http://localhost:5000/api/notifications?customer_id=123456789"

# ضع علامة على إشعار
curl -X POST http://localhost:5000/api/notifications/1/read

# تحقق من الصحة
curl http://localhost:5000/api/health
```

### استخدام Postman:

1. **GET** `http://localhost:5000/api/notifications`
   - Parameters: `customer_id=123456789`, `unread_only=true`

2. **POST** `http://localhost:5000/api/notifications/1/read`

3. **GET** `http://localhost:5000/api/health`

---

## 🚀 التطوير المستقبلي

### ميزات إضافية:
1. ✨ **الإشعارات المخصصة**: السماح للمستخدمين بتحديد أنواع الإشعارات المفضلة
2. 📧 **البريد الإلكتروني**: إرسال نسخة بريدية من الإشعارات المهمة
3. 🔔 **Push Notifications**: إرسال إشعارات فورية عند حدوث أحداث
4. 👥 **الإشعارات الجماعية**: إرسال إشعارات متعددة دفعة واحدة
5. 📊 **التحليلات**: تحليل أنواع الإشعارات الأكثر فتحاً

### تحسينات الأداء:
1. ♻️ **التخزين المؤقت**: تخزين الإشعارات محلياً على الهاتف
2. 🔄 **المزامنة الدورية**: تحديث الإشعارات في الخلفية
3. 🗑️ **تنظيف الإشعارات القديمة**: حذف الإشعارات بعد 30 يوماً

---

## 📝 الملاحظات

### النقاط المهمة:
1. **معرف التليجرام**: يجب تمرير معرف التليجرام الصحيح (بدون "-")
2. **نوع الإشعار**: استخدم نفس الأنواع في التطبيق والـ API
3. **التاريخ والوقت**: يتم الحفظ بصيغة ISO 8601
4. **بيانات JSON**: يمكن تمرير بيانات إضافية في حقل `data`

### أفضل الممارسات:
1. ✅ احفظ إشعار فور حدوث الحدث
2. ✅ استخدم عناوين واضحة وموجزة
3. ✅ اجعل الرسالة بسيطة وفهمية
4. ✅ أضف معلومات مفيدة (أسماء المنتجات، المبالغ، وقت الحدث)
5. ✅ استخدم أيقونات emoji لجعل الإشعار أكثر جاذبية

---

## 🐛 استكشاف الأخطاء

### المشكلة: لا تظهر الإشعارات في التطبيق

**الحل:**
1. تحقق من أن معرف التليجرام صحيح
2. تحقق من أن API يعمل: `http://localhost:5000/api/health`
3. افحص سجلات bot.py بحثاً عن أخطاء
4. تأكد من أن قاعدة البيانات تحتوي على الإشعارات

### المشكلة: خطأ "customer_id is required"

**الحل:**
- تأكد من تمرير `customer_id` في query parameters
- استخدم الصيغة الصحيحة: `/api/notifications?customer_id=123456789`

### المشكلة: فشل الاتصال بـ API

**الحل:**
1. تحقق من أن Flask يعمل
2. تحقق من رقم المنفذ (5000 افتراضياً)
3. تحقق من متغيرات البيئة `API_PORT`
4. تحقق من جدار الحماية

---

## 📞 الدعم

لأي مشاكل أو استفسارات، تحقق من:
- `bot.py`: الدوال والـ API
- `lib/services/notification_service.dart`: الخدمة
- `lib/screens/notifications_screen.dart`: الشاشة
- قاعدة البيانات: الجدول والفهارس

**آخر تحديث:** 2024
**الحالة:** ✅ جاهز للإنتاج
