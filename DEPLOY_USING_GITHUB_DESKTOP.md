# 🚀 نشر البوت على Railway - خطوات سهلة

## ✅ ما تحتاجه الآن:

### 1️⃣ حساب GitHub
- اذهب: https://github.com
- Sign Up (أو Sign In إذا عندك حساب)

### 2️⃣ حساب Railway  
- اذهب: https://railway.app
- Sign Up (اختر GitHub)

### 3️⃣ GitHub Desktop (أسهل من Command Line)
- اذهب: https://desktop.github.com
- حمّل وثبّت

---

## 📋 الخطوات (خطوة واحدة تلو الأخرى):

### **الخطوة 1: إنشاء Repository على GitHub**

1. اذهب: https://github.com/new
2. ملئ البيانات:
   ```
   Repository name: TelegramStoreBot
   Description: Telegram Store Bot
   Public: ✓ (اختر)
   ```
3. اضغط: "Create repository"

**النتيجة:** سيعطيك رابط مثل:
```
https://github.com/YOUR_USERNAME/TelegramStoreBot
```

---

### **الخطوة 2: تحميل ملفاتك باستخدام GitHub Desktop**

1. **حمّل وثبّت:** https://desktop.github.com

2. **افتح GitHub Desktop**

3. **انقر:** "Clone a repository from the Internet"

4. **في الـ URL:**
   ```
   https://github.com/YOUR_USERNAME/TelegramStoreBot
   ```

5. **في "Local Path":**
   ```
   C:\Users\Hp\Desktop\TelegramStoreBot
   ```

6. **اضغط:** "Clone"

7. **انقر:** "This is my own repository"

8. **الآن سحب ملفاتك:**
   - انسخ جميع ملفات المشروع
   - ألصقها في المجلد المُنسخ
   - (يمكنك استبدال الملفات)

9. **في GitHub Desktop:**
   - سيظهر لك: "Changes" مع الملفات الجديدة
   - اكتب رسالة: "Initial commit"
   - اضغط: "Commit to main"

10. **اضغط:** "Push origin"
    - سيرفع ملفاتك على GitHub

✅ **تم: ملفاتك على GitHub**

---

### **الخطوة 3: نشر على Railway**

1. **اذهب:** https://railway.app

2. **اضغط:** "Start Free"

3. **اختر:** "GitHub"

4. **اسمح لـ Railway** بالوصول لـ GitHub

5. **في Dashboard:**
   - اضغط: "New Project"
   - اختر: "Deploy from GitHub"

6. **اختر Repository:**
   - ابحث عن: `TelegramStoreBot`
   - اضغط عليه

7. **اضغط:** "Deploy Now" أو "Create"

8. **انتظر:** 2-3 دقائق للتثبيت

✅ **تم: البوت مرفوع**

---

### **الخطوة 4: إضافة المتغيرات المهمة**

**في Railway Dashboard:**

1. **اضغط على المشروع**

2. **اذهب:** "Variables" (في القائمة العلوية)

3. **أضف متغيرات جديدة:**

   ```
   متغير 1:
   الاسم: TELEGRAM_BOT_TOKEN
   القيمة: [رقم بوتك من @BotFather]
   ```

   ```
   متغير 2:
   الاسم: DATABASE_URL
   القيمة: [سيتم إنشاؤه تلقائياً]
   ```

4. **للـ DATABASE_URL:**
   - إذا لم تجده، اضغط: "Add Service"
   - اختر: "PostgreSQL"
   - سيتم إنشاء URL تلقائياً

✅ **تم: البيانات موجودة**

---

### **الخطوة 5: التحقق**

1. **في Railway Dashboard:**
   - اذهب: "Logs"
   - ابحث عن:
     ```
     Telegram bot started
     ```

2. **أرسل رسالة للبوت من Telegram**

3. **يجب أن يرد فوراً** ✅

---

## 🎉 تم!

البوت الآن:
- ✅ يعمل 24/7
- ✅ متاح من الموبايل دائماً
- ✅ لا حاجة لحاسوب يعمل
- ✅ مجاني تماماً

---

## 🔄 تحديث البوت (عند عمل تغييرات):

في GitHub Desktop:
```
1. عدّل ملفاتك محلياً
2. GitHub Desktop: "Changes"
3. اكتب رسالة: "Updated features"
4. "Commit to main"
5. "Push origin"
6. Railway تحدث تلقائياً! ✅
```

---

## ⚠️ الأخطاء الشائعة:

### ❌ "Deployment failed"
- في Railway: "Logs"
- ابحث عن رسالة الخطأ
- أصلح محلياً
- Push مرة أخرى

### ❌ "Bot not responding"
- تحقق: TELEGRAM_BOT_TOKEN صحيح؟
- في Logs: هل البوت بدأ؟
- أرسل رسالة مرة أخرى

### ❌ "DATABASE_URL not found"
- في Railway: "Add Service"
- اختر: "PostgreSQL"
- سيتم إنشاؤه تلقائياً

---

## 📞 الدعم السريع:

| المشكلة | الحل |
|--------|------|
| أين GitHub Desktop؟ | https://desktop.github.com |
| أين رقم البوت؟ | تحدث @BotFather على Telegram |
| كيف أضيف DATABASE_URL؟ | Railway: Add Service → PostgreSQL |
| البوت لا يعمل | تحقق من Logs في Railway |

---

**تم الإنشاء:** 14 يناير 2026
**الطريقة:** GitHub Desktop (الأسهل)
**الوقت:** 15 دقيقة فقط
