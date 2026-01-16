# دليل تشغيل بوت شحن الهاتف المحمول على سرفر محلي

## 📋 وصف المشروع
هذا بوت Telegram لشحن الهاتف المحمول (Mobile Recharge Bot) مكتوب بلغة PHP ويدعم عملات عراقية متعددة (Asiacell, Zain, Korek, Iraqsell, Alkafil, etc).

---

## ⚙️ المتطلبات

### 1. **البرامج المطلوبة**
- **PHP 7.4+** (مثبت وفعال في سطر الأوامر)
- **MySQL/MariaDB** (نسخة 5.7 أو أحدث)
- **Apache** أو **Nginx** (مع دعم PHP)
- **cURL** و **MySQLi** (مفعلة في PHP)

### 2. **أدوات إضافية**
- **Composer** (اختياري - مثبت مسبقاً)
- **Git** (اختياري)

---

## 🔧 خطوات التثبيت على Windows

### الخطوة 1: تثبيت XAMPP (الأسهل)
1. حمّل [XAMPP](https://www.apachefriends.org/)
2. ثبّتها بالإعدادات الافتراضية
3. تأكد من تفعيل:
   - Apache
   - MySQL
   - PHP مع cURL و MySQLi

### الخطوة 2: نسخ مجلد المشروع
```bash
# انسخ المشروع إلى مجلد htdocs
xcopy "C:\Users\Hp\Desktop\TELEBOT\mobilerechargev2 2\mobilerechargev2" "C:\xampp\htdocs\mobilerechargev2" /E /I
```

### الخطوة 3: إعداد قاعدة البيانات
1. افتح phpMyAdmin من https://localhost/phpmyadmin
2. انقر على الخيار "استيراد" (Import)
3. اختر ملف `mr.sql` من مجلد المشروع
4. انقر "استيراد"

**النتيجة المتوقعة:** ستُنشأ قاعدة بيانات `mr` مع جميع الجداول

---

## 🔑 إعداد مفاتيح Telegram

### تحديث API Key
1. افتح ملف [config.php](mobilerechargev2/config.php#L6)
2. استبدل القيمة الحالية بـ Token البوت الخاص بك:

```php
define('API_KEY', "YOUR_BOT_TOKEN_HERE");
```

**للحصول على Token:**
- تحدث مع BotFather على Telegram
- أرسل `/newbot`
- اتبع التعليمات

---

## 📝 الإعدادات الأساسية

### إعدادات قاعدة البيانات
في [config.php](mobilerechargev2/config.php#L12-L14):

```php
$Host = "localhost";      // عنوان الخادم
$UserName = "root";       // اسم المستخدم
$PassWord = '';           // كلمة المرور (فارغة افتراضياً)
$DBName = "mr";           // اسم قاعدة البيانات
```

### المسؤولون والمالكون
في جدول `bot`:
- `admins`: معرفات مسؤولي البوت
- `owners`: معرفات مالكي البوت (يتلقون التقارير)

---

## 🚀 التشغيل

### الطريقة 1: استخدام Apache (XAMPP)
```bash
# ابدأ Apache و MySQL من XAMPP Control Panel
# أو من سطر الأوامر:
"C:\xampp\apache_start.bat"
"C:\xampp\mysql_start.bat"

# ثم افتح المتصفح:
http://localhost/phpmyadmin  # للتحقق من قاعدة البيانات
```

### الطريقة 2: استخدام PHP Built-in Server
```bash
# انتقل إلى مجلد المشروع
cd C:\xampp\htdocs\mobilerechargev2

# شغّل الخادم
php -S localhost:8000

# افتح في المتصفح:
http://localhost:8000/xindex.php
```

---

## 📞 ربط البوت مع Telegram

### Webhook Method (الموصى به)
البوت يستخدم Webhook لاستقبال التحديثات من Telegram.

تأكد من:
1. **عنوان URL العام**: يجب أن يكون المشروع متاحاً على الإنترنت (استخدم Ngrok للاختبار)
2. **HTTPS**: Telegram يتطلب HTTPS

#### اختبار محلي مع Ngrok:
```bash
# حمّل Ngrok من https://ngrok.com/download
ngrok http 80

# استخدم العنوان المُنتج مع Telegram Bot API
# curl https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-ngrok-url/mobilerechargev2/xindex.php
```

### Polling Method (للاختبار المحلي)
للاختبار بدون Webhook، أنشئ ملف polling:

```php
<?php
require_once 'config.php';
require_once 'Control/main.class.php';

$BOT = new Main(API_KEY);

while(true) {
    $updates = json_decode($BOT->sendCommand('getUpdates'), true);
    foreach($updates['result'] as $update) {
        // معالجة التحديث
        include 'xindex.php';
    }
    sleep(1);
}
```

---

## ⏲️ Jobs المجدولة (Cron Jobs)

ملف [cronjob.php](mobilerechargev2/cronjob.php) يقوم بـ:
- إرسال التقارير اليومية
- حساب الأرباح
- تنظيف البيانات

### تشغيل يومي على Windows:
1. افتح Task Scheduler
2. أنشئ مهمة جديدة:
   ```
   Program: C:\xampp\php\php.exe
   Arguments: C:\xampp\htdocs\mobilerechargev2\cronjob.php
   Schedule: يومياً في الساعة المطلوبة
   ```

---

## 🧪 الاختبار

### 1. اختبر الاتصال بقاعدة البيانات
```bash
php -r "
  mysqli_connect('localhost', 'root', '', 'mr');
  echo mysqli_connect_error() ? 'خطأ: ' . mysqli_connect_error() : 'متصل بنجاح!';
"
```

### 2. اختبر API Telegram
```bash
php -r "
  \$token = 'YOUR_TOKEN_HERE';
  \$url = 'https://api.telegram.org/bot' . \$token . '/getMe';
  \$result = json_decode(file_get_contents(\$url), true);
  print_r(\$result);
"
```

### 3. اختبر الويب هوك
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":{"text":"/start","from":{"id":123,"first_name":"Test"}}}' \
  http://localhost/mobilerechargev2/xindex.php
```

---

## 📂 هيكل المشروع

```
mobilerechargev2/
├── config.php              # الإعدادات والاتصالات
├── xindex.php              # معالج Webhook الرئيسي
├── cronjob.php             # المهام المجدولة
├── numbers.json            # قائمة الأرقام
├── mr.sql                  # ملف قاعدة البيانات
├── Control/
│   └── main.class.php      # الفئة الرئيسية للبوت
├── Plugins/
│   ├── User/               # أوامر المستخدم
│   ├── Owner/              # أوامر المالك
│   └── Admin/              # أوامر المسؤول
└── Languages/
    └── ar.php              # الترجمات العربية
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: "لا يمكن الاتصال بقاعدة البيانات"
**الحل:**
- تأكد من تشغيل MySQL
- تحقق من بيانات الاتصال في `config.php`
- تأكد من وجود قاعدة البيانات `mr`

### المشكلة: "PHP لم تُثبّت بشكل صحيح"
**الحل:**
```bash
php -v  # تحقق من إصدار PHP
php -m  # تحقق من الإضافات المثبتة (يجب أن تجد curl و mysqli)
```

### المشكلة: "البوت لا يرد على الرسائل"
**الحل:**
- تحقق من صحة API_KEY
- تأكد من أن Webhook مُسجّل صحيحاً
- فعّل نمط Debug في `sendCommand()` لعرض الأخطاء

---

## 📊 الملفات الهامة المراجعة

| الملف | الوصف |
|------|-------|
| [config.php](mobilerechargev2/config.php) | المفاتيح والإعدادات الأساسية |
| [xindex.php](mobilerechargev2/xindex.php) | معالج الويب هوك الرئيسي |
| [main.class.php](mobilerechargev2/Control/main.class.php) | فئة البوت الأساسية |
| [cronjob.php](mobilerechargev2/cronjob.php) | المهام المجدولة |
| [mr.sql](mr.sql) | تصدير قاعدة البيانات |

---

## ✅ قائمة التحقق قبل الإطلاق

- [ ] تثبيت PHP 7.4+ و MySQL
- [ ] نسخ المشروع إلى مجلد الويب
- [ ] استيراد ملف `mr.sql` في phpMyAdmin
- [ ] تحديث `API_KEY` في `config.php`
- [ ] تفعيل Apache أو استخدام PHP Server
- [ ] اختبار الاتصال بقاعدة البيانات
- [ ] اختبار API Telegram
- [ ] ربط Webhook مع Telegram (أو استخدام Polling)

---

## 📞 دعم إضافي

للمزيد من المعلومات:
- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [PHP MySQLi Documentation](https://www.php.net/manual/en/book.mysqli.php)
- [cURL Documentation](https://www.php.net/manual/en/book.curl.php)

---

**آخر تحديث:** January 15, 2026
**الحالة:** ✅ جاهز للتشغيل
