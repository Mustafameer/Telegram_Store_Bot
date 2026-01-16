## 🚨 المشاكل الشائعة والحلول

### ❌ المشكلة: "Call to undefined function mysqli_query()"

**السبب:** MySQLi لم يتم تفعيله في PHP

**الحل:**
1. افتح `php.ini` (عادة في `C:\xampp\php\php.ini`)
2. ابحث عن السطر: `;extension=mysqli`
3. احذف الفاصلة من البداية: `extension=mysqli`
4. احفظ الملف وأعد تشغيل Apache

```ini
# قبل:
;extension=mysqli

# بعد:
extension=mysqli
```

---

### ❌ المشكلة: "Connection refused - Access denied for user 'root'@'localhost'"

**السبب:** MySQL غير مشغّل أو كلمة المرور خاطئة

**الحل:**
```bash
# تأكد من تشغيل MySQL
# من XAMPP: انقر على START بجانب MySQL

# أو من سطر الأوامر:
net start mysql80  # أو اسم خدمة MySQL

# اختبر الاتصال:
mysql -u root
```

إذا كانت لديك كلمة مرور:
```php
// في config.php
$PassWord = 'your_password';
```

---

### ❌ المشكلة: "Database 'mr' doesn't exist"

**السبب:** لم يتم استيراد ملف SQL

**الحل:**
1. افتح phpMyAdmin: http://localhost/phpmyadmin
2. انقر على "استيراد" (Import)
3. اختر ملف `mr.sql` من المشروع
4. انقر "استيراد"

**أو من سطر الأوامر:**
```bash
mysql -u root < mr.sql
```

---

### ❌ المشكلة: "Invalid API_KEY"

**السبب:** Token البوت غير صحيح

**الحل:**
1. تحدث مع @BotFather على Telegram
2. أرسل `/token` واختر البوت
3. نسّخ الـ Token
4. ضعه في `config.php`:

```php
define('API_KEY', "PASTE_YOUR_TOKEN_HERE");
```

**للتحقق:**
```bash
php -r "
require_once 'mobilerechargev2 2/mobilerechargev2/config.php';
echo 'API_KEY: ' . API_KEY . PHP_EOL;
"
```

---

### ❌ المشكلة: "Permission denied" عند تشغيل الملفات

**السبب:** مشاكل في أذونات الملفات

**الحل (Windows):**
```bash
# لا عادة ما تكون هناك مشكلة على Windows
# لكن تأكد من أن المجلد ليس محمياً

# إذا كان محمياً:
icacls "C:\xampp\htdocs\mobilerechargev2" /grant Everyone:(OI)(CI)F /T
```

---

### ❌ المشكلة: البوت لا يستقبل الرسائل

**السبب:** Webhook غير مسجّل أو URL غير صحيح

**الحل:**

**الخيار 1 - Webhook (للإنتاج):**
```bash
# يجب أن يكون المشروع متاحاً على HTTPS
curl -X POST \
  https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d url=https://yourdomain.com/mobilerechargev2/xindex.php
```

**الخيار 2 - Polling (للاختبار المحلي):**

أنشئ ملف `poll.php`:
```php
<?php
require_once 'mobilerechargev2 2/mobilerechargev2/config.php';
require_once 'mobilerechargev2 2/mobilerechargev2/Control/main.class.php';

$BOT = new Main(API_KEY);
$offset = 0;

while(true) {
    $updates = json_decode($BOT->sendCommand('getUpdates?offset=' . $offset), true);
    
    foreach($updates['result'] as $update) {
        $offset = $update['update_id'] + 1;
        
        // معالجة التحديث
        $_SERVER['HTTP_CF_CONNECTING_IP'] = '149.154.160.1'; // محاكاة IP Telegram
        $_POST = json_encode($update);
        
        include 'mobilerechargev2 2/mobilerechargev2/xindex.php';
    }
    
    sleep(1);
}
```

ثم شغّله:
```bash
php poll.php
```

---

### ❌ المشكلة: "cURL Error" عند الاتصال بـ Telegram

**السبب:** cURL لم يتم تفعيله

**الحل:**
1. افتح `php.ini`
2. ابحث عن: `;extension=curl`
3. احذف الفاصلة: `extension=curl`
4. أعد تشغيل Apache

```ini
# قبل:
;extension=curl

# بعد:
extension=curl
```

---

### ❌ المشكلة: "White blank page" عند فتح الموقع

**السبب:** خطأ في PHP لكن لم يتم عرضه

**الحل:**
1. افتح `php.ini`
2. غيّر: `display_errors = On`
3. غيّر: `error_reporting = E_ALL`

```ini
display_errors = On
error_reporting = E_ALL
```

أو أضف هذا في بداية `config.php`:
```php
ini_set('display_errors', 1);
error_reporting(E_ALL);
```

---

### ❌ المشكلة: "Access denied" من Telegram

**السبب:** IP الخادم ليس معروفاً لـ Telegram

**الحل:**

الكود يتحقق من IP Telegram تلقائياً، لكن إذا أردت اختبار محلي:

```php
// في xindex.php - أضف هذا في البداية:
if (is_telegram() === false) {
    // للاختبار فقط - احذفها لاحقاً!
    $_SERVER['HTTP_CF_CONNECTING_IP'] = '149.154.160.1';
}
```

---

### ❌ المشكلة: الأحرف العربية تظهر بشكل خاطئ

**السبب:** تشفير غير صحيح

**الحل:**

تأكد من أن `config.php` يحتوي على:
```php
mysqli_query($db, "SET NAMES utf8");
mysqli_query($db, "SET CHARACTER SET utf8");
```

وأن رأس الصفحة يحتوي على:
```php
header('Content-Type: application/json; charset=utf-8');
```

---

## 🔍 اختبار سريع

**اختبر البوت بهذا الأمر:**

```bash
# افتح terminal في مجلد المشروع وشغّل:
php -S localhost:8000

# ثم من terminal آخر:
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "text": "/start",
      "from": {"id": 123, "first_name": "Test"},
      "chat": {"id": 123, "type": "private"}
    }
  }' \
  http://localhost:8000/xindex.php
```

---

## 📞 التواصل مع الدعم

إذا واجهت مشاكل:
1. تحقق من رسائل الخطأ في `php error_log`
2. شغّل سكريبت `test.bat` لاختبار شامل
3. تحقق من معلومات الاتصال في `config.php`

---

**آخر تحديث:** January 15, 2026
