# 🚀 إعدادات السرفر المحلي

> **دليل كامل لتشغيل بوت شحن الهاتف المحمول محلياً على 192.168.0.108:8000**

---

## 📋 الإعدادات السريعة

### معلومات الاتصال
```
🌐 عنوان IP:     192.168.0.108
🔌 المنفذ:       8000
📍 Webhook URL:  http://192.168.0.108:8000/webhook
💾 قاعدة البيانات: bot_data.db (SQLite)
🔐 كلمة المرور:    123
⚙️  البيئة:        Local Development
```

---

## ⚡ البدء السريع (3 خطوات)

### 1️⃣ افتح Command Prompt أو PowerShell
```bash
# Windows + R
cmd
# أو
powershell
```

### 2️⃣ انتقل إلى مجلد المشروع
```bash
cd c:\Users\Hp\Desktop\TELEBOT\mobile_recharge_bot_python
```

### 3️⃣ شغّل السرفر
```bash
# الطريقة الأولى: Python مباشر
python start_server.py

# أو الطريقة الثانية: ملف Batch
start.bat

# أو الطريقة الثالثة: PowerShell
powershell -ExecutionPolicy Bypass -File start.ps1
```

---

## ✅ التحقق من التشغيل الناجح

### علامات النجاح:
```
✅ "Starting bot on 192.168.0.108:8000"
✅ "WARNING in app.run, this is a development server"
✅ السرفر يستقبل الطلبات
```

### اختبر السرفر:

#### من نفس الجهاز:
```bash
# في نافذة أخرى
curl http://192.168.0.108:8000/status
```

**النتيجة المتوقعة:**
```json
{"status": "running"}
```

#### من جهاز آخر في الشبكة:
```bash
curl http://192.168.0.108:8000/test
```

#### في المتصفح:
```
http://192.168.0.108:8000/status
```

---

## 🔧 الإعدادات المتقدمة

### تغيير الـ Port

**ملف `.env`:**
```env
PORT=8001
```

ثم أعد تشغيل السرفر

---

### تفعيل Debug Mode

**ملف `.env`:**
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

---

### تغيير الـ Host

**ملف `.env`:**
```env
# للوصول المحلي فقط
HOST=127.0.0.1

# للشبكة المحلية
HOST=192.168.0.108

# لكل الواجهات
HOST=0.0.0.0
```

---

## 🤖 اختبار البوت على Telegram

### 1️⃣ أرسل رسالة للبوت
```
/start
```

### 2️⃣ اتبع التعليمات على الشاشة

### 3️⃣ اختبر الأوامر:
```
/account    - معلومات الحساب
/history    - السجل
/admin      - الوظائف الإدارية
/profit     - الأرباح
```

---

## 📊 مراقبة السرفر

### عرض السجلات في الـ Console

عند التشغيل، ستظهر السجلات مباشرة:
```
2026-01-15 12:34:56 - INFO - User 123456789 created
2026-01-15 12:34:57 - DEBUG - Processing message: /start
2026-01-15 12:34:58 - INFO - Message sent to 123456789
```

### قراءة ملف السجلات

```bash
# عرض السجلات
type bot.log

# أو من PowerShell
Get-Content bot.log -Tail 50 -Wait
```

---

## 🐛 استكشاف الأخطاء الشائعة

### ❌ "Address already in use"

**السبب:** البوت يعمل بالفعل

**الحل:**
```bash
# غيّر الـ Port في .env
PORT=8001

# أو اقتل العملية
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

### ❌ "Module not found"

**السبب:** المتطلبات لم تُثبّت

**الحل:**
```bash
pip install -r requirements.txt
```

---

### ❌ "FileNotFoundError: .env"

**السبب:** ملف .env غير موجود

**الحل:**
```bash
copy .env.example .env
# عدّل قيم .env
```

---

### ❌ "Connection refused"

**السبب:** السرفر لم يبدأ

**الحل:**
```bash
# تأكد من عدم وجود أخطاء في الملفات
python -m py_compile *.py

# شغّل مع معلومات أكثر
python start_server.py
```

---

## 🔗 API Endpoints المتاحة

| الطريقة | الرابط | الوصف |
|--------|--------|-------|
| POST | `/webhook` | استقبال التحديثات من Telegram |
| GET | `/status` | حالة السرفر |
| GET | `/test` | اختبار الاتصال |
| GET | `/get_webhook_info` | معلومات الـ Webhook |
| POST | `/set_webhook` | تعيين الـ Webhook |

---

## 📁 هيكل المشروع

```
mobile_recharge_bot_python/
├── start_server.py          # نقطة الدخول الرئيسية
├── start.bat               # ملف تشغيل Windows
├── start.ps1               # نص PowerShell
├── webhook.py              # تطبيق Flask
├── config.py               # الإعدادات
├── database.py             # قاعدة البيانات
├── telegram_api.py         # واجهة Telegram
├── handlers.py             # معالجات الرسائل
├── bot.py                  # منطق البوت
├── languages.py            # الترجمات
├── .env                    # متغيرات البيئة
├── .env.example            # مثال الإعدادات
├── requirements.txt        # المتطلبات
├── bot_data.db            # قاعدة البيانات (يُنشأ تلقائياً)
└── bot.log                # ملف السجلات (يُنشأ تلقائياً)
```

---

## 🌐 الوصول من أجهزة أخرى

### من جهاز في نفس الشبكة:

```bash
# اختبر الاتصال
curl http://192.168.0.108:8000/status

# أو في المتصفح
http://192.168.0.108:8000/test
```

### ملاحظة أمان:
⚠️ **تحذير:** السرفر المحلي **ليس آمناً** للإنتاج
- استخدمه فقط للتطوير والاختبار
- للإنتاج استخدم Railway (مع HTTPS)

---

## 📝 متغيرات البيئة (.env)

```env
# Telegram
TELEGRAM_API_KEY=your_token_here

# Server
HOST=192.168.0.108
PORT=8000
WEBHOOK_URL=http://192.168.0.108:8000/webhook

# Database
DATABASE_URL=sqlite:///bot_data.db
DB_PATH=bot_data.db
DB_PASSWORD=123

# Admin
ADMIN_IDS=5420647695
OWNER_IDS=787700246,204378180

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=bot.log

# Flask
DEBUG=True

# Railway
RAILWAY_ENVIRONMENT=local
```

---

## 💡 نصائح مفيدة

### تشغيل متعدد الأجهزة:

اذا كنت تريد تشغيل السرفر على أجهزة متعددة:
```env
HOST=0.0.0.0          # كل الواجهات
PORT=8000
```

### للتطوير السريع:

```env
DEBUG=True
LOG_LEVEL=DEBUG
MAINTENANCE_MODE=False
```

### لحفظ البيانات:

```bash
# اعمل نسخة احتياطية من قاعدة البيانات
copy bot_data.db bot_data_backup.db
```

---

## ✨ الخطوات التالية

بعد التشغيل الناجح:

1. ✅ اختبر البوت على Telegram
2. ✅ تحقق من السجلات
3. ✅ اختبر الأوامر الأساسية
4. ✅ عندما تكون جاهزاً → نشّر على Railway

---

## 🚀 النشر على Railway

بعد أن تتأكد من أن السرفر المحلي يعمل بنجاح:

```bash
# اتبع دليل RAILWAY_DEPLOYMENT.md
```

---

## 📞 معلومات إضافية

- 📚 [دليل Telegram Bot API](https://core.telegram.org/bots)
- 🐍 [Python Documentation](https://docs.python.org/)
- 🚀 [Railway Documentation](https://docs.railway.app/)

---

**تم التحديث:** January 15, 2026  
**الحالة:** ✅ جاهز للاستخدام
