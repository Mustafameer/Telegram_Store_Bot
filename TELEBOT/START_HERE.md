## 📱 بوت شحن الهاتف المحمول

### ⚡ البدء السريع

```bash
# 1. تأكد من تثبيت PHP و MySQL
php -v
mysql -u root -v

# 2. استيراد قاعدة البيانات
mysql -u root < mr.sql

# 3. تحديث API_KEY في config.php

# 4. شغّل السرفر
cd "mobilerechargev2 2\mobilerechargev2"
php -S localhost:8000

# 5. افتح Telegram وابدأ!
```

---

### 📖 الأدلة والتوثيق

| الملف | المحتوى |
|------|---------|
| **[INDEX.md](INDEX.md)** | 🗺️ فهرس شامل وخريطة الملفات |
| **[README.md](README.md)** | 📘 نظرة عامة على المشروع |
| **[QUICKSTART.md](QUICKSTART.md)** | ⚡ البدء في 5 خطوات |
| **[SETUP_LOCAL_SERVER.md](SETUP_LOCAL_SERVER.md)** | 📖 شرح مفصل كامل |
| **[REQUIREMENTS.md](REQUIREMENTS.md)** | 📦 المتطلبات الكاملة |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | 🔧 حل المشاكل |
| **[COMMANDS_GUIDE.md](COMMANDS_GUIDE.md)** | 📚 دليل الأوامس |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | 🚀 النشر على الإنتاج |

---

### 🛠️ الأدوات والسكريبتات

```bash
# فحص المتطلبات والإعدادات
setup.bat

# اختبار شامل للبوت
test.bat
```

---

### 🎯 ابدأ من هنا

👉 **أولاً:** اقرأ [README.md](README.md) (5 دقائق)  
👉 **ثانياً:** اقرأ [QUICKSTART.md](QUICKSTART.md) (15 دقيقة)  
👉 **ثالثاً:** شغّل `setup.bat` و `test.bat`  
✅ **البوت جاهز!**

---

### 📁 هيكل المشروع

```
TELEBOT/
├── 📄 ملفات التوثيق (INDEX, README, QUICKSTART...)
├── 🛠️ أدوات (setup.bat, test.bat)
└── 📦 مجلد المشروع
    └── mobilerechargev2 2/mobilerechargev2/
        ├── config.php .................. (⚠️ عدّل هنا)
        ├── xindex.php ................. (معالج Webhook)
        ├── cronjob.php ................ (مهام دورية)
        ├── mr.sql ..................... (قاعدة البيانات)
        └── ... ملفات أخرى
```

---

### 🎮 الميزات الرئيسية

- 💰 شحن الهاتف بعملات عراقية
- 👥 إدارة متقدمة للمستخدمين
- 📊 نظام تقارير شامل
- 🔐 أمان قوي
- 🌍 دعم عربي كامل
- ⚡ أداء عالي

---

### 🚨 مشاكل شائعة؟

| المشكلة | الحل |
|--------|------|
| MySQL لا يعمل | شغّله من XAMPP Control Panel |
| API_KEY غير صحيح | احصل على Token جديد من @BotFather |
| البوت لا يرد | اقرأ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

---

### 📞 احتجت مساعدة؟

1. اقرأ [INDEX.md](INDEX.md) لخريطة الملفات
2. ابحث في [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. شغّل `test.bat` للتشخيص

---

### ✅ قائمة التحقق السريعة

- [ ] PHP 7.4+ مثبت
- [ ] MySQL يعمل
- [ ] قاعدة البيانات `mr` موجودة
- [ ] API_KEY محدّث
- [ ] السرفر يعمل بدون أخطاء

---

**آخر تحديث:** January 15, 2026  
**الحالة:** ✅ جاهز للتشغيل
