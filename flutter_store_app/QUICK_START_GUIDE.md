# دليل سريع - Quick Reference Guide

## 🎯 الهدف
اختبار نظام الصور والتشخيص من الـ Console

## 📋 قائمة التحقق - Checklist

### قبل البدء | Before Starting:
- [ ] تأكد أن الـ app مُغلق
- [ ] تأكد من اتصالك بـ PostgreSQL (Railway)
- [ ] افتح VS Code أو الـ Terminal

### الخطوات | Steps:

#### 1️⃣ ابدأ التطبيق
```bash
cd flutter_store_app
flutter run -d windows
```

#### 2️⃣ الانتقال للمتجر
- اختر متجر من القائمة
- انتقل لـ "إدارة المنتجات"

#### 3️⃣ إضافة صور
- اختر منتج
- اضغط "معرج الصور"
- اختر صورتين من جهازك

#### 4️⃣ جمع البيانات
- انسخ كل رسائل Console
- الصقها في ملف نصي
- شارك معي

---

## 🔍 علامات النجاح - Success Indicators

| الرسالة | المعنى | الإجراء |
|---------|--------|--------|
| 📤 جاري رفع الصورة | Upload starting | ✅ OK |
| ✅ تم رفع الصورة | Upload successful | ✅ OK |
| 🔗 جاري ربط الصورة | Linking starting | ✅ OK |
| ✅ تم إضافة الصورة | Link successful | ✅ OK |
| 📸 تم العثور على [count] | Count successful | ✅ OK |
| ✅ تم تحديث الكمية | Update successful | ✅ OK |
| ⏳ جاري تحميل الصورة | Loading starting | ✅ OK |
| ✅ تم تحميل الصورة | Load successful | ✅ OK |

---

## ⚠️ علامات التحذير - Warning Signs

| الرسالة | المشكلة | الحل |
|---------|--------|------|
| ❌ Error uploading | الرفع فشل | تحقق الاتصال بـ DB |
| Image file not found | لم يُحفظ | معادة الرفع |
| لم يتم تحميل الصورة | التحميل فشل | قد تحتاج base64 |
| خطأ في عرض الصورة | البيانات سيئة | تحقق نوع البيانات |

---

## 🎬 المتوقع | Expected Flow

```
1. فتح المعرج
   ↓
2. اختيار صور
   ↓
3. رفع الصور (ImageStorage)
   ↓
4. ربط الصور (ProductImages)
   ↓
5. تحديث الكمية
   ↓
6. الإرجاع للبطاقة
   ↓
7. تحميل الصور في المعرج
   ↓
8. عرض الصور ✅
   ↓
9. تحديث الكمية في البطاقة ✅
```

---

## 💾 الملفات المهمة

### للاختبار:
- `lib/screens/manage_product_images_screen.dart` - المعرج
- `lib/services/postgres_service.dart` - العمليات
- `lib/database/database_helper_cloud.dart` - المجموعة

### للمرجع:
- `DEBUG_IMAGE_LOADING.md` - دليل تفصيلي
- `DIAGNOSTIC_UPDATE.md` - التحديثات

---

## 📞 إذا حدث خطأ

**قدّم المعلومات التالية:**

```
1. رقم المتجر:
2. اسم المنتج:
3. عدد الصور:
4. رسائل الخطأ:
5. Console Output:
```

**كمثال:**
```
متجر ID: 5
اسم المنتج: T-Shirt Blue
عدد الصور: 2
الخطأ: Image not found in ImageStorage

Console Output:
📤 جاري رفع الصورة: 1234_abc.jpg، الحجم: 45000 bytes
✅ تم رفع الصورة بنجاح: 1234_abc.jpg
🔗 جاري ربط الصورة: 1234_abc.jpg بالمنتج 5
❌ خطأ في إضافة الصورة: Image file not found in ImageStorage: 1234_abc.jpg
```

---

## ⏱️ المدة المتوقعة
- فتح التطبيق: **1-2 دقيقة**
- إضافة صورتين: **30-60 ثانية**
- جمع البيانات: **5 دقائق**

**الإجمالي: ~10 دقائق** ✅

---

**هل أنت مستعد؟ ابدأ الآن! 🚀**

