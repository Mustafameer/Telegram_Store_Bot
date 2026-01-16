# ⚡ مرجع سريع - نظام TELEBOT

## 🎯 ماهو TELEBOT؟
نظام موحد يجمع منتجات جميع المتاجر المقفولة في واجهة واحدة.

---

## 🔑 المعرفات الحاسمة

| المعرف | القيمة |
|------|-------|
| **TelegramID** | `999999999` |
| **SellerID** | `27` |
| **StoreName** | `TELEBOT - المتاجر المغلقة` |

---

## 📂 الملفات المعدلة

### 1. **bot.py**
- السطور 7644-7759: دالة `send_telebot_catalog()`
- السطور 7766-7769: توجيه TELEBOT

### 2. **home_screen.dart**
- تصنيف: TELEBOT يظهر أولاً

### 3. **store_detail_screen.dart**
- إخفاء أزرار التعديل والقفل من TELEBOT
- منع Dialog التعديل

### 4. **categories_tab.dart**
- منع إضافة الفئات (SellerID == 27)

### 5. **products_tab.dart**
- منع إضافة/تعديل/حذف المنتجات (SellerID == 27)

---

## ✅ الفحوصات الأساسية

```dart
// التحقق من TELEBOT (في Bot)
if (seller_telegram_id == 999999999):
    send_telebot_catalog()

// التحقق من TELEBOT (في Flutter)
if (widget.seller.telegramId == 999999999):
    // إخفاء/منع التعديل

if (widget.sellerId == 27):
    // منع العمليات على الفئات والمنتجات
```

---

## 🔒 الحماية

### المستوى 1: إخفاء الواجهة
```dart
if (widget.isSellerMode && widget.seller.telegramId != 999999999)
  IconButton(...)
```

### المستوى 2: حماية Dialog
```dart
if (widget.seller.telegramId == 999999999) {
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('⛔ متجر TELEBOT لا يمكن تعديله'))
  );
  return;
}
```

### المستوى 3: منع العمليات
```dart
if (widget.sellerId == 27) {
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('🔒 متجر TELEBOT محجوز'))
  );
  return;
}
```

---

## 🧪 اختبار سريع

```bash
# 1. نظف وشغّل
flutter clean
flutter pub get
flutter run

# 2. افتح التطبيق وتحقق من:
- TELEBOT يظهر أولاً ✅
- لا توجد أزرار تعديل على TELEBOT ✅
- لا يمكن إضافة فئات ✅
- لا يمكن تعديل منتجات ✅
```

---

## 📊 حالة الترتيب

### TELEBOT:
```
من: MetaData
المعايير: TelegramID == 999999999
النتيجة: يظهر أولاً (return -1)
```

### باقي المتاجر:
```
المعايير: alphabetical sort
النتيجة: مرتبة أبجدياً بعد TELEBOT
```

---

## 🎨 رسائل المستخدم

| السياق | الرسالة |
|-------|--------|
| محاولة تعديل TELEBOT | ⛔ متجر TELEBOT لا يمكن تعديله |
| إضافة فئة | 🔒 متجر TELEBOT محجوز ولا يحتاج إلى فئات |
| تعديل منتج | 🔒 متجر TELEBOT محجوز - لا يمكن تعديل المنتجات |
| حذف منتج | 🔒 متجر TELEBOT محجوز - لا يمكن حذف المنتجات |

---

## 🚀 خطوات النشر

1. ✅ تأكد من عدم وجود أخطاء: `flutter analyze`
2. ✅ اختبر التطبيق: `flutter run`
3. ✅ تحقق من جميع الحالات الثلاث:
   - TELEBOT (محجوز)
   - متجر مقفول (مقفول)
   - متجر مفتوح (مفتوح)
4. ✅ أطلقه للإنتاج

---

## 📞 استكشاف الأخطاء

| المشكلة | الحل |
|-------|------|
| TELEBOT لا يظهر أولاً | تحقق من `_refreshSellers()` في `home_screen.dart` |
| أزرار التعديل تظهر | تحقق من الشرط في الـ `if` بالسطر 320+ من `store_detail_screen.dart` |
| يمكن تعديل TELEBOT | تحقق من الحماية في `_showEditStoreDialog()` |
| يمكن إضافة فئات | تحقق من الحماية في `_showCategoryDialog()` |
| يمكن تعديل منتجات | تحقق من الحماية في `_showProductForm()` و `_deleteProduct()` |

---

## 💾 معلومات قاعدة البيانات

### جدول Sellers:
```sql
SELECT * FROM Sellers WHERE TelegramID = 999999999;
-- ستجد: SellerID = 27, StoreName = 'TELEBOT - المتاجر المغلقة'
```

### المنتجات:
```sql
SELECT p.*, s.StoreName 
FROM Products p
JOIN Sellers s ON p.SellerId = s.SellerId
WHERE s.RequireCustomerRegistration = 1;
-- هذه المنتجات تظهر في TELEBOT
```

---

## 🎯 ملخص الحالات

| الحالة | المتجر | الظهور | التعديل |
|-------|-------|---------|---------|
| **TELEBOT** | SellerID=27 | أولاً | ❌ محجوز |
| **مقفول** | RequireCustomerRegistration=1 | عادي | ✅ متاح (لصاحبه) |
| **مفتوح** | RequireCustomerRegistration=0 | عادي | ✅ متاح (لصاحبه) |

---

## 📝 التحقق السريع

```dart
// للتحقق من أن TELEBOT يعمل:

// 1. في home_screen.dart:
// تحقق من وجود: if (a.telegramId == 999999999) return -1;

// 2. في store_detail_screen.dart:
// تحقق من وجود: if (widget.seller.telegramId == 999999999)

// 3. في categories_tab.dart:
// تحقق من وجود: if (widget.sellerId == 27)

// 4. في products_tab.dart:
// تحقق من وجود: if (widget.sellerId == 27)
```

---

## 🎉 النتيجة

نظام TELEBOT كامل وآمن وجاهز للاستخدام! ✅

---

**مرجع سريع**: استخدم هذا الملف للعودة السريعة للمعلومات الأساسية.

