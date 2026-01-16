# متطلبات تشغيل بوت شحن الهاتف المحمول

## 📦 المتطلبات الأساسية

### 1. **PHP 7.4 أو أحدث**
- تحميل: https://www.php.net/downloads
- أو استخدام XAMPP: https://www.apachefriends.org/

**للتحقق:**
```bash
php -v
```

**الإضافات المطلوبة:**
- ✅ MySQLi (للاتصال بقاعدة البيانات)
- ✅ cURL (لاتصال API Telegram)
- ✅ JSON (عادة مفعّل افتراضياً)

**للتحقق من الإضافات:**
```bash
php -m | find "mysqli"
php -m | find "curl"
```

---

### 2. **MySQL 5.7+ أو MariaDB 10.3+**
- MySQL: https://dev.mysql.com/downloads/
- MariaDB: https://mariadb.org/download/
- أو استخدام XAMPP (يأتي مع كليهما)

**للتحقق:**
```bash
mysql -u root -v
```

**الإعدادات:**
- المضيف: `localhost`
- المستخدم: `root`
- كلمة المرور: فارغة (افتراضياً)
- قاعدة البيانات: `mr` (يتم إنشاؤها من mr.sql)

---

### 3. **خادم ويب**
اختر واحداً من:

**الخيار A - Apache (XAMPP)**
- يأتي مع XAMPP
- الأسهل للمبتدئين
- يدعم .htaccess

**الخيار B - PHP Built-in Server**
```bash
php -S localhost:8000
```
- خفيف الوزن
- سريع للاختبار
- غير مناسب للإنتاج

**الخيار C - Nginx**
- أسرع من Apache
- يتطلب إعداد أكثر

---

## 🔧 التثبيت المسبق على Windows

### الطريقة 1: XAMPP (الموصى بها)

**خطوات:**
1. حمّل XAMPP من https://www.apachefriends.org/
2. ثبّتها بالمجلد الافتراضي `C:\xampp`
3. شغّل `xampp-control.exe`
4. ابدأ Apache و MySQL

**التحقق:**
- https://localhost/phpmyadmin

---

### الطريقة 2: أدوات منفصلة

**PHP:**
```bash
# حمّل من php.net
# ثبّتها في C:\php

# أضف إلى PATH:
setx PATH "%PATH%;C:\php"
```

**MySQL:**
```bash
# حمّل من dev.mysql.com
# ثبّتها وشغّلها كخدمة
```

---

## 📋 الملفات والمجلدات المطلوبة

```
mobilerechargev2/
├── config.php              ✓ مطلوب
├── xindex.php              ✓ مطلوب
├── cronjob.php             ✓ مطلوب
├── mr.sql                  ✓ مطلوب (لقاعدة البيانات)
├── numbers.json            ✓ مطلوب
├── Control/
│   └── main.class.php      ✓ مطلوب
├── Plugins/
│   ├── User/               ✓ مطلوب
│   ├── Owner/              ✓ مطلوب
│   └── Admin/              ✓ مطلوب
└── Languages/
    └── ar.php              ✓ مطلوب
```

---

## 🔑 المفاتيح والإعدادات

### API Telegram
- الحصول على Token من @BotFather
- مثال: `1234567890:ABCDefghijklmnopqrstuvwxyz`

### بيانات قاعدة البيانات
- المضيف: `localhost`
- المستخدم: `root`
- كلمة المرور: فارغة
- قاعدة البيانات: `mr`

### معرفات المسؤولين
- يتم تخزينها في جدول `bot`
- مثال: `[5420647695, 204378180]`

---

## 🌐 الاتصال بالإنترنت

### للاختبار المحلي
- غير مطلوب (Polling في وضع محلي)

### للإنتاج
- اتصال HTTPS إلزامي
- IP عام ثابت
- نطاق أو subdomain

---

## 💾 متطلبات التخزين

| العنصر | الحجم |
|--------|--------|
| مجلد المشروع | ~50 MB |
| قاعدة البيانات | متغير (عادة < 100 MB) |
| ملفات الصور | متغير |
| **المجموع** | ~500 MB (آمن) |

---

## 🔒 متطلبات الأمان

### للاختبار المحلي
- لا توجد متطلبات إضافية

### للإنتاج
- ✅ HTTPS مطلوب
- ✅ كلمات مرور قوية
- ✅ تحديث البرامج المنتظم
- ✅ نسخ احتياطية دورية
- ✅ جدار حماية

---

## ⚡ الأداء

### الحد الأدنى (اختبار)
- RAM: 512 MB
- CPU: أي معالج حديث
- الإنترنت: 1 Mbps

### الموصى به (إنتاج)
- RAM: 2 GB أو أكثر
- CPU: معالج ثنائي النواة أو أكثر
- الإنترنت: 10 Mbps أو أكثر

---

## 📦 الحزم والمكتبات

### مثبّتة مسبقاً
- PHPUnit (من Composer)
- PHP Codesniffer
- PHP Parallel Lint
- Prophecy (مكتبة اختبار)

### المطلوبة للتشغيل
- لا توجد متطلبات خارجية إضافية

---

## ✅ قائمة فحص قبل البدء

```bash
# 1. تحقق من PHP
php -v
# يجب أن تظهر النسخة 7.4 أو أحدث

# 2. تحقق من MySQLi
php -r "print_r(extension_loaded('mysqli') ? 'MySQLi: OK' : 'MySQLi: MISSING');"

# 3. تحقق من cURL
php -r "print_r(extension_loaded('curl') ? 'cURL: OK' : 'cURL: MISSING');"

# 4. تحقق من MySQL
mysql -u root -e "SELECT VERSION();"

# 5. تحقق من الملفات
dir mobilerechargev2
```

---

## 🔄 التحديثات

### PHP
```bash
# تحقق من التحديثات بانتظام
php -v

# للتحديث: أعد تثبيت من php.net
```

### MySQL
```bash
# تحقق من التحديثات
mysql -u root -e "SELECT VERSION();"
```

### البوت
```bash
# تحقق من التحديثات في GitHub/Repository
git pull
```

---

## 🆘 التشخيص

### سجل الأخطاء
```bash
# في XAMPP:
C:\xampp\apache\logs\error.log
C:\xampp\mysql\data\error.log

# في PHP:
php -i | find "error_log"
```

### اختبر بسرعة
```bash
# استخدم سكريبت الاختبار
test.bat
```

---

**آخر تحديث:** January 15, 2026
**الحالة:** ✅ جميع المتطلبات موثقة وجاهزة
