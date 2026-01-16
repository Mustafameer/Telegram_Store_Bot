# ⚡ البدء السريع - 5 خطوات

## 1️⃣ تحضير النظام
```bash
# تحقق من PHP
php -v

# تثبيت XAMPP إذا لم تكن مثبتة
# https://www.apachefriends.org/
```

## 2️⃣ تحضير قاعدة البيانات
```bash
# أنشئ قاعدة البيانات من phpMyAdmin
http://localhost/phpmyadmin

# استيراد ملف mr.sql
# أو من الـ terminal:
mysql -u root < mr.sql
```

## 3️⃣ تحديث الإعدادات
افتح `mobilerechargev2 2/mobilerechargev2/config.php` وغيّر:

```php
// من هذا:
define('API_KEY', "1127341833:AAHHpf_rrxrsr70g07Xxz4flDSPWcJZ4eEg");

// إلى Token البوت الصحيح:
define('API_KEY', "YOUR_BOT_TOKEN");
```

**للحصول على Token:**
- تحدث مع @BotFather
- أرسل `/newbot`
- انسخ الـ Token

## 4️⃣ شغّل السرفر

**الطريقة A - PHP Server (الأسهل):**
```bash
cd "mobilerechargev2 2\mobilerechargev2"
php -S localhost:8000
```

**الطريقة B - Apache (XAMPP):**
```bash
# انسخ المشروع إلى:
C:\xampp\htdocs\mobilerechargev2

# شغّل Apache من XAMPP Control Panel
# افتح: http://localhost/mobilerechargev2/
```

## 5️⃣ اختبر البوت

```bash
# الطريقة 1: أرسل رسالة إلى البوت على Telegram

# الطريقة 2: اختبر من Terminal
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":{"text":"/start","from":{"id":123}}}' \
  http://localhost:8000/xindex.php

# الطريقة 3: استخدم سكريبت الاختبار
test.bat
```

---

## 🎯 ملخص البوت

| الميزة | القيمة |
|--------|--------|
| **النوع** | بوت Telegram لشحن الهاتف |
| **اللغة** | PHP 7.4+ |
| **قاعدة البيانات** | MySQL 5.7+ |
| **العملات** | IQD (دينار عراقي) |
| **العملات المدعومة** | Asiacell, Zain, Korek, Iraqsell, Alkafil وغيرها |
| **الميزات** | إدارة المستخدمين، التقارير، الأرباح |

---

## 📁 الملفات المهمة

| الملف | الوصف |
|------|-------|
| `setup.bat` | سكريبت التثبيت والفحص |
| `test.bat` | سكريبت الاختبار الشامل |
| `SETUP_LOCAL_SERVER.md` | دليل التثبيت المفصل |
| `TROUBLESHOOTING.md` | حلول المشاكل الشائعة |
| `config.php` | الإعدادات والمفاتيح |

---

## ✅ قائمة التحقق

- [ ] PHP مثبت
- [ ] MySQL مشغّل
- [ ] قاعدة البيانات `mr` موجودة
- [ ] API_KEY محدّث
- [ ] السرفر يعمل بدون أخطاء
- [ ] البوت يستقبل الرسائل

---

## 🆘 مساعدة سريعة

| المشكلة | الحل |
|--------|------|
| PHP غير موجود | ثبّت XAMPP |
| MySQL لا يعمل | شغّل Apache/MySQL من XAMPP |
| خطأ في قاعدة البيانات | استيراد mr.sql |
| البوت لا يرد | تحديث API_KEY |
| أحرف عربية غريبة | تفعيل UTF-8 |

---

**استمتع بتشغيل البوت! 🚀**
