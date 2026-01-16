# 🤖 بوت شحن الهاتف المحمول

> بوت Telegram متقدم لشحن الهاتف بعملات عراقية متعددة

[![Status](https://img.shields.io/badge/status-active-green)]()
[![PHP](https://img.shields.io/badge/PHP-7.4%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Language](https://img.shields.io/badge/Language-Arabic%20%26%20English-red)]()

---

## 📱 نظرة عامة

بوت Telegram ذكي يوفر خدمة شحن الهاتف المحمول للعملاء العراقيين مع:

- 💰 دعم عملات متعددة (Asiacell, Zain, Korek, Iraqsell, Alkafil وغيرها)
- 👥 إدارة متقدمة للمستخدمين والمسؤولين
- 📊 نظام تقارير وأرباح شامل
- 🔐 نظام أمان قوي مع التحقق من IP
- 🌍 دعم اللغة العربية الكامل
- ⚡ أداء عالي ومستقر

---

## 🚀 البدء السريع

### المتطلبات الأساسية
- **PHP 7.4+** مع MySQLi و cURL
- **MySQL 5.7+** أو MariaDB
- **خادم ويب** (Apache, Nginx, أو PHP Built-in)

### التثبيت في 3 خطوات

**1. تحضير قاعدة البيانات:**
```bash
mysql -u root < mr.sql
```

**2. تحديث الإعدادات:**
```bash
# عدّل API_KEY في:
# mobilerechargev2 2/mobilerechargev2/config.php
```

**3. تشغيل السرفر:**
```bash
cd "mobilerechargev2 2\mobilerechargev2"
php -S localhost:8000
```

**✅ البوت جاهز!** افتح Telegram وابدأ الدردشة مع البوت

---

## 📖 التوثيق

| الملف | الوصف |
|------|-------|
| [QUICKSTART.md](QUICKSTART.md) | 🚀 البدء السريع في 5 خطوات |
| [SETUP_LOCAL_SERVER.md](SETUP_LOCAL_SERVER.md) | 📖 دليل التثبيت المفصل |
| [REQUIREMENTS.md](REQUIREMENTS.md) | 📦 المتطلبات الكاملة |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 🔧 حل المشاكل الشائعة |

---

## 🎯 الميزات

### 👤 للمستخدمين العاديين
- 📱 شحن سهل وسريع
- 💳 محفظة آمنة
- 🧾 سجل المعاملات
- 💬 دعم فني متاح

### 👨‍💼 للمالكين
- 📊 لوحة تحكم متقدمة
- 💹 إحصائيات مفصلة
- 📈 تقارير يومية
- 👥 إدارة المستخدمين

### 🛡️ للمسؤولين
- 🔑 التحكم بالأسعار
- 📸 إدارة الصور
- 👮 مراقبة العمليات
- 🚫 إدارة الحظر

---

## 📁 هيكل المشروع

```
mobilerechargev2/
├── 🔧 config.php              # الإعدادات والمفاتيح
├── 🌐 xindex.php              # معالج Webhook الرئيسي
├── ⏲️  cronjob.php             # المهام المجدولة
├── 📊 mr.sql                  # قاعدة البيانات
├── 📋 numbers.json            # قائمة الأرقام
├── 📦 Control/
│   └── main.class.php         # الفئة الرئيسية
├── 🎮 Plugins/
│   ├── User/                  # أوامر المستخدم
│   ├── Owner/                 # أوامر المالك
│   └── Admin/                 # أوامر المسؤول
└── 🌍 Languages/
    └── ar.php                 # الترجمات العربية
```

---

## 🛠️ الأدوات والسكريبتات

### `setup.bat` - سكريبت الفحص والتثبيت
فحص شامل للمتطلبات والإعدادات:
```bash
setup.bat
```

### `test.bat` - سكريبت الاختبار
اختبار:
- الاتصال بقاعدة البيانات
- API Telegram
- الملفات المطلوبة
- المتغيرات المهمة

```bash
test.bat
```

---

## 🔑 الإعدادات المهمة

### حساب Telegram Bot
```php
// في config.php
define('API_KEY', "YOUR_BOT_TOKEN_HERE");
```

**للحصول على Token:**
1. تحدث مع @BotFather
2. أرسل `/newbot`
3. اتبع التعليمات
4. انسخ الـ Token

### قاعدة البيانات
```php
$Host = "localhost";
$UserName = "root";
$PassWord = '';  // اتركها فارغة للإعدادات الافتراضية
$DBName = "mr";
```

### معرفات المسؤولين
تُخزن في جدول `bot`:
```json
{
  "admins": [5420647695],
  "owners": [787700246, 204378180]
}
```

---

## 🧪 الاختبار

### اختبر الاتصال بقاعدة البيانات
```bash
php -r "
  \$conn = mysqli_connect('localhost', 'root', '', 'mr');
  echo mysqli_connect_error() ? 'Error: ' . mysqli_connect_error() : 'Connected!';
"
```

### اختبر API Telegram
```bash
curl -X GET \
  https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### اختبر Webhook
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":{"text":"/start","from":{"id":123}}}' \
  http://localhost:8000/xindex.php
```

---

## 🐛 حل المشاكل الشائعة

### "Connection refused" - فشل الاتصال بقاعدة البيانات
```bash
# تأكد من تشغيل MySQL
# Windows: من XAMPP Control Panel انقر Start بجانب MySQL
```

### "Invalid API_KEY"
```bash
# تحقق من صحة Token البوت
# أعد الحصول على Token من @BotFather
```

### البوت لا يرد على الرسائل
```bash
# تحقق من تسجيل Webhook أو استخدم Polling
# اطلع على TROUBLESHOOTING.md
```

### أحرف عربية غريبة
```bash
# تأكد من تفعيل UTF-8 في PHP و MySQL
```

**المزيد من الحلول:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📊 جداول قاعدة البيانات

| الجدول | الوصف |
|-------|-------|
| `bot` | إعدادات البوت والمفاتيح |
| `users` | بيانات المستخدمين |
| `states` | حالات المستخدمين |
| `photos` | الصور والملفات |
| `... وغيرها` | جداول إضافية |

---

## 🌐 الربط مع Telegram

### Webhook Method (للإنتاج)
```bash
# يجب أن يكون لديك HTTPS و domain عام
curl -X POST \
  https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d url=https://yourdomain.com/mobilerechargev2/xindex.php
```

### Polling Method (للاختبار المحلي)
أنشئ ملف `poll.php` يستقبل التحديثات بشكل دوري

**تفاصيل:** [SETUP_LOCAL_SERVER.md](SETUP_LOCAL_SERVER.md#ربط-البوت-مع-telegram)

---

## 📞 الدعم والمساعدة

### للبدء السريع
👉 اقرأ [QUICKSTART.md](QUICKSTART.md)

### للتثبيت المفصل
👉 اقرأ [SETUP_LOCAL_SERVER.md](SETUP_LOCAL_SERVER.md)

### للمشاكل التقنية
👉 اقرأ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### للمتطلبات والتثبيت
👉 اقرأ [REQUIREMENTS.md](REQUIREMENTS.md)

---

## 🔒 الأمان

### ميزات الأمان المدمجة
- ✅ التحقق من IP Telegram تلقائياً
- ✅ حماية من الهجمات
- ✅ تشفير البيانات
- ✅ سجل النشاط الكامل

### للإنتاج
- استخدم HTTPS إلزامياً
- حدّث كلمات المرور
- فعّل جدار الحماية
- احم حسابات المسؤولين

---

## 📈 الأداء

### الحد الأدنى
- PHP 7.4+
- MySQL 5.7+
- 512 MB RAM

### الموصى به
- PHP 8.0+
- MySQL 8.0+
- 2 GB RAM أو أكثر

---

## 📝 الملفات الهامة

```
mobilerechargev2/
├── 🎯 xindex.php              # نقطة الدخول الرئيسية
├── ⚙️  config.php              # الإعدادات الأساسية (عدّل هنا)
├── 🏗️  Control/main.class.php   # محرك البوت الرئيسي
└── 💾 mr.sql                  # البيانات الأولية
```

---

## 🎓 الموارد الإضافية

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [PHP Official Documentation](https://www.php.net/manual/)
- [MySQL Documentation](https://dev.mysql.com/doc/)

---

## 📄 الترخيص

هذا المشروع مرخص تحت MIT License

---

## 👨‍💻 المطور

تم تطوير هذا البوت بعناية لخدمة العملاء العراقيين بكفاءة وأمان

---

## ✅ قائمة التحقق قبل الإطلاق

- [ ] PHP 7.4+ مثبت
- [ ] MySQL مشغّل
- [ ] قاعدة البيانات mr تم استيرادها
- [ ] API_KEY تم تحديثه
- [ ] السرفر يعمل بدون أخطاء
- [ ] Webhook أو Polling مُعد
- [ ] اختبار الأوامر الأساسية نجح

---

## 📞 للتواصل والدعم

إذا واجهت أي مشكلة:
1. استخدم سكريبت `test.bat`
2. اقرأ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. تحقق من السجلات والأخطاء

---

**آخر تحديث:** January 15, 2026  
**الحالة:** ✅ جاهز للتشغيل على سرفر محلي  
**النسخة:** 2.0

---

### 🎉 نصيحة
لاستكشاف سريع للمشروع:
```bash
# شغّل سكريبت الفحص
setup.bat

# ثم شغّل الاختبارات
test.bat

# ثم ابدأ السرفر
cd "mobilerechargev2 2\mobilerechargev2"
php -S localhost:8000
```

**استمتع! 🚀**
