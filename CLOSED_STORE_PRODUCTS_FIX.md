# ✅ حل مشكلة "خطأ في تحميل المنتجات" للعملاء المسجلين سابقاً في المتاجر المغلقة

## 🔴 المشكلة الأصلية

عند دخول عميل مسجل سابقاً (له طلبات قديمة) في متجر مغلق وينقر على فئة، يحصل على رسالة خطأ:
```
❌ حدث خطأ في تحميل المنتجات
```

## 🔍 السبب الجذري

الدالة `is_customer_registered_for_store_by_telegram_id()` كانت تتحقق فقط من جدول `CreditCustomers`:
- تبحث عن العميل بناءً على `TelegramID` و `SellerID`
- إذا لم يكن موجود في الجدول → رفض الوصول
- **المشكلة**: العملاء القدماء قد لا يكونون في `CreditCustomers` أصلاً أو لديهم `TelegramID` مختلف

## ✅ الحل المطبق

تم إضافة دالة جديدة: `has_previous_orders_for_store()`

### 1. الدالة الجديدة (bot.py #2242)

```python
def has_previous_orders_for_store(telegram_id, seller_id):
    """التحقق من وجود طلبات سابقة للعميل من متجر معين (للمتاجر المغلقة)"""
    try:
        if not telegram_id:
            return False
        
```python
def has_previous_orders_for_store(telegram_id, seller_id):
    """التحقق من وجود طلبات سابقة للعميل من متجر معين (للمتاجر المغلقة)"""
    try:
        if not telegram_id:
            return False
        
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        # البحث عن أي طلبات سابقة مؤكدة للعميل من هذا البائع
        # البحث في جدول Orders حيث BuyerID = TelegramID للمشتري
        cursor_wrapper.execute("""
            SELECT OrderID FROM Orders 
            WHERE BuyerID=? AND SellerID=? AND Status IN ('confirmed', 'delivered', 'completed')
            LIMIT 1
        """, (telegram_id, seller_id))
        
        result = cursor_wrapper.fetchone()
        cursor_wrapper.close()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من الطلبات السابقة: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### 2. التعديل في دالة `handle_view_category()` (bot.py #9265)

تم تعديل منطق التحقق من التسجيل:

**قبل:**
```python
if requires_registration:
    # تحقق فقط من CreditCustomers
    is_registered = is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id)
    if not is_registered:
        # رفض الوصول
```

**بعد:**
```python
if requires_registration:
    # أولاً: تحقق من CreditCustomers
    is_registered = is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id)
    
    # إذا لم يكن مسجلاً في CreditCustomers، تحقق من الطلبات السابقة
    if not is_registered:
        has_previous = has_previous_orders_for_store(customer_telegram_id, seller_id)
        if has_previous:
            is_registered = True  # السماح برؤية المنتجات
```

## 🔄 سير العملية الآن

```
العميل ينقر على فئة
    ↓
هل المتجر مغلق؟
    ├─ نعم → تحقق من التسجيل:
    │         ├─ هل موجود في CreditCustomers؟
    │         │   ├─ نعم → عرض المنتجات
    │         │   └─ لا → تحقق من الطلبات السابقة
    │         │           ├─ نعم → عرض المنتجات ✅ (الحل الجديد)
    │         │           └─ لا → عرض رسالة رفض
    │         └─ أي خطأ → رفض الوصول
    └─ لا → عرض المنتجات مباشرة
```

## 📊 الحالات المدعومة الآن

| الحالة | CreditCustomers | طلبات سابقة | النتيجة |
|--------|-----------------|-----------|---------|
| عميل جديد تماماً | ❌ | ❌ | ❌ رفض |
| عميل قديم مع تسجيل | ✅ | - | ✅ سماح |
| عميل قديم بدون تسجيل | ❌ | ✅ | ✅ سماح (الحل الجديد) |
| صاحب المتجر | - | - | ✅ سماح دائماً |

## 🧪 الاختبار

قم بتشغيل:
```bash
python test_closed_store_fix.py
```

## 📝 الملفات المعدلة

- **bot.py**:
  - إضافة دالة `has_previous_orders_for_store()` (السطر 2242)
  - تعديل منطق التحقق في `handle_view_category()` (السطر 9265)

## ⚠️ ملاحظات مهمة

1. **قاعدة البيانات**: الحل يعتمد على وجود جدول `Orders` مع عمود `BuyerID` (Telegram ID للمشتري) و `SellerID` و `Status`
2. **الأداء**: البحث محدود بـ `LIMIT 1` لتحسين الأداء
3. **الحالات المدعومة**: يبحث عن طلبات بالحالات التالية فقط:
   - `confirmed` (مؤكد)
   - `delivered` (مسلم)
   - `completed` (مكتمل)

4. **الأمان**: الحل يحافظ على أمان النظام:
   - العملاء الجدد لا يمكنهم الوصول
   - فقط من لهم طلبات سابقة يمكنهم رؤية المنتجات

## 🎯 النتيجة النهائية

✅ العملاء المسجلين سابقاً الآن يمكنهم:
- دخول المتاجر المغلقة بدون رسالة خطأ
- رؤية فئات المنتجات
- تصفح المنتجات وإضافتها للسلة
- إكمال عملية الشراء

---
**آخر تحديث**: 2026-01-17
