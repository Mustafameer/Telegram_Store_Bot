# 📦 نظام متجر TELEBOT - دليل الاستخدام

## 🎯 الهدف

تم تطوير نظام متجر **TELEBOT** لعرض منتجات **المتاجر المغلقة** (Closed Stores) بشكل منفصل عن المتاجر العادية المفتوحة.

---

## 📊 نموذج البيانات

### أنواع المتاجر:

| النوع | الخاصية | الوصف |
|------|--------|-------|
| **متجر مفتوح** | `RequireCustomerRegistration = 0` | مفتوح للجميع، بدون قيود |
| **متجر مقفول** | `RequireCustomerRegistration = 1` | مقفول للزبائن المسجلين فقط |
| **متجر TELEBOT** | `UserName = 'telebot'` | يعرض منتجات المتاجر المقفولة |

---

## 🚀 كيفية الاستخدام

### 1️⃣ التأكد من وجود متجر TELEBOT

تحقق من أن متجر TELEBOT موجود في قاعدة البيانات:

```bash
python test_telebot_system.py
```

**النتيجة المتوقعة:**
```
✅ متجر TELEBOT موجود:
   - SellerID: 27
   - StoreName: TELEBOT - المتاجر المغلقة
   - TelegramID: 999999999
   - Status: active
```

---

### 2️⃣ إنشاء متجر مقفول

لتحويل متجر عادي إلى متجر مقفول:

```sql
-- تحويل المتجر رقم 5 إلى متجر مقفول
UPDATE Sellers 
SET RequireCustomerRegistration = 1 
WHERE SellerID = 5;
```

**ملاحظة:** بعد هذا التحديث، جميع منتجات هذا المتجر ستظهر في **متجر TELEBOT**.

---

### 3️⃣ فتح متجر مقفول

لتحويل متجر مقفول إلى متجر مفتوح:

```sql
-- فتح المتجر رقم 5
UPDATE Sellers 
SET RequireCustomerRegistration = 0 
WHERE SellerID = 5;
```

---

### 4️⃣ عرض المتاجر المقفولة

```sql
-- عرض جميع المتاجر المقفولة
SELECT SellerID, StoreName, UserName 
FROM Sellers 
WHERE RequireCustomerRegistration = 1 
  AND Status = 'active'
ORDER BY StoreName;
```

---

### 5️⃣ عرض منتجات المتاجر المقفولة

```sql
-- عرض جميع منتجات المتاجر المقفولة
SELECT DISTINCT 
    p.ProductID, 
    p.Name, 
    p.Price, 
    s.StoreName
FROM Products p
JOIN Sellers s ON p.SellerID = s.SellerID
WHERE s.RequireCustomerRegistration = 1 
  AND s.Status = 'active' 
  AND p.Status = 'active'
ORDER BY s.StoreName, p.Name;
```

---

## 💻 الدوال البرمجية

### `send_telebot_catalog(chat_id, customer_telegram_id=None)`

**الموقع**: `bot.py` (سطر ~7644)

**الوظيفة الأساسية:**
```python
# معالجة خاصة لمتجر TELEBOT
if seller_telegram_id == 999999999:
    send_telebot_catalog(chat_id, customer_telegram_id)
    return
```

**ماذا تفعل:**
1. جلب جميع المنتجات من المتاجر حيث `RequireCustomerRegistration = 1`
2. تجميع المنتجات حسب اسم المتجر
3. عرض كل منتج مع صورة واحدة فقط

**المعاملات:**
- `chat_id` (int): معرف المحادثة في Telegram
- `customer_telegram_id` (int, اختياري): معرف الزبون

**المخرجات:**
- رسائل يحتوي كل منها على منتج واحد مع صورة وخيارات الشراء

---

## 🔄 مثال عملي كامل

### السيناريو:
1. لديك 3 متاجر:
   - متجر "ملابس رجالية" (SellerID = 5) - **مقفول**
   - متجر "أحذية" (SellerID = 8) - **مفتوح**
   - متجر "إكسسوارات" (SellerID = 12) - **مفتوح**

2. المستخدم يدخل البوت

### الخطوات:

**الخطوة 1: إعداد المتاجر**
```sql
-- جعل "ملابس رجالية" مقفول
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

-- التأكد من أن الآخرين مفتوحة
UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE SellerID IN (8, 12);
```

**الخطوة 2: المستخدم يرى المتاجر**
```
🛍️ المتاجر المتاحة:

1. 🏪 TELEBOT - المتاجر المغلقة
2. 🏪 أحذية
3. 🏪 إكسسوارات
```

**الخطوة 3: اختيار TELEBOT**
- يرى **فقط** منتجات "ملابس رجالية"
- كل منتج يعرض مع **صورة واحدة**
- يمكنه إضافة المنتجات للسلة بشكل عادي

**الخطوة 4: اختيار متجر مفتوح (مثل "أحذية")**
- يرى **جميع** منتجات المتجر
- كل منتج يعرض مع **صورة واحدة**
- يمكنه الشراء بدون قيود

---

## 📱 واجهة المستخدم

### عند اختيار متجر TELEBOT:

```
🏪 TELEBOT - المتاجر المغلقة
منتجات المتاجر المقفولة للزبائن المسجلين:

🏪 ملابس رجالية (5 منتجات)

📦 قميص رجالي أبيض
📝 قميص عالي الجودة 100% قطن
💰 السعر: 25,000 IQD
📦 الكمية المتاحة: 50

[➕ إضافة للسلة] [🛒 السلة]

...منتجات أخرى...
```

---

## ⚙️ الإعدادات

| الإعداد | القيمة | الوصف |
|-------|--------|-------|
| `TELEBOT TelegramID` | 999999999 | معرف فريد لمتجر TELEBOT |
| `TELEBOT SellerID` | 27 | معرف المتجر في قاعدة البيانات |
| `StoreName` | TELEBOT - المتاجر المغلقة | اسم المتجر المعروض |

---

## 🔒 الأمان

### متجر TELEBOT:
- ✅ معرف فريد وآمن (`TelegramID = 999999999`)
- ✅ لا يقبل طلبات حقيقية (للعرض فقط)
- ✅ يعرض فقط المنتجات النشطة
- ✅ يدعم صور السحابة (ImageStorage)

### المتاجر العادية:
- ✅ تعمل بشكل مستقل
- ✅ لا تتأثر بنظام TELEBOT
- ✅ تحتفظ بإعدادات RequireCustomerRegistration الخاصة بها

---

## 🧪 الاختبار

### اختبار النظام كاملاً:

```bash
# 1. اختبار قاعدة البيانات
python test_telebot_system.py

# 2. تشغيل البوت
python bot.py

# 3. اختبار التصفح
# - افتح Telegram
# - ابحث عن البوت
# - اضغط /start
# - اختر "تصفح المتاجر 🛍️"
# - يجب أن تري "TELEBOT - المتاجر المغلقة"
```

---

## 📝 قائمة التحقق

- [ ] تم إضافة متجر TELEBOT إلى قاعدة البيانات
- [ ] تم اختبار النظام باستخدام `test_telebot_system.py`
- [ ] تم تحديث `bot.py` بدالة `send_telebot_catalog()`
- [ ] تم اختبار البوت يدويًا في Telegram
- [ ] تم تحويل متجر واحد على الأقل إلى "مقفول"
- [ ] تم التأكد من ظهور TELEBOT مع المتاجر الأخرى
- [ ] تم اختبار عرض منتجات المتاجر المقفولة
- [ ] تم اختبار عملية الشراء من TELEBOT

---

## 🐛 حل المشاكل

### المشكلة: لا يظهر متجر TELEBOT

**الحل:**
```python
# تشغيل السكريبت لإعادة إضافة TELEBOT
python add_telebot_store.py

# أو تحقق يدويًا من قاعدة البيانات
SELECT * FROM Sellers WHERE UserName = 'telebot';
```

### المشكلة: لا تظهر منتجات المتاجر المقفولة

**الحل:**
```sql
-- تحقق من وجود متاجر مقفولة
SELECT COUNT(*) FROM Sellers WHERE RequireCustomerRegistration = 1;

-- إذا كان 0، حول متجر إلى مقفول:
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;
```

### المشكلة: الصور لا تظهر

**الحل:**
- تحقق من أن الصور موجودة في جدول `ImageStorage`
- تحقق من أن `image_path` صحيح في جدول Products

---

## 📞 دعم إضافي

للمزيد من المعلومات، انظر:
- `TELEBOT_CLOSED_STORES_GUIDE.md` - دليل تقني مفصل
- `bot.py` (سطر ~7644) - كود الدالة الأساسية

---

**آخر تحديث**: 15 يناير 2026
**الحالة**: ✅ جاهز للاستخدام
