# 🔐 كيفية السماح للزبائن المسجلين بالدخول للمتجر المقفول

## 📋 ملخص سريع

النظام يعمل على **ثلاث خطوات أساسية**:

### 1️⃣ **إغلاق المتجر (تفعيل قيد الدخول)**
- صاحب المتجر يفعّل خيار "🔒 تفعيل قيد الدخول"
- هذا يضع `RequireCustomerRegistration = 1` في قاعدة البيانات

### 2️⃣ **تسجيل الزبون (إضافة اسمه)**
- صاحب المتجر يضيف الزبون من قائمة "🏪 إدارة الزبائن الآجلين"
- الزبون يُضاف إلى جدول `CreditCustomers` مع `Telegram ID` الخاص به

### 3️⃣ **التحقق عند الدخول (البوت يتحقق)**
- عندما يحاول الزبون تصفح المتجر، البوت يتحقق:
  - هل المتجر مقفول؟ (RequireCustomerRegistration = 1)
  - هل Telegram ID الزبون مسجل عند صاحب المتجر؟

---

## 🔍 كيفية التعرف على الزبون المسجل

### الطريقة: Telegram ID

**البوت يستخدم `Telegram ID` (معرف تليجرام الفريد) للتعرف على الزبون:**

```python
# 1. عندما يأتي الزبون
customer_telegram_id = message.from_user.id  # مثال: 123456789

# 2. البوت يبحث عنه في CreditCustomers
SELECT CustomerID FROM CreditCustomers 
WHERE SellerID = seller_id AND TelegramID = customer_telegram_id

# 3. إذا وجده = مسجل ✅
# إذا لم يجده = غير مسجل ❌
```

### مثال عملي:

| رقم الخطوة | الحدث | الـ Database |
|-----------|------|------------|
| 1 | أنت (صاحب المتجر) بـ Telegram ID: **111111** تفتح قائمة الزبائن الآجلين | - |
| 2 | تضيف زبون باسم "أحمد" بـ Telegram ID: **222222** | `CreditCustomers` يحفظ: SellerID=111111, TelegramID=222222, Name="أحمد" |
| 3 | البوت يغلق المتجر (RequireCustomerRegistration = 1) | `Sellers` يحفظ: RequireCustomerRegistration=1 |
| 4 | أحمد (TelegramID: 222222) يحاول دخول المتجر | البوت يبحث: "هل التليجرام 222222 مسجل عند 111111؟" |
| 5 | البوت يجد البيانات في الصف السابق | ✅ يسمح لأحمد بالدخول |

---

## ⚙️ الكود الفعلي (bot.py)

### دالة التحقق من التسجيل:
```python
def is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id):
    """التحقق من أن Telegram ID مسجل في CreditCustomers"""
    
    cursor.execute("""
        SELECT CustomerID FROM CreditCustomers 
        WHERE SellerID=? AND TelegramID=?
    """, (seller_id, telegram_id))
    
    result = cursor.fetchone()
    return result is not None  # True إذا وجد، False إذا لم يجد
```

### الدالة الرئيسية عند فتح المتجر:
```python
def send_store_catalog_by_telegram_id(chat_id, seller_telegram_id, customer_telegram_id=None):
    
    # الخطوة 1: الحصول على معلومات صاحب المتجر
    seller = get_seller_by_telegram(seller_telegram_id)
    seller_id = seller[0]
    
    # الخطوة 2: التحقق من إعداد قيد الدخول
    require_registration = seller[9] == 1  # RequireCustomerRegistration
    
    # الخطوة 3: إذا كان قيد الدخول مفعلاً، التحقق من تسجيل الزبون
    if require_registration and customer_telegram_id != seller_telegram_id:
        if not is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id):
            # الزبون غير مسجل - رفض الدخول
            bot.send_message(chat_id, "🔒 **الدخول مقيد**\n...")
            return
    
    # الخطوة 4: الزبون مسجل أو المتجر مفتوح - عرض المنتجات
    show_products(seller_id, chat_id)
```

---

## 🚀 التدفق الكامل

```
┌─────────────────────────────────────────┐
│ الزبون يختار متجر من قائمة المتاجر      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ البوت يستدعي:                           │
│ send_store_catalog_by_telegram_id(      │
│   seller_telegram_id=...,              │
│   customer_telegram_id=...             │
│ )                                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ البوت يبحث عن معلومات صاحب المتجر       │
│ (seller_id، RequireCustomerRegistration) │
└──────────────┬──────────────────────────┘
               │
               ▼
           ┌────────────────────────────┐
           │ هل المتجر مقفول؟          │
           │ RequireCustomerRegistration │
           └────┬──────────────────┬────┘
                │                  │
        ✅ لا    │                  │    ✅ نعم
                │                  │
                ▼                  ▼
         ┌──────────────┐  ┌────────────────────────┐
         │ عرض جميع      │  │ البحث في CreditCustomers│
         │ المنتجات      │  │ عن TelegramID الزبون  │
         └──────────────┘  └────┬──────────────┬────┘
                                │              │
                        ✅ وجد    │              │    ❌ لم يجد
                                │              │
                                ▼              ▼
                        ┌──────────────┐  ┌──────────────┐
                        │ عرض المنتجات  │  │ رسالة:        │
                        └──────────────┘  │ "غير مسجل"   │
                                          └──────────────┘
```

---

## 💡 الجدول الذي يحفظ البيانات

### جدول `CreditCustomers`

| العمود | النوع | الوصف |
|--------|-------|--------|
| `CustomerID` | INT | معرف الزبون الفريد |
| `SellerID` | INT | معرف صاحب المتجر |
| `FullName` | TEXT | اسم الزبون |
| `TelegramID` | BIGINT | معرف تليجرام الزبون **← هذا هو المفتاح** |
| `CustomerType` | TEXT | نوع الزبون (CreditCustomer / RetailPoint) |
| `PhoneNumber` | TEXT | رقم الهاتف (اختياري) |
| `CreatedAt` | TIMESTAMP | تاريخ الإنشاء |

### جدول `Sellers`

| العمود | النوع | الوصف |
|--------|-------|--------|
| `SellerID` | INT | معرف البائع |
| `StoreName` | TEXT | اسم المتجر |
| ... | ... | ... |
| `RequireCustomerRegistration` | INT | 1 = مقفول، 0 = مفتوح **← المفتاح** |

---

## 🎯 خطوات العملية من البداية

### للبائع (صاحب المتجر):

1. **فتح قائمة "🏪 إدارة الزبائن الآجلين"**
   - استدعي: `/credit_customers` أو اضغط على الزر

2. **اختيار "➕ إضافة زبون جديد"**
   - تحديد النوع: زبون آجل / نقطة بيع
   - إدخال الاسم
   - ✅ تم الحفظ في جدول `CreditCustomers` مع Telegram ID الزبون

3. **إغلاق المتجر (اختياري)**
   - فتح "⚙️ إدارة المتجر"
   - اختيار "🔐 إدارة قيد الدخول"
   - تفعيل "🔒 تفعيل قيد الدخول"
   - ✅ تم وضع `RequireCustomerRegistration=1`

### للزبون:

1. **فتح "تصفح المتاجر 🛍️"**
2. **اختيار متجر البائع**
3. **البوت يتحقق:**
   - هل المتجر مقفول؟ ✅
   - هل أنا مسجل؟ ✅
4. **✅ عرض المنتجات!**

---

## ❓ الأسئلة الشائعة

### س: كيف البوت يعرف Telegram ID الزبون؟
**ج:** من `message.from_user.id` - التليجرام يرسلها تلقائياً مع كل رسالة

### س: ماذا لو غيّر الزبون حسابه؟
**ج:** التليجرام ID الجديد لن يكون مسجلاً، يجب إضافته مجدداً

### س: هل يمكن إضافة نفس الزبون مرتين؟
**ج:** نعم، لكن سيكون لديه سجلين (يمكن للبائع حذف السجل القديم)

### س: هل الزبون يعرف أنه مسجل؟
**ج:** لا، النظام صامت - الزبون فقط سيلاحظ أنه يستطيع الدخول

---

## ✅ التحقق من التسجيل

لاختبار ما إذا كان الزبون مسجلاً:

```python
# 1. خذ Telegram ID الزبون
telegram_id = 222222

# 2. اسأل: هل هذا الرقم موجود في CreditCustomers لمتجري؟
is_registered = is_customer_registered_for_store_by_telegram_id(
    telegram_id=222222,
    seller_id=111111
)

# 3. إذا كان True = مسجل ✅
# إذا كان False = غير مسجل ❌
```

---

**آخر تحديث:** January 14, 2026
