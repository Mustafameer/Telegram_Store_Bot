# ✅ حل مشكلة "خطأ في تحميل المنتجات" بعد حذف جدول ProductImages

## 🔴 المشكلة الأصلية

بعد حذف جدول `productimages` وتحسين جدول `imagestorage`:
- الزبون يدخل المتجر المغلق ويضغط على فئة
- يحصل على رسالة خطأ: **"❌ حدث خطأ في تحميل المنتجات"**

## 🔍 السبب الجذري

الكود كان يحاول البحث في جدول `productimages`/`ProductImages` الذي تم حذفه في عدة أماكن:

1. **عند جلب المنتجات بعد الشراء** (السطر 3263-3275)
   - محاولة الحذف من جدول غير موجود

2. **عند الشراء بدون تسجيل** (السطر 11191-11210)
   - نفس المشكلة

3. **عند حذف الصور يدويا** (السطر 6711-6727 و 6771-6784)
   - محاولة الحذف من جدول غير موجود

## ✅ الحل المطبق

تم استبدال جميع استعلامات البحث والحذف من جدول `productimages` ليبحثوا في `imagestorage` بدلاً من ذلك.

### التعديلات:

#### 1️⃣ في دالة معالجة الشراء (حول السطر 3263)

**قبل:**
```python
if IS_POSTGRES:
    cursor_wrapper.execute("""
        SELECT imagepath FROM productimages WHERE productid=%s
    """, (pid,))
else:
    cursor_wrapper.execute("""
        SELECT ImagePath FROM ProductImages WHERE ProductID=?
    """, (pid,))

image_paths = cursor_wrapper.fetchall()
for (img_path,) in image_paths:
    if img_path:
        filename = os.path.basename(img_path)
        # حذف من ImageStorage
```

**بعد:**
```python
if IS_POSTGRES:
    cursor_wrapper.execute("""
        SELECT filename FROM imagestorage WHERE productid=%s
    """, (pid,))
else:
    cursor_wrapper.execute("""
        SELECT FileName FROM imagestorage WHERE ProductID=?
    """, (pid,))

image_paths = cursor_wrapper.fetchall()
for (filename,) in image_paths:
    if filename:
        # حذف من ImageStorage مباشرة
```

#### 2️⃣ في دالة الشراء بدون تسجيل (حول السطر 11191)

نفس التعديل - استبدال جدول `productimages` بـ `imagestorage`

#### 3️⃣ في دوال حذف الصور اليدوية (السطر 6711 و 6771)

تم تعديل استعلامات الحذف:
- من: `DELETE FROM productimages WHERE productid=...`
- إلى: `DELETE FROM imagestorage WHERE productid=...`

## 📊 النتيجة

✅ **الآن:**
- جميع الاستعلامات تبحث في `imagestorage` (الجدول الجديد)
- لا توجد محاولات للبحث في جدول محذوف
- الزبون يمكنه دخول المتجر وتصفح وشراء المنتجات بدون أخطاء

## 🧪 الاختبار

قم بتشغيل:
```bash
python test_product_loading_fix.py
```

أو اختبر يدويا:
1. ادخل متجر مغلق
2. اضغط على فئة
3. يجب أن تظهر المنتجات بنجاح

## 📝 الملفات المعدلة

- **bot.py**:
  - السطر 3263-3280: تصحيح استعلام جلب الصور بعد الشراء
  - السطر 6711-6727: تصحيح حذف الصورة الحالية
  - السطر 6771-6784: تصحيح حذف الصور القديمة
  - السطر 11191-11210: تصحيح استعلام الشراء بدون تسجيل

## ⚠️ ملاحظات مهمة

1. **جدول imagestorage**: يحتوي على:
   - `ImageID` (معرّف فريد)
   - `ProductID` (معرّف المنتج)
   - `FileName` (اسم الملف)
   - `ImageOrder` (ترتيب الصورة)

2. **لا توجد مرجعية مباشرة للمسار** - نستخدم اسم الملف فقط الآن

3. **الأداء محسّن** - لا توجد محاولات التحويل من المسار الكامل إلى اسم الملف

## 🎯 الخطوات التالية

إذا كانت هناك مشاكل أخرى:
1. تحقق من سجلات البوت للأخطاء
2. تأكد من أن جدول `imagestorage` يحتوي على البيانات الصحيحة
3. قم بتشغيل `test_product_loading_fix.py` للتشخيص

---
**آخر تحديث**: 2026-01-17
