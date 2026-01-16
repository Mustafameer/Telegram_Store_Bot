# 🔧 تعديل تطبيق الديسكتوب - التلاؤم مع منطق TELEBOT

## 📋 نظرة عامة

تطبيق الديسكتوب (Flutter) بحاجة إلى تعديلات لدعم نظام TELEBOT الجديد:
1. **إضافة فئات (Categories)** للمتاجر
2. **إضافة منتجات (Products)** مع مراعاة المتاجر المقفولة
3. **تحديث واجهة المستخدم** لعرض معلومات TELEBOT

---

## 🎯 أهداف التعديل

### 1. دعم إضافة الفئات (Categories)
- ✅ التطبيق يدعمها بالفعل (في `categories_tab.dart`)
- ⚠️ **تأكد**: جميع الفئات تُضاف إلى الـ SellerID الصحيح

### 2. دعم إضافة المنتجات (Products)
- ✅ التطبيق يدعمها بالفعل (في `products_tab.dart`)
- ⚠️ **تأكد**: المنتجات تُضاف إلى الـ CategoryID الصحيح
- ⚠️ **جديد**: دعم متاجر TELEBOT (TelegramID = 999999999)

### 3. دعم متاجر TELEBOT الخاصة
- 🆕 تحديث `home_screen.dart` لعرض TELEBOT كمتجر خاص
- 🆕 تحديث `store_detail_screen.dart` للتعامل مع TELEBOT

---

## 🔄 التعديلات المطلوبة

### أ) في `home_screen.dart`:

**الهدف**: إضافة معالجة خاصة لمتجر TELEBOT

```dart
// قبل: عرض جميع المتاجر بنفس الطريقة
// بعد: تمييز TELEBOT كمتجر خاص

// في قسم عرض المتاجر:
Future<void> _loadStores() async {
  final stores = await DatabaseHelper.instance.getAllSellers();
  
  // ترتيب خاص: TELEBOT أولاً إن وُجد
  stores.sort((a, b) {
    // TELEBOT (TelegramID = 999999999) يظهر أولاً
    if (a.telegramId == 999999999) return -1;
    if (b.telegramId == 999999999) return 1;
    return a.storeName.compareTo(b.storeName);
  });
  
  setState(() {
    _stores = stores;
  });
}
```

### ب) في `store_detail_screen.dart`:

**الهدف**: معالجة خاصة لمتجر TELEBOT (عرض فقط، بدون تحرير)

```dart
// TELEBOT - متجر خاص للقراءة فقط
if (widget.seller.telegramId == 999999999) {
  // إظهار المنتجات فقط
  // إخفاء أزرار الإضافة والتعديل والحذف
  isEditable = false;
} else {
  // متجر عادي - يمكن التحرير
  isEditable = widget.seller.telegramId == currentUser?.telegramId;
}
```

### ج) في `products_tab.dart`:

**الهدف**: دعم معالجة منتجات المتاجر المقفولة

```dart
// إضافة معالجة خاصة للمنتجات المقفولة
Future<void> _loadProducts() async {
  final products = await DatabaseHelper.instance.getProducts(
    widget.sellerId,
    forceRefresh: true,
  );
  
  // إذا كان المتجر TELEBOT:
  if (widget.sellerId == 27) { // SellerID لـ TELEBOT
    // يتم جلب المنتجات من جدول المتاجر المقفولة فقط
    // (يتم هذا في قاعدة البيانات بالفعل)
    print('📦 جاري تحميل منتجات المتاجر المقفولة من TELEBOT');
  }
}
```

### د) في `categories_tab.dart`:

**الهدف**: منع إضافة فئات لـ TELEBOT

```dart
// إضافة فحص في _showCategoryDialog:
void _showCategoryDialog({Category? category}) {
  // TELEBOT لا يحتاج إلى فئات خاصة
  if (widget.sellerId == 27) { // SellerID لـ TELEBOT
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('متجر TELEBOT لا يحتاج إلى فئات')),
    );
    return;
  }
  
  // للمتاجر الأخرى - العملية العادية
  showDialog(...);
}
```

---

## 📁 الملفات التي تحتاج تعديل

| الملف | التعديل | الأولوية |
|------|---------|---------|
| `home_screen.dart` | ترتيب TELEBOT أولاً | 🔴 عالية |
| `store_detail_screen.dart` | معالجة TELEBOT كقراءة فقط | 🔴 عالية |
| `products_tab.dart` | دعم منتجات المتاجر المقفولة | 🟡 متوسطة |
| `categories_tab.dart` | منع إضافة فئات لـ TELEBOT | 🟢 منخفضة |
| `database_helper.dart` | تحديث الاستعلامات (اختياري) | 🟢 منخفضة |

---

## 🔌 التكامل مع Bot.py

### الاتصال بـ TELEBOT:

**في البوت (bot.py)**:
```python
if seller_telegram_id == 999999999:  # TELEBOT
    send_telebot_catalog()  # عرض منتجات المتاجر المقفولة
```

**في التطبيق (Flutter)**:
```dart
if (seller.telegramId == 999999999) {  // TELEBOT
  // عرض خاص للمتاجر المقفولة
  _loadClosedStoresProducts();
}
```

---

## 💾 البيانات في قاعدة البيانات

### متجر TELEBOT:
```sql
SELECT * FROM Sellers WHERE TelegramID = 999999999;

-- النتيجة:
-- SellerID: 27
-- StoreName: TELEBOT - المتاجر المغلقة
-- TelegramID: 999999999
-- Status: active
-- RequireCustomerRegistration: 0 (مفتوح للعرض)
```

### المنتجات المقفولة:
```sql
-- يتم جلب منتجات المتاجر حيث RequireCustomerRegistration = 1
SELECT p.* FROM Products p
JOIN Sellers s ON p.SellerID = s.SellerID
WHERE s.RequireCustomerRegistration = 1;
```

---

## 🚀 خطوات التطبيق

### 1. تحديث `home_screen.dart`:
```dart
// إضافة ترتيب خاص لـ TELEBOT
stores.sort((a, b) {
  if (a.telegramId == 999999999) return -1;
  if (b.telegramId == 999999999) return 1;
  return a.storeName.compareTo(b.storeName);
});
```

### 2. تحديث `store_detail_screen.dart`:
```dart
// معالجة TELEBOT كمتجر خاص
bool _isTelebot = widget.seller.telegramId == 999999999;
bool isEditable = !_isTelebot && /* شروط أخرى */;
```

### 3. تحديث `products_tab.dart`:
```dart
// معالجة منتجات TELEBOT
if (widget.sellerId == 27) {
  // يتم التعامل مع TELEBOT بشكل خاص
}
```

---

## ✨ مميزات النظام المحسّن

| الميزة | الفائدة |
|--------|--------|
| **ترتيب TELEBOT أولاً** | سهولة الوصول |
| **قراءة فقط لـ TELEBOT** | حماية البيانات |
| **دعم المتاجر المقفولة** | عرض منظم |
| **تكامل كامل مع البوت** | تجربة موحدة |

---

## 🧪 الاختبار

### اختبر المميزات الجديدة:

1. **شغل التطبيق**:
   ```bash
   flutter run
   ```

2. **اختبر ترتيب المتاجر**:
   - تحقق من أن TELEBOT يظهر أولاً

3. **اختبر منع التعديل على TELEBOT**:
   - حاول الضغط على أزرار التعديل
   - يجب أن تكون معطلة

4. **اختبر عرض المنتجات**:
   - انظر إلى منتجات المتاجر المقفولة
   - يجب أن تظهر في TELEBOT

---

## 📝 ملاحظات مهمة

1. **لا تعدل** TelegramID لـ TELEBOT (999999999)
2. **لا تحذف** متجر TELEBOT من قاعدة البيانات
3. **تأكد** من تطابق SellerID (27) بين البوت والتطبيق
4. **استخدم** نفس معرفات الجداول في البوت والتطبيق

---

## 🔗 الملفات ذات الصلة

- [TELEBOT_USAGE_GUIDE.md](../TELEBOT_USAGE_GUIDE.md) - دليل TELEBOT
- [CODE_EXPLANATION.md](../CODE_EXPLANATION.md) - شرح كود TELEBOT
- `lib/screens/home_screen.dart` - الشاشة الرئيسية
- `lib/screens/store_detail_screen.dart` - تفاصيل المتجر
- `lib/database/database_helper.dart` - مساعد قاعدة البيانات

---

**آخر تحديث**: 15 يناير 2026  
**الحالة**: 📋 دليل التعديل
