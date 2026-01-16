# 💻 شرح الكود المضاف - نظام TELEBOT

## 📍 الموقع في bot.py

### 1. دالة `send_telebot_catalog()` - سطر ~7644

```python
def send_telebot_catalog(chat_id, customer_telegram_id=None):
    """
    إرسال كتالوج متجر TELEBOT - يعرض منتجات المتاجر المغلقة فقط
    """
```

#### الخطوة 1: التحقق من تسجيل الزبون
```python
if customer_telegram_id:
    user = get_user(customer_telegram_id)
    if not user:
        add_user(customer_telegram_id, None, 'buyer', None, None)
```
- تأكد من أن الزبون مسجل في جدول Users
- إضافته تلقائياً إذا لم يكن موجوداً

#### الخطوة 2: جلب منتجات المتاجر المغلقة
```python
if IS_POSTGRES:
    query = """
        SELECT DISTINCT p.ProductID, p.SellerID, p.CategoryID, p.Name, 
               p.Description, p.Price, p.WholesalePrice, p.Quantity, 
               p.ImagePath, p.Status, s.StoreName, s.UserName
        FROM Products p
        JOIN Sellers s ON p.SellerID = s.SellerID
        WHERE s.RequireCustomerRegistration = 1 
          AND s.Status = 'active' 
          AND p.Status = 'active'
        ORDER BY s.StoreName, p.ProductID
    """
```

**ملاحظات الاستعلام**:
- `WHERE s.RequireCustomerRegistration = 1` - يجلب فقط المتاجر المقفولة
- `AND s.Status = 'active'` - يجلب فقط المتاجر النشطة
- `AND p.Status = 'active'` - يجلب فقط المنتجات النشطة
- `ORDER BY s.StoreName, p.ProductID` - ترتيب حسب اسم المتجر ثم المنتج

#### الخطوة 3: تجميع المنتجات حسب المتجر
```python
products_by_store = {}
for product in products:
    seller_id = product[1]
    store_name = product[10]
    
    if seller_id not in products_by_store:
        products_by_store[seller_id] = {'store_name': store_name, 'products': []}
    
    products_by_store[seller_id]['products'].append(product)
```

**الغرض**:
- تجميع المنتجات تحت كل متجر
- مثال:
  ```
  {
    5: {
      'store_name': 'ملابس رجالية',
      'products': [product1, product2, ...]
    },
    8: {
      'store_name': 'حذاء',
      'products': [product1, product2, ...]
    }
  }
  ```

#### الخطوة 4: إرسال المنتجات
```python
for product in store_products:
    product_id, seller_id, category_id, name, description, price, \
    wholesale_price, quantity, image_path, status, store_name, username = product
    
    text = f"📦 **{name}**\n"
    if description:
        text += f"📝 {description}\n"
    text += f"💰 السعر: {price:,.0f} IQD\n"
    text += f"📦 الكمية المتاحة: {quantity}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("➕ إضافة للسلة", 
                                  callback_data=f"add_to_cart_{product_id}_1"),
        types.InlineKeyboardButton("🛒 السلة", 
                                  callback_data="open_cart_inline")
    )
    
    # إرسال الصورة أو رسالة عادية
    if image_path:
        try:
            image_data = get_image_from_cloud(image_path)
            if image_data:
                bot.send_photo(chat_id, image_data, caption=text, 
                              reply_markup=markup, parse_mode='Markdown')
```

**التفاصيل**:
- صيغة بطاقة المنتج تتضمن:
  - اسم المنتج (عريض)
  - الوصف (إن وُجد)
  - السعر (مع فاصلة آلاف)
  - الكمية المتاحة
- أزرار الإجراء:
  - "➕ إضافة للسلة" - لإضافة منتج واحد
  - "🛒 السلة" - لفتح السلة

---

### 2. تعديل دالة `send_store_catalog_by_telegram_id()` - سطر ~7766

```python
def send_store_catalog_by_telegram_id(chat_id, seller_telegram_id, customer_telegram_id=None):
    """إرسال كتالوج المتجر - يتطلب تسجيل الزبون في CreditCustomers إذا كان الإعداد مفعلاً"""
    
    # معالجة خاصة لمتجر TELEBOT
    if seller_telegram_id == 999999999:  # TelegramID لـ TELEBOT
        print(f"🔍 متجر TELEBOT - عرض المتاجر المغلقة")
        send_telebot_catalog(chat_id, customer_telegram_id)
        return
```

**كيفية عمل الفحص**:
1. يتحقق من أن `seller_telegram_id == 999999999`
2. إذا كان صحيح، استدعاء `send_telebot_catalog()` وإنهاء الدالة
3. إذا لم يكن صحيح، متابعة الكود العادي (للمتاجر الأخرى)

---

## 🔄 تدفق البيانات

```
المستخدم يختار TELEBOT
    ↓
handle_view_store() يتم استدعاؤها
    ↓
send_store_catalog_by_telegram_id(chat_id, 999999999, customer_id)
    ↓
يتحقق: هل seller_telegram_id == 999999999؟
    ├─ نعم → send_telebot_catalog() ← إعادة التوجيه
    │         ↓
    │         جلب منتجات المتاجر المقفولة
    │         ↓
    │         عرض كل منتج مع صورة واحدة
    │
    └─ لا → متابعة الكود العادي
            (للمتاجر الأخرى غير TELEBOT)
```

---

## 📊 جدول المقارنة - قبل وبعد

| الميزة | قبل | بعد |
|--------|-----|-----|
| **عرض المتاجر المقفولة** | ❌ مختلطة مع الأخرى | ✅ منفصلة في TELEBOT |
| **متجر خاص للمقفولة** | ❌ غير موجود | ✅ TELEBOT موجود |
| **دالة متخصصة** | ❌ واحدة عامة | ✅ متخصصة لكل نوع |
| **تنظيم المنتجات** | ❌ بدون تجميع | ✅ مجمعة حسب المتجر |

---

## 🎯 أمثلة على الاستخدام

### مثال 1: عرض TELEBOT
```python
# عند اختيار المتجر:
send_store_catalog_by_telegram_id(
    chat_id=123456,
    seller_telegram_id=999999999,  # TELEBOT
    customer_telegram_id=987654
)

# ← تدخل الدالة
# ← تكتشف أن seller_telegram_id == 999999999
# ← تستدعي send_telebot_catalog()
# ← تعرض منتجات المتاجر المقفولة
```

### مثال 2: عرض متجر عادي
```python
# عند اختيار متجر عادي:
send_store_catalog_by_telegram_id(
    chat_id=123456,
    seller_telegram_id=123456789,  # متجر عادي
    customer_telegram_id=987654
)

# ← تدخل الدالة
# ← تكتشف أن seller_telegram_id ≠ 999999999
# ← تتابع الكود العادي (كما هو الحال قبل التعديل)
# ← تعرض منتجات المتجر بشكل عادي
```

---

## 🔐 الأمان والتحقق

### 1. التحقق من TelegramID الفريد
```python
if seller_telegram_id == 999999999:  # معرف فريد وآمن
```

### 2. التحقق من حالة المتجر
```python
WHERE s.Status = 'active'  # فقط المتاجر النشطة
AND s.RequireCustomerRegistration = 1  # فقط المقفولة
```

### 3. التحقق من حالة المنتج
```python
AND p.Status = 'active'  # فقط المنتجات النشطة
```

### 4. التحقق من الزبون
```python
if customer_telegram_id:
    user = get_user(customer_telegram_id)
    if not user:
        add_user(customer_telegram_id, ...)
```

---

## ⚡ الأداء والكفاءة

### استعلام محسّن:
```sql
WHERE s.RequireCustomerRegistration = 1 
  AND s.Status = 'active' 
  AND p.Status = 'active'
ORDER BY s.StoreName, p.ProductID
```

**المميزات**:
- استخدام `DISTINCT` لتجنب المنتجات المكررة
- ترتيب مسبق في قاعدة البيانات بدلاً من البرنامج
- فلترة في قاعدة البيانات (أسرع من البرنامج)

---

## 📝 الملاحظات التقنية

### 1. استخدام `IS_POSTGRES`
```python
if IS_POSTGRES:
    cursor_wrapper.execute(query_postgres)
else:
    cursor_wrapper.execute(query_sqlite)
```
- يدعم كلاً من PostgreSQL و SQLite
- بناء على متغير بيئة `DATABASE_URL`

### 2. استخدام `get_image_from_cloud()`
```python
image_data = get_image_from_cloud(image_path)
if image_data:
    bot.send_photo(chat_id, image_data, ...)
```
- جلب الصور من `ImageStorage` (السحابة)
- دعم Railway PostgreSQL مباشرة

### 3. معالجة الأخطاء
```python
try:
    image_data = get_image_from_cloud(image_path)
    if image_data:
        bot.send_photo(...)
except Exception as e:
    print(f"⚠️ خطأ: {e}")
    bot.send_message(...)
```
- تعامل آمن مع الأخطاء
- رسائل خطأ واضحة للمستخدم

---

## 🧪 كيفية الاختبار

### اختبار الدالة مباشرة:
```python
# في ملف اختبار
from bot import send_telebot_catalog

# اختبر الدالة
send_telebot_catalog(chat_id=123456, customer_telegram_id=789)

# سيطبع:
# 🔍 send_telebot_catalog: عرض منتجات المتاجر المغلقة
# ... رسائل الاختبار ...
```

### اختبار التكامل:
```bash
# شغل البوت
python bot.py

# في Telegram:
# /start
# تصفح المتاجر 🛍️
# اختر TELEBOT - المتاجر المغلقة
# ✅ يجب أن تري منتجات المتاجر المقفولة
```

---

## 📌 النقاط المهمة

1. ✅ **معرف فريد**: `999999999` لمتجر TELEBOT فقط
2. ✅ **فحص سريع**: يتم الفحص في بداية الدالة
3. ✅ **لا تأثر على الآخرين**: المتاجر الأخرى تعمل كالمعتاد
4. ✅ **معالجة الأخطاء**: جميع الحالات معالجة
5. ✅ **الأداء**: استعلام محسّن وترتيب مسبق

---

**آخر تحديث**: 15 يناير 2026
**الحالة**: ✅ شرح كامل
