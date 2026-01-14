# 🚀 تشغيل البوت تلقائياً - دليل شامل

## ❓ لماذا يجب تشغيل البوت من Terminal؟

البوت يستخدم **polling mode** - يعني أنه يطلب تحديثات من Telegram باستمرار:
```python
bot.infinity_polling()  # استطلاع مستمر
```

**المشاكل:**
- ❌ عندما تغلق Terminal → البوت يتوقف
- ❌ عندما تعيد تشغيل الحاسوب → البوت لا يعمل
- ❌ يجب فتح Terminal يدويًا في كل مرة

---

## ✅ الحل: تشغيل تلقائي بدون Terminal

### 🥇 الطريقة 1: Task Scheduler (الموصى بها)

**المميزات:**
- ✅ سهلة جداً
- ✅ تعمل على جميع إصدارات Windows
- ✅ تشغيل تلقائي عند بدء التشغيل
- ✅ موثوقة جداً

**الخطوات:**

1. **افتح Task Scheduler:**
   - اضغط: `Windows Key + R`
   - اكتب: `taskschd.msc`
   - اضغط: Enter

2. **انقر على "Create Task"** (في الجانب الأيمن)

3. **تبويب "General":**
   ```
   Name: TelegramStoreBot
   Description: Telegram Store Bot - Auto Run
   ✓ Run with highest privileges
   ```

4. **تبويب "Triggers":**
   - انقر "New..."
   - اختر: "At Startup"
   - انقر OK

5. **تبويب "Actions":**
   - انقر "New..."
   - Program/script: `python.exe`
   - Add arguments: `bot.py`
   - Start in: `C:\Users\Hp\Desktop\TelegramStoreBot`
   - انقر OK

6. **انقر OK** لحفظ

**الآن:**
- ✅ البوت سيعمل تلقائياً عند بدء Windows
- ✅ لا حاجة لفتح Terminal

---

### 🥈 الطريقة 2: Service Wrapper (مع Auto-Restart)

**المميزات:**
- ✅ إعادة تشغيل تلقائي عند التعطل
- ✅ Logging مفصل
- ✅ أكثر استقراراً

**الخطوات:**

1. **شغّل Batch File:**
   ```
   C:\Users\Hp\Desktop\TelegramStoreBot\run_with_service_wrapper.bat
   ```

2. **أو من Command Prompt:**
   ```bash
   cd C:\Users\Hp\Desktop\TelegramStoreBot
   python service_wrapper.py
   ```

**المميزات الإضافية:**
- 🔄 إعادة تشغيل تلقائي (5 محاولات)
- 📝 Logging مفصل في `bot_service.log`
- 🛡️ حماية من توقف البوت غير المتوقع

---

### 🥉 الطريقة 3: Batch File بسيط

**الخطوات:**

1. **انقر مرتين على:**
   ```
   C:\Users\Hp\Desktop\TelegramStoreBot\run_bot_background.bat
   ```

2. **هذا سيشغل البوت بدون نافذة Console ظاهرة**

**ملاحظة:**
- الأبسط لكن لا يعيد التشغيل تلقائياً عند التعطل

---

### 🔴 الطريقة 4: PowerShell Script

**للمستخدمين المتقدمين:**

```powershell
# فتح PowerShell كـ Admin وشغّل:
cd "C:\Users\Hp\Desktop\TelegramStoreBot"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_scheduled_task.ps1
```

---

## ✅ التحقق من أن البوت يعمل:

### 1️⃣ عبر Task Manager:
```
Ctrl + Shift + Esc → ابحث عن "python.exe"
```

### 2️⃣ عبر Telegram:
- أرسل رسالة للبوت
- يجب أن يرد فوراً

### 3️⃣ عبر Logs:
```
C:\Users\Hp\Desktop\TelegramStoreBot\bot_service.log
```

---

## 🔧 إعادة تشغيل البوت:

### إذا توقف البوت:

**الطريقة 1 - Task Scheduler:**
1. افتح Task Scheduler
2. ابحث عن: `TelegramStoreBot`
3. اضغط بزر أيمن → "Run"

**الطريقة 2 - Command Prompt:**
```bash
taskkill /F /IM python.exe
# ثم شغّل البوت مرة أخرى
```

**الطريقة 3 - Service Wrapper:**
- Service Wrapper سيعيد التشغيل تلقائياً

---

## 📊 مقارنة الطرق:

| الميزة | Task Scheduler | Service Wrapper | Batch File |
|--------|---|---|---|
| سهولة الإعداد | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| موثوقية | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Restart تلقائي | ❌ | ✅ | ❌ |
| Logging | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| عمل تلقائي | ✅ | ✅ (مع setup) | ❌ |
| استخدام الموارد | منخفض | منخفض | منخفض |

---

## 🎯 التوصية النهائية:

### للاستخدام الفوري:
👉 **استخدم Batch File**
```
run_bot_background.bat
```
- أسرع طريقة
- بدون تعقيدات

### للتشغيل التلقائي:
👉 **استخدم Task Scheduler**
- الأفضل للإنتاج
- تشغيل تلقائي عند بدء Windows

### للاستقرار الأقصى:
👉 **استخدم Service Wrapper**
- إعادة تشغيل تلقائي
- Logging مفصل
- الأكثر أماناً

---

## ⚠️ ملاحظات مهمة:

### 1️⃣ حول DATABASE_URL:
```bash
# تأكد من وجود .env مع DATABASE_URL
cat .env
```

### 2️⃣ في حالة الأخطاء:
```bash
# تحقق من Logs:
cat bot_service.log

# أو شغّل مباشرة:
python bot.py
```

### 3️⃣ إيقاف البوت:
```bash
taskkill /F /IM python.exe
```

---

## 🚀 البدء الفوري:

**اختر واحدة:**

1. **أسرع (بدون تشغيل تلقائي):**
   ```
   Double-click: run_bot_background.bat
   ```

2. **الأفضل (تشغيل تلقائي):**
   ```
   اتبع خطوات Task Scheduler أعلاه
   ```

3. **الأكثر استقراراً (مع Auto-Restart):**
   ```
   Double-click: run_with_service_wrapper.bat
   ```

---

**تم التحديث:** 14 يناير 2026
**الحالة:** ✅ جاهز للاستخدام
