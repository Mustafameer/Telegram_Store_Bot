# 🚀 نشر البوت على Railway

> دليل شامل لنشر بوت شحن الهاتف المحمول على منصة Railway السحابية

---

## 📋 المحتويات

1. [ما هي Railway؟](#ما-هي-railway)
2. [المتطلبات الأساسية](#المتطلبات-الأساسية)
3. [خطوات التثبيت](#خطوات-التثبيت)
4. [الإعدادات](#الإعدادات)
5. [النشر](#النشر)
6. [المراقبة والصيانة](#المراقبة-والصيانة)
7. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## ما هي Railway؟

**Railway** هي منصة سحابية حديثة لنشر التطبيقات:

✅ **المميزات:**
- نشر سهل من GitHub
- بيئات متعددة (local, preview, production)
- SQLite و PostgreSQL مدمج
- متغيرات البيئة آمنة
- سجلات مباشرة (Logs)
- مراقبة الموارد (CPU, Memory)
- سعر منخفض أو مجاني للبدء

---

## المتطلبات الأساسية

### 1. حساب على Railway
- زيارة: https://railway.app
- التسجيل عبر GitHub

### 2. Repository على GitHub
```bash
git clone https://github.com/yourusername/mobile-recharge-bot.git
cd mobile-recharge-bot
```

### 3. Telegram Bot Token
- احصل عليه من @BotFather على Telegram

---

## خطوات التثبيت

### الخطوة 1️⃣: إعداد المشروع محلياً

```bash
# انسخ المجلد
cd mobile_recharge_bot_python

# أنشئ بيئة افتراضية
python -m venv venv

# فعّل البيئة الافتراضية
# على Windows:
venv\Scripts\activate
# على Mac/Linux:
source venv/bin/activate

# ثبّت المتطلبات
pip install -r requirements.txt

# أنشئ ملف .env من .env.example
cp .env.example .env

# عدّل .env بـ معلوماتك
```

### الخطوة 2️⃣: اختبر محلياً

```bash
# تأكد من أن config صحيح
python -c "from config import API_KEY; print(f'Bot ID: {API_KEY.split(\":\")[0]}')"

# شغّل الويب هوك
python main.py
```

يجب أن ترى:
```
Starting bot on 0.0.0.0:8000
```

### الخطوة 3️⃣: ادفع إلى GitHub

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

---

## النشر على Railway

### الطريقة 1: عبر واجهة Railway (الأسهل)

#### 1. إنشاء مشروع جديد
1. اذهب إلى: https://railway.app/dashboard
2. اضغط `+ New Project`
3. اختر `Deploy from GitHub repo`
4. اختر الـ repository الخاص بك

#### 2. اختيار البرنامج
- Railway سيكتشف تلقائياً أنه مشروع Python
- سيستخدم الـ `Procfile` و `requirements.txt`

#### 3. إضافة متغيرات البيئة
1. اذهب إلى `Variables` في Dashboard
2. أضف المتغيرات:

```
TELEGRAM_API_KEY = Your_Bot_Token_Here
WEBHOOK_URL = https://your-railway-app.up.railway.app/webhook
ADMIN_IDS = 5420647695
OWNER_IDS = 787700246,204378180
MAINTENANCE_MODE = False
RAILWAY_ENVIRONMENT = production
```

#### 4. نشر
1. اضغط `Deploy`
2. انتظر حتى ينتهي النشر (2-3 دقائق)
3. احصل على الـ URL الخاص بك

---

### الطريقة 2: عبر CLI (البرنامج الموسع)

#### 1. ثبّت Railway CLI
```bash
npm install -g @railway/cli
# أو
brew install railway
```

#### 2. سجّل الدخول
```bash
railway login
```

#### 3. أنشئ مشروع جديد
```bash
railway init
```

#### 4. أضف متغيرات البيئة
```bash
railway variable add TELEGRAM_API_KEY your_token_here
railway variable add WEBHOOK_URL https://your-app.up.railway.app/webhook
railway variable add ADMIN_IDS 5420647695
railway variable add OWNER_IDS 787700246,204378180
```

#### 5. نشر
```bash
railway up
```

---

## الإعدادات على Railway

### 1️⃣ تعيين Webhook

بعد النشر، اذهب إلى URL الخاص بك:

```bash
curl -X POST https://your-app.up.railway.app/set_webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.up.railway.app/webhook"}'
```

أو من Python:
```python
from telegram_api import telegram_api

result = telegram_api.set_webhook("https://your-app.up.railway.app/webhook")
print(result)
```

### 2️⃣ التحقق من الـ Webhook

```bash
curl https://your-app.up.railway.app/get_webhook_info
```

يجب أن ترى:
```json
{
  "ok": true,
  "webhook_info": {
    "url": "https://your-app.up.railway.app/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 3️⃣ اختبر البوت

أرسل `/start` إلى البوت على Telegram وتحقق من الرد

---

## المراقبة والصيانة

### 1️⃣ عرض السجلات

```bash
# عبر الواجهة
# اذهب إلى Dashboard > Logs

# عبر CLI
railway logs
```

### 2️⃣ عرض موارد التطبيق

- اذهب إلى Dashboard
- شاهد CPU و Memory Usage
- إذا تجاوز الحد، upgrade الـ plan

### 3️⃣ متابعة البوت

يمكنك إضافة routes للمراقبة:

```python
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})
```

ثم استخدام:
```bash
curl https://your-app.up.railway.app/health
```

---

## استكشاف الأخطاء

### المشكلة: "Deployment Failed"

**الحل:**
1. تحقق من logs: `railway logs`
2. تأكد من وجود `Procfile`
3. تأكد من أن `requirements.txt` صحيح

```bash
# اختبر محلياً
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 webhook:app
```

---

### المشكلة: "Bot not responding"

**الحل:**
1. تحقق من متغيرات البيئة:
   ```bash
   railway variable list
   ```

2. تحقق من الـ Webhook:
   ```bash
   curl https://your-app.up.railway.app/get_webhook_info
   ```

3. تحقق من السجلات:
   ```bash
   railway logs
   ```

4. اختبر التصحيح:
   ```bash
   curl -X POST https://your-app.up.railway.app/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

---

### المشكلة: "Database not found"

**السبب:** SQLite قد لا يتم حفظها على Railway

**الحل:** استخدم PostgreSQL بدلاً من SQLite

#### تفعيل PostgreSQL على Railway:

1. في Dashboard، اضغط `+ Add Service`
2. اختر `Postgres`
3. سيتم إضافة متغير `DATABASE_URL` تلقائياً

ثم عدّل `database.py` لدعم PostgreSQL:

```python
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///./bot.db")
```

---

## نصائح الإنتاج

### 1️⃣ الأمان
```
✅ استخدم متغيرات البيئة للحساسية
✅ فعّل HTTPS (مدمج في Railway)
✅ حدّد الـ Admin IDs بشكل صريح
✅ لا تضع المفاتيح في الأكواد
```

### 2️⃣ الأداء
```
✅ استخدم PostgreSQL بدلاً من SQLite
✅ أضف caching للبيانات المتكررة
✅ راقب أوقات الاستجابة
✅ استخدم workers متعددة (في Procfile)
```

### 3️⃣ المراقبة
```
✅ تابع السجلات بانتظام
✅ أنشئ تنبيهات للأخطاء
✅ احفظ النسخ الاحتياطية من البيانات
✅ اختبر البوت يومياً
```

---

## متغيرات البيئة الكاملة

| المتغير | الوصف | مثال |
|--------|-------|-------|
| `TELEGRAM_API_KEY` | Bot Token | `1234567:ABCDEFgh...` |
| `WEBHOOK_URL` | رابط الويب هوك | `https://app.up.railway.app/webhook` |
| `ADMIN_IDS` | معرفات المسؤولين | `123,456,789` |
| `OWNER_IDS` | معرفات المالكين | `123,456` |
| `DATABASE_URL` | رابط قاعدة البيانات | يتم إنشاؤه تلقائياً |
| `MAINTENANCE_MODE` | وضع الصيانة | `False` |
| `LOG_LEVEL` | مستوى السجلات | `INFO` |
| `RAILWAY_ENVIRONMENT` | البيئة | `production` |

---

## أوامر مفيدة

```bash
# عرض جميع متغيرات البيئة
railway variable list

# عرض سجلات البوت
railway logs --follow

# عرض معلومات التطبيق
railway info

# حذف متغير
railway variable delete KEY_NAME

# اعادة نشر
railway deploy

# إيقاف التطبيق
railway pause

# تشغيل التطبيق
railway unpause
```

---

## مثال كامل للنشر

```bash
# 1. انسخ المشروع
git clone ...
cd mobile_recharge_bot_python

# 2. أنشئ بيئة على Railway
railway init

# 3. أضف متغيرات البيئة
railway variable add TELEGRAM_API_KEY "your-token"
railway variable add WEBHOOK_URL "https://your-app.up.railway.app/webhook"

# 4. نشّر
railway up

# 5. تحقق من الحالة
railway logs --follow

# 6. اختبر
curl https://your-app.up.railway.app/status

# 7. اضبط الـ Webhook
curl -X POST https://your-app.up.railway.app/set_webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.up.railway.app/webhook"}'
```

---

## الخلاصة

Railway توفر:
- ✅ نشر سهل جداً من GitHub
- ✅ متغيرات بيئة آمنة
- ✅ قواعد بيانات متقدمة
- ✅ سجلات وتراقب فورية
- ✅ سعر منخفض للبدء (أو مجاني)

**البوت الآن جاهز للإنتاج!** 🚀

---

**آخر تحديث:** January 15, 2026
