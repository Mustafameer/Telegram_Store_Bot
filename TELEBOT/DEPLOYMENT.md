# 🚀 نشر البوت على خادم إنتاجي

> هذا الدليل يشرح كيفية نشر بوت شحن الهاتف على خادم حقيقي (VPS, Dedicated Server, إلخ)

---

## 📋 الفرق بين الاختبار والإنتاج

| الميزة | اختبار محلي | خادم إنتاجي |
|--------|-----------|-----------|
| **HTTPS** | اختياري | ✅ مطلوب |
| **Domain** | localhost | example.com |
| **Webhook** | محاكاة | حقيقي |
| **الأداء** | غير مهم | ⚡ حرج |
| **الأمان** | أقل | 🔒 عالي جداً |
| **النسخ الاحتياطية** | اختياري | ✅ مطلوب |

---

## 🔧 خطوات النشر

### 1️⃣ تحضير الخادم

#### اختر نوع الخادم
```
📌 VPS (Virtual Private Server) - الخيار الأمثل
- Linode, DigitalOcean, AWS, Google Cloud
- السعر: $5-20 شهرياً
- الكنترول: كامل

📌 Dedicated Server - للأحمال الثقيلة
- السعر: $50+ شهرياً
- الأداء: الأفضل

📌 Hosting (cPanel) - الأسهل
- السعر: $5-15 شهرياً
- الكنترول: محدود
```

#### التثبيت على Ubuntu/Debian

**تحديث النظام:**
```bash
sudo apt update
sudo apt upgrade -y
```

**تثبيت Apache و PHP:**
```bash
sudo apt install apache2 php7.4 php7.4-mysqli php7.4-curl -y
sudo a2enmod rewrite
sudo systemctl restart apache2
```

**تثبيت MySQL:**
```bash
sudo apt install mysql-server -y
sudo mysql_secure_installation
```

---

### 2️⃣ إعداد النطاق (Domain)

#### اشتري نطاق (Domain)
```
من مواقع مثل:
- GoDaddy
- Namecheap
- Google Domains
```

#### اربط النطاق بالخادم
```
عيّن Name Servers إلى خادمك
أو أضف A Record يشير إلى IP الخادم
```

---

### 3️⃣ تفعيل HTTPS

#### استخدم Let's Encrypt (مجاني!)

```bash
# ثبّت Certbot
sudo apt install certbot python3-certbot-apache -y

# أصدر شهادة
sudo certbot certonly --apache -d yourdomain.com -d www.yourdomain.com

# فعّل التجديد التلقائي
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

#### أعدّ Apache للـ HTTPS
```bash
sudo a2enmod ssl
sudo a2enmod rewrite

# عدّل VirtualHost في:
sudo nano /etc/apache2/sites-available/yourdomain.com.conf
```

**مثال على VirtualHost:**
```apache
<VirtualHost *:443>
    ServerName yourdomain.com
    ServerAlias www.yourdomain.com
    
    DocumentRoot /var/www/yourdomain.com
    
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/yourdomain.com/privkey.pem
    
    <Directory /var/www/yourdomain.com>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>

# Redirect HTTP to HTTPS
<VirtualHost *:80>
    ServerName yourdomain.com
    ServerAlias www.yourdomain.com
    Redirect permanent / https://yourdomain.com/
</VirtualHost>
```

---

### 4️⃣ نشر المشروع

#### انسخ المجلد
```bash
sudo mkdir -p /var/www/yourdomain.com
sudo cp -r "mobilerechargev2 2/mobilerechargev2" /var/www/yourdomain.com/

# أعطِ الصلاحيات
sudo chown -R www-data:www-data /var/www/yourdomain.com
sudo chmod -R 755 /var/www/yourdomain.com
```

#### أعدّ قاعدة البيانات
```bash
# سجّل الدخول إلى MySQL
sudo mysql -u root -p

# أنشئ قاعدة البيانات والمستخدم:
CREATE DATABASE mr;
CREATE USER 'mrbot'@'localhost' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON mr.* TO 'mrbot'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# استيراد البيانات
mysql -u mrbot -p mr < /var/www/yourdomain.com/mr.sql
```

#### عدّل config.php
```bash
sudo nano /var/www/yourdomain.com/config.php
```

**الإعدادات الإنتاجية:**
```php
<?php
date_default_timezone_set("Asia/Baghdad");

// الإعدادات المعتادة
define('API_KEY', "YOUR_BOT_TOKEN");

// إعدادات قاعدة البيانات الإنتاجية
$Host = "localhost";
$UserName = "mrbot";
$PassWord = "secure_password_here";  // استخدم كلمة مرور قوية!
$DBName = "mr";

// تفعيل الأمان
error_reporting(0);  // أخفِ الأخطاء من المستخدمين
ini_set('display_errors', 0);

// إعدادات إضافية
define('BOT_NAME', 'Mobile Recharge Bot');
define('BOT_ADMIN', 204378180);
?>
```

---

### 5️⃣ إعداد Webhook

#### سجّل Webhook مع Telegram
```bash
curl -X POST \
  https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook \
  -d url=https://yourdomain.com/path/to/xindex.php \
  -d allowed_updates=["message","callback_query"]
```

#### تحقق من Webhook
```bash
curl -X GET \
  https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

**يجب أن تجد:**
```json
{
  "ok": true,
  "result": {
    "url": "https://yourdomain.com/path/to/xindex.php",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

### 6️⃣ المهام المجدولة (Cron Jobs)

#### شغّل Cron Job للتقارير اليومية
```bash
# افتح crontab
crontab -e

# أضف هذا السطر (يعمل كل يوم في الساعة الثانية صباحاً):
0 2 * * * /usr/bin/php /var/www/yourdomain.com/cronjob.php >> /tmp/cronjob.log 2>&1
```

#### مثال لأوقات مختلفة
```bash
# كل ساعة
0 * * * * /usr/bin/php /var/www/yourdomain.com/cronjob.php

# كل 6 ساعات
0 */6 * * * /usr/bin/php /var/www/yourdomain.com/cronjob.php

# كل يوم في الساعة 3 صباحاً
0 3 * * * /usr/bin/php /var/www/yourdomain.com/cronjob.php

# كل أحد في الساعة 1 ليلاً
0 1 * * 0 /usr/bin/php /var/www/yourdomain.com/cronjob.php
```

---

### 7️⃣ النسخ الاحتياطية

#### النسخ الاحتياطية اليومية لقاعدة البيانات
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/mr_bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mr_$DATE.sql"

mkdir -p $BACKUP_DIR

# أنشئ نسخة احتياطية
mysqldump -u mrbot -p'secure_password' mr > $BACKUP_FILE

# احذف النسخ القديمة (أكثر من 30 يوم)
find $BACKUP_DIR -name "mr_*.sql" -mtime +30 -delete

echo "Backup created: $BACKUP_FILE"
```

**أضفها إلى crontab:**
```bash
# كل يوم في الساعة 4 صباحاً
0 4 * * * /path/to/backup.sh >> /tmp/backup.log 2>&1
```

---

### 8️⃣ المراقبة والسجلات

#### تفعيل السجلات
```bash
# اتحقق من أخطاء Apache
sudo tail -f /var/log/apache2/error.log

# اتحقق من access logs
sudo tail -f /var/log/apache2/access.log

# اتحقق من MySQL
sudo tail -f /var/log/mysql/error.log
```

#### إنشاء ملف سجل للبوت
```bash
# أنشئ ملف سجل
sudo touch /var/log/mobilebot.log
sudo chmod 777 /var/log/mobilebot.log

# في config.php أضف:
define('LOG_FILE', '/var/log/mobilebot.log');

// في الأكواد المهمة:
error_log("Important message", 3, LOG_FILE);
```

---

## 🔒 الأمان على الخادم

### 1. جدار الحماية (Firewall)
```bash
# UFW (على Ubuntu)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 3306/tcp   # أغلق MySQL من الخارج
```

### 2. كلمات مرور قوية
```bash
# استخدم كلمات مرور قوية:
# - 16 حرف على الأقل
# - أحرف كبيرة وصغيرة
# - أرقام ورموز خاصة

# مثال: G8h$jK2#mL9qR5@nP3x
```

### 3. حماية config.php
```bash
# أضف في .htaccess
<Files "config.php">
    <IfModule mod_authz_core.c>
        Require all denied
    </IfModule>
</Files>
```

### 4. تعطيل directory listing
```bash
# في .htaccess
Options -Indexes
```

### 5. تحديث منتظم
```bash
sudo apt update && sudo apt upgrade -y
```

---

## 📊 مراقبة الأداء

### استخدام CPU و Memory
```bash
top
htop  # (أفضل)
```

### حجم قاعدة البيانات
```bash
mysql -u mrbot -p -e "SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb FROM information_schema.TABLES WHERE table_schema = 'mr';"
```

### سرعة الاستجابة
```bash
# اختبر من terminal آخر
ab -n 100 -c 10 https://yourdomain.com/xindex.php
```

---

## 🆘 حل المشاكل على الإنتاج

### البوت يرد بطء
```bash
# تحقق من الموارد
free -h
df -h

# أعد تشغيل Apache
sudo systemctl restart apache2

# أعد تشغيل MySQL
sudo systemctl restart mysql
```

### HTTPS لا يعمل
```bash
# تحقق من الشهادة
sudo certbot certificates

# تجديد يدوي
sudo certbot renew --dry-run

# تحقق من VirtualHost
sudo apache2ctl configtest
```

### قاعدة البيانات بطيئة
```sql
-- أضف indexes للجداول المهمة
ALTER TABLE users ADD INDEX (from_id);
ALTER TABLE users ADD INDEX (state);

-- تحقق من حجم النتائج
SELECT COUNT(*) FROM users;
```

---

## 📈 الترقيات المستقبلية

### زيادة الأداء
```
1. استخدم Redis للـ caching
2. أضف load balancer
3. استخدم CDN للملفات الثابتة
4. فعّل PHP opcode caching
```

### الميزات الجديدة
```
1. تطبيق mobile خاص
2. لوحة تحكم ويب متقدمة
3. نظام rewards/points
4. دعم العملات المتعددة
```

---

## 📞 الدعم والصيانة

### الفريق الموصى به
- **DevOps Engineer** - لإدارة الخادم
- **Database Admin** - لإدارة قاعدة البيانات
- **Security Expert** - للأمان والحماية

### Monitoring Tools
- **New Relic** - مراقبة الأداء
- **Sentry** - تتبع الأخطاء
- **DataDog** - إحصائيات شاملة

---

## ✅ قائمة التحقق قبل الإطلاق

- [ ] HTTPS فعّال ولديك شهادة صحيحة
- [ ] Database مستوردة وآمنة
- [ ] Webhook مسجّل مع Telegram
- [ ] Cron jobs مهيّأة
- [ ] النسخ الاحتياطية تعمل
- [ ] السجلات تتم مراقبتها
- [ ] جدار الحماية فعّال
- [ ] كلمات المرور قوية
- [ ] SSL/TLS محدّث
- [ ] الأداء مقبول

---

## 🎉 تم النشر بنجاح!

الآن بوتك يعمل 24/7 على خادم إنتاجي حقيقي!

---

**آخر تحديث:** January 15, 2026

### موارد إضافية
- [Apache Documentation](https://httpd.apache.org/docs/)
- [MySQL Performance Tuning](https://dev.mysql.com/doc/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Telegram Bot API Security](https://core.telegram.org/bots/api#getupdates)
