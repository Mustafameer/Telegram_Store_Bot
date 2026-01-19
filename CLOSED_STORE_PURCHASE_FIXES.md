# شراء الصور من المتجر المغلق - الإصلاحات والتحسينات

## المشاكل التي تم حلها

### 1. ✅ حذف جميع الصور بدلاً من الكمية المطلوبة فقط

**المشكلة السابقة:**
```python
# حذف جميع صور المنتج (خاطئ)
DELETE FROM imagestorage WHERE productid = ?
```

**الحل:**
```python
def delete_product_images_for_closed_store(seller_id, items_list):
    # items_list: [(product_id, quantity, price, name), ...]
    
    for product_id, quantity, price, name in items_list:
        # جرّب أول N صورة فقط (حيث N = الكمية المشتراة)
        images_to_delete = images[:quantity]
        
        # حذف فقط الصور المطلوبة
        for image_id in images_to_delete:
            cursor.execute('DELETE FROM imagestorage WHERE imageid = ?', (image_id,))
```

**النتيجة:**
- إذا اشترى العميل 2 صورة من منتج يحتوي على 5 صور → يتم حذف صورتين فقط
- الصور المتبقية (3 صور) تبقى في النظام

---

### 2. ✅ إرسال الصور مباشرة للعميل عند الشراء

**التحسين:**
```python
# قبل: إرسال صورة واحدة فقط
SELECT FileName FROM imagestorage LIMIT 1

# بعد: إرسال جميع الصور المشتراة مباشرة
SELECT filename FROM imagestorage 
WHERE productid = %s 
LIMIT %s  -- العدد المطلوب = الكمية المشتراة
```

**العملية:**
1. العميل يشتري 3 صور من منتج
2. البوت يرسل 3 صور مباشرة في الفور
3. كل صورة مع caption توضيحية:
   ```
   📦 اسم المنتج
   💰 السعر: XX د.ع
   📊 الكمية: 3
   ✅ تم شراؤها بنجاح!
   ```

---

### 3. ⏳ رسالة التطبيق (في الانتظار)

**الحالة الحالية:**
- ✅ رسالة للمشتري (Telegram)
- ✅ رسالة للبائع (Telegram)
- ❌ رسالة للتطبيق (لم تُطبق بعد)

**الحل المقترح:**
للإرسال لـ Flutter app، نحتاج إلى:
1. **إنشاء جدول Notifications** في قاعدة البيانات
2. **تخزين الإشعار** عند الشراء
3. **التطبيق يطلب الإشعارات** بشكل دوري

```sql
CREATE TABLE Notifications (
    NotificationID SERIAL PRIMARY KEY,
    CustomerID INT,
    SellerID INT,
    Type VARCHAR(50),      -- 'order_confirmed', 'product_received', etc
    Message TEXT,
    IsRead BOOLEAN DEFAULT FALSE,
    CreatedAt TIMESTAMP DEFAULT NOW()
);
```

---

## التغييرات في bot.py

### دالة `delete_product_images_for_closed_store()`
- **قبل:** تقبل `product_ids` وتحذف جميع الصور
- **بعد:** تقبل `items_list` وتحذف بناءً على الكمية المشتراة

### دالة `create_confirmed_order_for_closed_store()`
- **إرسال الصور:** الآن يرسل جميع الصور المشتراة مباشرة (وليس صورة واحدة)
- **حذف الصور:** يحذف فقط الصور المشتراة (بناءً على quantity)
- **الرسائل:** كما هي (للمشتري والبائع والتطبيق قيد الانتظار)

---

## الاختبار

### Scenario 1: شراء 2 صورة من منتج به 5 صور
```
قبل الشراء:   5 صور في المنتج
بعد الشراء:   3 صور في المنتج (تم حذف 2)
للمشتري:      2 صورة مرسلة مباشرة
```

### Scenario 2: شراء 3 صور من منتج به 3 صور
```
قبل الشراء:   3 صور
بعد الشراء:   0 صور (المنتج خالي الآن)
للمشتري:      3 صور مرسلة مباشرة
```

---

## الخطوات التالية

### للإصلاح الكامل (رسالة التطبيق):
1. إنشاء جدول `Notifications`
2. إضافة حفظ الإشعار في `create_confirmed_order_for_closed_store()`
3. إضافة API في Bot لـ Flutter:
   ```python
   @bot.message_handler(commands=['get_notifications'])
   def get_notifications(message):
       # Flutter app يطلب الإشعارات
       # Bot يرجع JSON بالإشعارات الجديدة
   ```
4. تحديث Flutter app لعرض الإشعارات من API

---

## الملخص

| المشكلة | الحالة | الحل |
|--------|--------|-----|
| حذف جميع الصور | ✅ تم الحل | حذف فقط الكمية المطلوبة |
| إرسال صورة واحدة | ✅ تم الحل | إرسال جميع الصور المشتراة |
| رسالة التطبيق | ⏳ قيد الانتظار | يحتاج API و Notifications table |

