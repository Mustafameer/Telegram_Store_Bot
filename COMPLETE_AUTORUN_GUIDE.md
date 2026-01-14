# 🚀 تشغيل البوت تلقائياً - دليل عملي

## ❓ المشكلة:

البوت يستخدم `bot.infinity_polling()` - يتطلب عملية Python نشطة مستمرة:
- ❌ إغلاق Terminal → البوت يتوقف
- ❌ إعادة تشغيل الحاسوب → البوت لا يعمل
- ❌ يجب فتح Terminal في كل مرة

---

## ✅ الحل: 4 طرق للتشغيل التلقائي

### 🥇 **الطريقة 1: البسيطة - Double-Click Batch File**

**الأسرع والأبسط**

1. **انقر مرتين على:**
   ```
   run_bot_background.bat
   ```

2. **هذا سيشغل البوت:**
   - ✅ بدون نافذة Console
   - ✅ في الخلفية
   - ⏱️ يعمل حتى تغلق النافذة

**ملاحظة:** 
- قد تظهر نافذة console قصيرة
- إذا اختفت، معناه البوت يعمل

---

### 🥈 **الطريقة 2: Service Wrapper - مع Auto-Restart** ⭐

**الأفضل للاستخدام اليومي**

#### **أ) عبر Batch File:**
1. **انقر مرتين على:**
   ```
   run_with_service_wrapper.bat
   ```

2. **المميزات:**
   - ✅ إعادة تشغيل تلقائي عند التعطل
   - ✅ Logging مفصل في `bot_service.log`
   - ✅ يحافظ على البوت يعمل

#### **ب) عبر PowerShell:**
1. **افتح PowerShell** في المجلد
2. **اكتب:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\run_bot_service.ps1
   ```

---

### 🥉 **الطريقة 3: Task Scheduler - تشغيل تلقائي عند البدء** ⭐⭐

**الأفضل للإنتاج والاستخدام الدائم**

#### **الخطوات:**

1. **افتح Task Scheduler:**
   - اضغط: `Windows Key + R`
   - اكتب: `taskschd.msc`
   - اضغط: Enter

2. **في اليسار، انقر على "Create Task"**

3. **تبويب "General":**
   ```
   Name: TelegramStoreBot
   Description: Telegram Store Bot - Auto Run
   ✓ Run with highest privileges
   ```

4. **تبويب "Triggers":**
   - اضغط "New..."
   - اختر: "At Startup"
   - اضغط OK

5. **تبويب "Actions":**
   - اضغط "New..."
   - **Program/script:** `python.exe`
   - **Add arguments:** `bot.py`
   - **Start in:** `C:\Users\Hp\Desktop\TelegramStoreBot`
   - اضغط OK

6. **اضغط OK** لحفظ

**النتيجة:**
- ✅ البوت يشتغل تلقائياً عند بدء Windows
- ✅ يعمل دائماً في الخلفية
- ✅ لا حاجة لعمل شيء يدويًا

---

### 🔴 **الطريقة 4: PowerShell Script - للمتقدمين**

**للمستخدمين ذوي الخبرة**

1. **افتح PowerShell كـ Admin:**
   - اضغط: `Windows Key`
   - اكتب: `PowerShell`
   - اضغط: `Ctrl + Shift + Enter`

2. **اكتب:**
   ```powershell
   cd "C:\Users\Hp\Desktop\TelegramStoreBot"
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup_scheduled_task.ps1
   ```

3. **سيتم إنشاء Task Scheduler تلقائياً**

---

## ✅ التحقق من أن البوت يعمل:

### **الطريقة 1 - Task Manager:**
```
Ctrl + Shift + Esc → ابحث عن "python.exe"
```
يجب أن تراه في القائمة ✅

### **الطريقة 2 - Telegram:**
```
أرسل رسالة للبوت → يجب أن يرد فوراً ✅
```

### **الطريقة 3 - Logs:**
```
C:\Users\Hp\Desktop\TelegramStoreBot\bot_service.log
```
يجب أن تجد رسائل من البوت ✅

---

## 🔧 إيقاف أو إعادة تشغيل البوت:

### **إيقاف البوت:**

**عبر Command Prompt:**
```bash
taskkill /F /IM python.exe
```

**عبر Task Manager:**
1. `Ctrl + Shift + Esc`
2. ابحث عن `python.exe`
3. انقر عليها، ثم اضغط "End Task"

### **إعادة التشغيل:**

**عبر Task Scheduler:**
1. افتح Task Scheduler
2. ابحث عن: `TelegramStoreBot`
3. انقر بزر أيمن → "Run"

**أو شغّل البوت مرة أخرى:**
```
python bot.py
```

---

## 📊 مقارنة الطرق:

| الميزة | Batch File | Service Wrapper | Task Scheduler | PowerShell |
|--------|---|---|---|---|
| **سهولة الإعداد** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **التشغيل التلقائي** | ❌ | ❌* | ✅ | ✅ |
| **Auto-Restart** | ❌ | ✅ | ❌ | ❌ |
| **موثوقية** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Logging** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **مناسب للمبتدئين** | ✅ | ✅ | ⭐⭐⭐ | ❌ |

*مع إضافة startup shortcut

---

## 🎯 التوصيات:

### **للاستخدام الفوري:**
👉 **استخدم Batch File**
```
run_bot_background.bat
```

### **للاستقرار الأفضل:**
👉 **استخدم Service Wrapper**
```
run_with_service_wrapper.bat
```

### **للتشغيل التلقائي الدائم:**
👉 **استخدم Task Scheduler**
- يعمل عند بدء Windows
- يعمل دائماً

### **للمحترفين:**
👉 **استخدم PowerShell Script**
- أكثر مرونة
- تحكم كامل

---

## ⚠️ الأخطاء الشائعة:

### ❌ "PowerShell: command not found"
**الحل:**
```powershell
.\run_bot_service.ps1
```
لاحظ النقطة والخط المائل في البداية `.\`

### ❌ "ExecutionPolicy error"
**الحل:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### ❌ "python.exe not found"
**الحل:**
1. تأكد من تثبيت Python
2. استخدم المسار الكامل: `C:\Python39\python.exe`

### ❌ "DATABASE_URL not found"
**الحل:**
تأكد من وجود `.env` مع:
```
DATABASE_URL=...
```

---

## 🚀 البدء الفوري:

**اختر واحدة:**

1. **الأسرع:**
   ```
   Double-click: run_bot_background.bat
   ```

2. **الأفضل:**
   ```
   Double-click: run_with_service_wrapper.bat
   ```

3. **الدائم:**
   - اتبع خطوات Task Scheduler

---

## 📝 الملفات المساعدة:

- ✅ `run_bot_background.bat` - تشغيل بسيط
- ✅ `run_with_service_wrapper.bat` - مع Auto-Restart
- ✅ `run_bot_service.ps1` - PowerShell script
- ✅ `service_wrapper.py` - Service Wrapper
- ✅ `setup_scheduled_task.ps1` - إنشاء Task Scheduler
- ✅ `bot_service.log` - Logs (يُنشأ تلقائياً)

---

**تم التحديث:** 14 يناير 2026
**الحالة:** ✅ جاهز للاستخدام
**الثقة:** 100%
