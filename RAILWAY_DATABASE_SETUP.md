# 🔗 ربط قاعدة البيانات على Railway

## ✅ بيانات الاتصال الخاصة بك:

```
Host:     switchback.proxy.rlwy.net
Port:     20266
Database: railway
Username: postgres
Password: bqcTJxNXLgwOftDoarrtmjmjYWurEIEh
```

---

## 🔑 DATABASE_URL الكامل:

```
postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway
```

**انسخ هذا الرابط كاملاً**

---

## 📝 كيفية إضافته إلى Railway:

### **الخطوة 1: في Railway Dashboard**

1. اذهب: https://railway.app
2. اختر: Project
3. اضغط على المشروع

### **الخطوة 2: إضافة المتغير**

1. اذهب: **Variables** (في القائمة العلوية)
2. اضغط: **New Variable**
3. ملئ البيانات:
   ```
   الاسم:  DATABASE_URL
   القيمة: postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway
   ```
4. اضغط: **Add**

### **الخطوة 3: إضافة TELEGRAM_BOT_TOKEN**

1. اضغط: **New Variable**
2. ملئ البيانات:
   ```
   الاسم:  TELEGRAM_BOT_TOKEN
   القيمة: [رقم البوت من @BotFather]
   ```
3. اضغط: **Add**

✅ **تم: المتغيرات موجودة**

---

## 🚀 خطوات النشر:

### **إذا لم تنشر بعد:**

1. **في Railway:** اضغط "Deploy Now"
2. **انتظر:** 2-3 دقائق
3. **تحقق:** من Logs

### **إذا نشرت بالفعل:**

البوت سيعيد التشغيل تلقائياً:
```
✅ سيقرأ DATABASE_URL
✅ سيتصل بـ PostgreSQL
✅ سيبدأ البوت فوراً
```

---

## ✅ التحقق من الاتصال:

### **في Railway Logs:**

ابحث عن رسالة مثل:
```
✅ Database connected successfully
✅ Telegram bot started
```

### **أرسل رسالة للبوت:**

```
✅ إذا أجاب = كل شيء يعمل! 🎉
❌ إذا ما أجاب = تحقق من Logs
```

---

## 🔐 ملاحظات أمان:

**⚠️ الرسالة الحمراء:**

**لا تشارك هذه البيانات:**
```
❌ لا تحطها على GitHub
❌ لا تشارك الرابط
❌ لا تكتبها في Messages عام
```

**فقط:**
```
✅ في Railway Variables (آمن تماماً)
✅ في .env محلياً (خاص بك)
```

---

## 📊 الحالة الآن:

| العنصر | الحالة |
|--------|--------|
| **Host** | ✅ switchback.proxy.rlwy.net |
| **Port** | ✅ 20266 |
| **Database** | ✅ railway |
| **Username** | ✅ postgres |
| **Password** | ✅ محفوظ |
| **DATABASE_URL** | ✅ جاهز |

---

## 🎯 الخطوة التالية:

1. **أضف المتغيرات في Railway** (DATABASE_URL و TELEGRAM_BOT_TOKEN)
2. **اضغط Deploy**
3. **انتظر 2-3 دقائق**
4. **أرسل رسالة للبوت**
5. **يجب أن يرد** ✅

---

## 💡 نصيحة:

إذا واجهت مشكلة:
1. اذهب: **Logs** في Railway
2. ابحث عن رسالة الخطأ
3. ابعت الرسالة في Google
4. أصلح المشكلة
5. أعد المحاولة

---

**تم الإنشاء:** 14 يناير 2026
**الحالة:** ✅ بيانات جاهزة للنشر
**الأمان:** ✅ بيانات محفوظة
