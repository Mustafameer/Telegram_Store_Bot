# 🚀 تشغيل السرفر المحلي

> دليل سريع لتشغيل بوت شحن الهاتف المحمول على السرفر المحلي

---

## ⚡ البدء السريع

### الخطوة 1: تشغيل السرفر
```bash
# انقر على الملف
run_local_server.bat

# أو من سطر الأوامر
cd mobile_recharge_bot_python
python main.py
```

### الخطوة 2: اختبر البوت
```bash
# افتح Telegram وابدأ المحادثة مع البوت
# أرسل: /start

# أو من سطر الأوامر
curl http://192.168.0.108:8000/status
```

---

## 📋 إعدادات السرفر المحلي

```
🌐 IP Address:    192.168.0.108
🔌 Port:          8000
📍 Webhook URL:   http://192.168.0.108:8000/webhook
💾 Database:      bot_data.db (SQLite)
🔐 Password:      123
⚙️  Environment:   Local Development
```

---

## 🔧 الإعدادات المتقدمة

### تغيير الـ Port

عدّل ملف `.env`:
```env
PORT=8001
```

### تفعيل Debug Mode

عدّل ملف `.env`:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

### تغيير الـ Host

عدّل ملف `.env`:
```env
HOST=127.0.0.1        # localhost فقط
HOST=0.0.0.0          # جميع الأجهزة في الشبكة
HOST=192.168.0.108    # IP محدد
```

---

## 📡 API Endpoints

| الطلب | الوصف | الأمثلة |
|------|-------|--------|
| `POST /webhook` | استقبال التحديثات من Telegram | تحديثات البوت |
| `GET /status` | حالة السرفر | `curl http://192.168.0.108:8000/status` |
| `GET /test` | اختبار الاتصال بـ Telegram | `curl http://192.168.0.108:8000/test` |
| `POST /set_webhook` | تعيين الـ Webhook | متقدم |
| `GET /get_webhook_info` | معلومات الـ Webhook | `curl http://192.168.0.108:8000/get_webhook_info` |

---

## ✅ اختبار السرفر

### 1️⃣ اختبر الـ Status
```bash
curl http://192.168.0.108:8000/status
```

يجب أن ترى:
```json
{"status": "running"}
```

### 2️⃣ اختبر الـ Webhook
```bash
curl http://192.168.0.108:8000/get_webhook_info
```

يجب أن ترى:
```json
{
  "webhook_url": "http://192.168.0.108:8000/webhook",
  "status": "configured"
}
```

### 3️⃣ اختبر البوت
أرسل `/start` إلى البوت على Telegram

---

## 🐛 استكشاف الأخطاء

### المشكلة: "Address already in use"

**السبب:** البوت يعمل بالفعل على نفس الـ Port

**الحل:**
```bash
# غيّر الـ Port في .env
PORT=8001

# أو اقتل العملية
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

### المشكلة: "Connection refused"

**السبب:** السرفر لم يبدأ

**الحل:**
```bash
# تأكد من تثبيت المتطلبات
pip install -r requirements.txt

# تأكد من وجود .env
copy .env.example .env

# شغّل مباشرة
python main.py
```

---

### المشكلة: "Module not found"

**السبب:** المتطلبات لم تُثبّت

**الحل:**
```bash
# فعّل البيئة الافتراضية
venv\Scripts\activate

# ثبّت المتطلبات
pip install -r requirements.txt
```

---

## 📊 مراقبة السرفر

### عرض السجلات

```bash
# عند التشغيل، ستظهر السجلات مباشرة
# Logs appear in console

# أو اقرأ ملف bot.log
type bot.log

# أو تابع السجلات مباشرة
tail -f bot.log
```

### معلومات قيمة في السجلات

```
✅ [INFO] Telegram IP verified
✅ [DEBUG] User 123456 created
❌ [ERROR] Database connection failed
⚠️  [WARNING] Webhook update timeout
```

---

## 🎯 الاختبارات السريعة

### اختبر قاعدة البيانات

```python
from database import db
from config import DATABASE_URL

# تحقق من الاتصال
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print("✅ Database connected")
```

### اختبر Telegram API

```python
from telegram_api import telegram_api

# تحقق من البيانات
result = telegram_api.get_me()
print(result)
```

### اختبر قراءة الإعدادات

```python
from config import API_KEY, ADMIN_IDS, OWNER_IDS

print(f"Bot ID: {API_KEY.split(':')[0]}")
print(f"Admins: {ADMIN_IDS}")
print(f"Owners: {OWNER_IDS}")
```

---

## 🌐 الوصول من أجهزة أخرى

إذا كنت تريد الوصول من جهاز آخر في نفس الشبكة:

```bash
# من جهاز آخر
curl http://192.168.0.108:8000/status

# أو في المتصفح
http://192.168.0.108:8000/test
```

---

## 📝 ملخص الملفات

| الملف | الوصف |
|------|-------|
| `main.py` | نقطة الدخول الرئيسية |
| `webhook.py` | تطبيق Flask |
| `config.py` | الإعدادات |
| `database.py` | قاعدة البيانات |
| `telegram_api.py` | واجهة Telegram |
| `handlers.py` | معالجات الرسائل |
| `languages.py` | الترجمات |
| `bot.py` | منطق البوت |
| `.env` | متغيرات البيئة |
| `requirements.txt` | المتطلبات |

---

## ✨ نصائح

```
✅ استخدم DEBUG=True للتطوير
✅ تابع السجلات أثناء التطوير
✅ اختبر الـ API endpoints قبل النشر
✅ احفظ النسخة احتياطية من bot_data.db
✅ غيّر LOG_LEVEL إلى DEBUG لمزيد من التفاصيل
```

---

**البوت جاهز للعمل!** 🚀
