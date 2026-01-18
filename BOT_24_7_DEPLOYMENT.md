# 🚀 تشغيل البوت 24/7 بدون توقف

## 📌 الخيارات المتاحة

هناك 4 طرق لتشغيل البوت بشكل مستمر:

---

## ✅ **الخيار 1: Railway (الأفضل - بدون تكلفة)**

Railway توفر تشغيل مستمر في السحابة بدون تكلفة (تقريباً).

### الخطوات:

#### 1️⃣ إنشء حساب على Railway
- اذهب إلى [railway.app](https://railway.app)
- سجل دخول بـ GitHub
- أنشئ مشروع جديد

#### 2️⃣ ربط المستودع الخاص بك
```bash
# تأكد من وجود Procfile في المستودع
cat Procfile
# يجب أن يحتوي على:
# web: python bot.py
```

#### 3️⃣ إضافة متغيرات البيئة
```
DATABASE_URL=postgresql://username:password@host:port/dbname
TELEGRAM_BOT_TOKEN=your_token_here
```

#### 4️⃣ النشر
```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
```

### ✅ المميزات:
- ✅ مجاني (تقريباً)
- ✅ تشغيل مستمر 24/7
- ✅ قاعدة بيانات PostgreSQL مدمجة
- ✅ دعم مراقبة الأداء
- ✅ نشر تلقائي عند كل git push

### 📍 الملفات الموجودة:
- `Procfile` - ملف نشر جاهز
- `railway.json` - إعدادات Railway
- `run_cloud.bat` - سكريبت نشر
- `deploy_to_cloud.bat` - سكريبت نشر آخر

---

## ✅ **الخيار 2: Windows Task Scheduler (للتشغيل على جهازك)**

إذا كنت تريد تشغيل البوت على جهازك Windows بشكل مستمر:

### الخطوات:

#### 1️⃣ أنشئ ملف Batch

أنشئ ملف `run_bot_24_7.bat`:

```batch
@echo off
REM تشغيل البوت بشكل مستمر - إذا توقف، ابدأ من جديد

:loop
echo.
echo ====================================
echo تشغيل البوت...
echo ====================================
echo الوقت: %date% %time%
echo.

python bot.py

echo.
echo ====================================
echo انتظر 10 ثوانٍ قبل إعادة المحاولة...
echo ====================================
echo.

timeout /t 10 /nobreak

goto loop
```

#### 2️⃣ اجعل الملف آمناً من الإغلاق العرضي

أنشئ ملف `protect_bot.bat`:

```batch
@echo off
REM حماية البوت من الإغلاق

taskkill /FI "WINDOWTITLE eq تشغيل البوت*" /T /F >nul 2>&1

REM تشغيل البوت في نافذة مخفية
start /B python bot.py

REM التحقق كل دقيقة - إذا توقف، أعد تشغيله
:check
timeout /t 60 /nobreak
tasklist | find "python.exe" >nul
if errorlevel 1 (
    echo البوت توقف! إعادة التشغيل...
    start /B python bot.py
)
goto check
```

#### 3️⃣ أضفه إلى Windows Task Scheduler

**الطريقة الصحيحة:**

```powershell
# افتح PowerShell كمسؤول وشغل هذا الأمر:

$action = New-ScheduledTaskAction -Execute "C:\Users\Hp\Desktop\TelegramStoreBot\run_bot_24_7.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Description "Run Telegram Bot 24/7"
Register-ScheduledTask -TaskName "TelegramBot24_7" -InputObject $task
```

**أو استخدم الواجهة الرسومية:**

1. اضغط `Win + R` واكتب `taskschd.msc`
2. اضغط على "Create Basic Task..."
3. اكتب الاسم: `TelegramBot24_7`
4. اختر "Run whether user is logged in or not"
5. في التريغر، اختر "At Startup"
6. في الأكشن:
   - Program: `C:\Users\Hp\Desktop\TelegramStoreBot\run_bot_24_7.bat`
   - Start in: `C:\Users\Hp\Desktop\TelegramStoreBot`
7. اضغط OK

### ✅ المميزات:
- ✅ بدون تكلفة
- ✅ يعمل على جهازك
- ✅ إعادة تشغيل تلقائي عند الفشل
- ✅ تشغيل عند بدء Windows

### ⚠️ العيوب:
- ❌ يحتاج جهازك مشغلاً دائماً
- ❌ استهلاك كهرباء
- ❌ أبطأ من السحابة

---

## ✅ **الخيار 3: PM2 (للأجهزة و Linux/Mac)**

PM2 أداة قوية لإدارة العمليات:

### التثبيت:

```bash
# تثبيت Node.js أولاً (إذا لم يكن مثبتاً)
# ثم:

npm install -g pm2

# أو على Windows:
npm install --global pm2
```

### الاستخدام:

```bash
# تشغيل البوت مع PM2
cd C:\Users\Hp\Desktop\TelegramStoreBot
pm2 start bot.py --name "TelegramBot"

# عرض الحالة
pm2 status

# عرض السجلات
pm2 logs TelegramBot

# إعادة التشغيل
pm2 restart TelegramBot

# الإيقاف
pm2 stop TelegramBot

# حفظ العملية لتبدأ تلقائياً عند التمهيد
pm2 startup

# حفظ القائمة
pm2 save
```

### إنشء ملف إعدادات PM2

أنشئ `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'TelegramBot',
      script: 'bot.py',
      interpreter: 'python',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '500M',
      env: {
        DATABASE_URL: 'your_database_url',
        TELEGRAM_BOT_TOKEN: 'your_token'
      },
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      log_file: './logs/combined.log',
      time: true,
      autorestart: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000
    }
  ]
};
```

### التشغيل من الملف:

```bash
pm2 start ecosystem.config.js
```

### ✅ المميزات:
- ✅ قوي وموثوق
- ✅ إعادة تشغيل تلقائي
- ✅ مراقبة استخدام الموارد
- ✅ يعمل على Windows و Linux و Mac

---

## ✅ **الخيار 4: Docker (للمحترفين)**

إذا كنت تريد حل احترافي:

### أنشئ `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# نسخ الملفات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# تشغيل البوت
CMD ["python", "bot.py"]
```

### أنشئ `docker-compose.yml`:

```yaml
version: '3.8'

services:
  bot:
    build: .
    container_name: telegram_bot
    environment:
      DATABASE_URL: ${DATABASE_URL}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    restart: always
    volumes:
      - ./data:/app/data
    networks:
      - bot-network

  postgres:
    image: postgres:15
    container_name: postgres_db
    environment:
      POSTGRES_DB: telegrambot
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bot-network

volumes:
  postgres_data:

networks:
  bot-network:
```

### التشغيل:

```bash
docker-compose up -d
```

### ✅ المميزات:
- ✅ عزل كامل للبيئة
- ✅ سهل النشر على أي خادم
- ✅ قابل للتوسع
- ✅ احترافي جداً

---

## 🏆 **الخيار الموصى به: Railway**

### 🎯 لماذا Railway؟

| المعيار | Railway | Windows Task | PM2 | Docker |
|--------|---------|------------|-----|--------|
| **السعر** | مجاني | مجاني | مجاني | مجاني |
| **السهولة** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **الموثوقية** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **الأداء** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **المراقبة** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### 💡 التوصية:
**استخدم Railway** - إنها الأفضل والأسهل والأكثر موثوقية.

---

## 🔧 **الخطوات السريعة للنشر على Railway**

### 1️⃣ تأكد من وجود المتغيرات البيئية

أنشئ أو عدل `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 2️⃣ تحقق من `Procfile`

```
web: python bot.py
```

### 3️⃣ دفع إلى GitHub

```bash
git add .
git commit -m "Ready for Railway deployment"
git push
```

### 4️⃣ إنشاء المشروع على Railway

```bash
# إذا لم تكن مثبتاً:
npm install -g @railway/cli

# سجل دخول
railway login

# أنشئ مشروع جديد
railway init

# ربط المستودع
railway link

# نشر
railway up
```

### 5️⃣ إضافة قاعدة البيانات

في لوحة التحكم على Railway:
1. اضغط "New"
2. اختر "Database" → "PostgreSQL"
3. سيتم إنشاء `DATABASE_URL` تلقائياً

### ✅ تم! البوت يعمل الآن 24/7 🎉

---

## 📊 **مراقبة البوت**

### على Railway:

1. اذهب إلى [railway.app/dashboard](https://railway.app/dashboard)
2. اختر مشروعك
3. اضغط على "Deployments"
4. شاهد السجلات والأخطاء

### أوامر مفيدة:

```bash
# عرض السجلات
railway logs

# عرض الحالة
railway status

# إعادة النشر
railway up
```

---

## 🚨 **استكشاف الأخطاء**

### البوت لا يتصل بقاعدة البيانات

```python
# تحقق من bot.py السطر 1:
IS_POSTGRES = 'DATABASE_URL' in os.environ
print(f"Using PostgreSQL: {IS_POSTGRES}")
```

### البوت يتوقف بدون سبب

```bash
# شاهد السجلات:
railway logs --tail

# أعد النشر:
railway up
```

### استهلاك الموارد مرتفع

```python
# في bot.py، أضف حد للقصور:
# قيد عدد الاتصالات المتزامنة
# استخدم connection pooling
```

---

## ✨ **الخلاصة**

اختر الخيار الأنسب:

| الحالة | الخيار |
|-------|--------|
| تريد الأفضل والأسهل | **Railway** ✅ |
| جهازك مشغل دائماً | Windows Task Scheduler |
| تريد حل احترافي | Docker |
| تريد مراقبة قوية | PM2 |

---

## 📞 **الدعم**

إذا واجهت مشكلة:

1. اقرأ السجلات
2. تحقق من المتغيرات البيئية
3. تأكد من قاعدة البيانات
4. جرب إعادة النشر

---

**الآن بوتك يعمل 24/7 بدون توقف! 🚀**

