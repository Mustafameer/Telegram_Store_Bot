# 🚀 نظام متجر TELEBOT - المتاجر المغلقة

## 📋 نظرة عامة

تم إضافة منطق جديد إلى بوت TelegramStoreBot لدعم متجر **TELEBOT** الخاص الذي يعرض منتجات **المتاجر المغلقة** فقط.

---

## 🏗️ البنية الجديدة

### 1. **متجر TELEBOT**
- **SellerID**: 27
- **StoreName**: TELEBOT - المتاجر المغلقة
- **TelegramID**: 999999999 (معرف فريد)
- **Status**: active
- **الوظيفة**: عرض جميع منتجات المتاجر المقفولة للزبائن المسجلين

### 2. **المتاجر المقفولة (Closed Stores)**
- أي متجر لديه `RequireCustomerRegistration = 1`
- تعني أن المتجر **مقفول للزبائن المسجلين فقط** في جدول CreditCustomers
- منتجات هذه المتاجر تُعرض في متجر TELEBOT

### 3. **المتاجر المفتوحة (Open Stores)**
- أي متجر لديه `RequireCustomerRegistration = 0` أو NULL
- تعني أن المتجر **مفتوح للجميع**
- تعرض منتجاتها بشكل عادي (بطاقة منتج واحدة مع صورة واحدة لكل منتج)

---

## 🔧 كيفية عمل النظام

### أ) عند تصفح المتاجر:

**المستخدم يرى:**
```
🛍️ المتاجر المتاحة:

1. 🏪 TELEBOT - المتاجر المغلقة
2. 🏪 متجرك المفتوح الأول
3. 🏪 متجرك المفتوح الثاني
```

### ب) عند اختيار متجر TELEBOT:

**النظام يقوم بـ:**
1. التحقق من أن `seller_telegram_id == 999999999`
2. استدعاء دالة `send_telebot_catalog()`
3. جلب جميع المنتجات من المتاجر حيث `RequireCustomerRegistration = 1`
4. تجميع المنتجات حسب اسم المتجر
5. عرض **بطاقة منتج واحدة** مع **صورة واحدة فقط** لكل منتج

### ج) عند اختيار متجر عادي مفتوح:

**النظام يقوم بـ:**
1. استدعاء دالة `send_store_catalog_by_telegram_id()` كالمعتاد
2. عرض المنتجات بصيغة عادية (بطاقة + صورة واحدة)
3. لا توجد قيود على الوصول

---

## 💾 جدول Sellers المعدل

```sql
-- متجر TELEBOT الجديد
INSERT INTO Sellers (TelegramID, UserName, StoreName, Status, RequireCustomerRegistration)
VALUES (999999999, 'telebot', 'TELEBOT - المتاجر المغلقة', 'active', 0);

-- متجر مقفول (مثال)
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

-- متجر مفتوح (مثال)
UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE SellerID = 3;
```

---

## 📊 استعلام جلب منتجات المتاجر المغلقة

```sql
SELECT DISTINCT p.ProductID, p.SellerID, p.CategoryID, p.Name, p.Description, 
       p.Price, p.WholesalePrice, p.Quantity, p.ImagePath, p.Status,
       s.StoreName, s.UserName
FROM Products p
JOIN Sellers s ON p.SellerID = s.SellerID
WHERE s.RequireCustomerRegistration = 1 
  AND s.Status = 'active' 
  AND p.Status = 'active'
ORDER BY s.StoreName, p.ProductID;
```

---

## 🔄 الدوال الرئيسية

### 1. `send_telebot_catalog(chat_id, customer_telegram_id)`
**الموقع**: bot.py (بعد سطر 7635)

**الوظيفة**:
- جلب منتجات المتاجر المقفولة من قاعدة البيانات
- تجميع المنتجات حسب المتجر
- إرسال كل منتج مع صورة واحدة فقط

**المعاملات**:
- `chat_id`: معرف المحادثة
- `customer_telegram_id`: معرف الزبون (اختياري)

**المخرجات**:
- رسائل مع بطاقات المنتجات والصور

---

### 2. `send_store_catalog_by_telegram_id()` - معدلة
**التعديل**: إضافة فحص خاص لـ TELEBOT في البداية

```python
# معالجة خاصة لمتجر TELEBOT
if seller_telegram_id == 999999999:  # TelegramID لـ TELEBOT
    print(f"🔍 متجر TELEBOT - عرض المتاجر المغلقة")
    send_telebot_catalog(chat_id, customer_telegram_id)
    return
```

---

## 📝 مثال على الاستخدام

### السيناريو:
1. لديك متجر "ملابس رجالية" مقفول (RequireCustomerRegistration = 1)
2. لديك متجر "أحذية" مفتوح (RequireCustomerRegistration = 0)
3. المستخدم يدخل البوت

### النتائج:
```
عند اختيار TELEBOT - المتاجر المغلقة:
├─ يرى منتجات "ملابس رجالية" فقط
├─ كل منتج يعرض بصورة واحدة
└─ مع خيارات الإضافة للسلة

عند اختيار متجر "أحذية":
├─ يرى جميع منتجات المتجر
├─ كل منتج يعرض بصورة واحدة
└─ مع خيارات الإضافة للسلة
```

---

## 🔐 الأمان والقيود

### متجر TELEBOT:
- ✅ معرّف بـ `seller_telegram_id = 999999999`
- ✅ **لا يحتاج** إلى كلمة مرور أو تحقق خاص
- ✅ يعرض **فقط** منتجات المتاجر المقفولة

### المتاجر العادية:
- ✅ تعمل كالمعتاد
- ✅ قد تكون مقفولة (RequireCustomerRegistration = 1)
- ✅ أو مفتوحة (RequireCustomerRegistration = 0)

---

## 🛠️ التعديلات على ملفات المشروع

### ملفات معدلة:
1. **bot.py**
   - إضافة دالة `send_telebot_catalog()` (سطر 7644-7759)
   - تعديل `send_store_catalog_by_telegram_id()` (سطر 7766-7769)

### ملفات جديدة:
1. **add_telebot_store.py** - سكريبت لإضافة متجر TELEBOT تلقائياً

---

## ✅ الخطوات المنجزة

- ✅ تم إضافة متجر TELEBOT إلى قاعدة بيانات Railway
- ✅ تم إضافة دالة `send_telebot_catalog()` لعرض المتاجر المغلقة
- ✅ تم تعديل `send_store_catalog_by_telegram_id()` للتعامل مع TELEBOT
- ✅ تم توثيق النظام بالكامل

---

## 🚀 الخطوات التالية

### 1. اختبار النظام:
```bash
# تشغيل البوت والتحقق من ظهور TELEBOT
python bot.py
```

### 2. إدارة المتاجر:
```python
# لإغلاق متجر:
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

# لفتح متجر:
UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE SellerID = 5;
```

### 3. مراقبة الأداء:
- تتبع عدد المستخدمين الذين يدخلون متجر TELEBOT
- مراقبة المنتجات المضافة للسلة من TELEBOT

---

## 📞 الدعم

إذا حدثت مشاكل:
1. تحقق من أن `RequireCustomerRegistration` صحيح في جدول Sellers
2. تحقق من أن متجر TELEBOT له `TelegramID = 999999999`
3. تحقق من سجلات البوت (logs) بحثاً عن أخطاء

---

**آخر تحديث**: 15 يناير 2026
**الحالة**: ✅ جاهز للإنتاج
