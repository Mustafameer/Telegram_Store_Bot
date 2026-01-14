# ⚙️ دليل تشغيل البوت تلقائياً على Windows

## 🎯 الهدف:
تشغيل البوت تلقائياً عند بدء التشغيل بدون الحاجة لفتح Terminal.

---

## 🚀 الطريقة 1: استخدام Task Scheduler (الأفضل والأسهل)

### الخطوة 1: فتح Task Scheduler

#### ✅ الطريقة أ - عبر البحث:
1. اضغط على `Windows Key` + `R`
2. اكتب: `taskschd.msc`
3. اضغط Enter

#### ✅ الطريقة ب - عبر Control Panel:
1. اذهب إلى Control Panel → Administrative Tools
2. اختر Task Scheduler

---

### الخطوة 2: إنشاء Task جديد

1. في الجانب الأيمن، اضغط على **"Create Task"**

2. في تبويب **"General"**:
   - اسم: `TelegramStoreBot`
   - وصف: `Telegram Store Bot`
   - اختر: ✅ "Run with highest privileges"

3. في تبويب **"Triggers"**:
   - اضغط على "New..."
   - اختر: "At startup"
   - اضغط OK

4. في تبويب **"Actions"**:
   - اضغط على "New..."
   - **Program/script**: `python.exe`
   - **Add arguments**: `bot.py`
   - **Start in**: `C:\Users\Hp\Desktop\TelegramStoreBot`
   - اضغط OK

5. اضغط OK لحفظ Task

---

## 🚀 الطريقة 2: استخدام PowerShell Script (أوتوماتيكي)

### الخطوة 1: فتح PowerShell بصلاحيات Admin

1. اضغط على `Windows Key`
2. اكتب: `PowerShell`
3. اضغط على **"Run as Administrator"**

### الخطوة 2: تشغيل Script

```powershell
cd "C:\Users\Hp\Desktop\TelegramStoreBot"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_scheduled_task.ps1
```

---

## 🚀 الطريقة 3: استخدام Batch File مباشرة

### الطريقة البسيطة:

1. انقر مرتين على:
   ```
   C:\Users\Hp\Desktop\TelegramStoreBot\run_bot_background.bat
   ```

2. البوت سيعمل في الخلفية (بدون نافذة Console ظاهرة)

---

## ✅ التحقق من أن البوت يعمل:

### 1️⃣ عبر Task Scheduler:
1. افتح Task Scheduler
2. ابحث عن `TelegramStoreBot`
3. انقر عليها بزر الفأرة الأيمن
4. اختر "Run" لتشغيل البوت فوراً
5. تحقق من "Status" - يجب أن يكون "Running"

### 2️⃣ عبر Telegram:
- أرسل رسالة للبوت
- يجب أن يرد على الفور

### 3️⃣ عبر Task Manager:
1. اضغط `Ctrl + Shift + Esc`
2. ابحث عن `python.exe` في القائمة
3. يجب أن تراه يعمل

---

## 🔄 إعادة تشغيل البوت:

### إذا تعطل البوت:

**الطريقة 1:** عبر Task Scheduler:
1. افتح Task Scheduler
2. اضغط بزر أيمن على Task
3. اختر "Run"

**الطريقة 2:** عبر Command Prompt:
```bash
taskkill /F /IM python.exe
# الانتظار 5 ثوان
python bot.py
```

---

## 🛠️ حل المشاكل:

### ❌ المشكلة: Task لا تعمل
**الحل:**
1. تأكد من أن DATABASE_URL محددة في .env
2. تأكد من اتصال الإنترنت
3. تحقق من أن .env موجود في المجلد

### ❌ المشكلة: البوت يتوقف بعد فترة
**الحل:**
1. أضف restart logic للبوت
2. استخدم pm2 (أكثر موثوقية)
3. استخدم systemd (على Linux)

### ❌ المشكلة: لا يمكن فتح PowerShell Script
**الحل:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📊 مقارنة الطرق:

| الطريقة | السهولة | الموثوقية | الأداء |
|--------|--------|----------|--------|
| Task Scheduler | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | جيدة |
| PowerShell Script | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | جيدة |
| Batch File | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | متوسطة |
| Windows Service | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ممتازة |
| pm2 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ممتازة |

---

## 🎯 التوصية:

### للمبتدئين:
👉 **استخدم Task Scheduler** (الطريقة 1)
- سهلة جداً
- لا تحتاج خبرة
- موثوقة جداً

### للمحترفين:
👉 **استخدم pm2 أو systemd**
- أكثر موثوقية
- restart تلقائي
- logging محسّن

---

**تم التحديث:** 14 يناير 2026
