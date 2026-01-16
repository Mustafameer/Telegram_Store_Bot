# 🔍 جدول المراجعة السريعة

## 📋 جدول المحتويات السريع

### حسب الحاجة (ابحث هنا):

| الحاجة | الملف | الوقت |
|------|------|------|
| 🚀 **ابدأ بسرعة** | START_HERE.md | 5 دق |
| ⚡ **خطوات سريعة** | QUICKSTART.md | 15 دق |
| 📖 **دليل شامل** | SETUP_LOCAL_SERVER.md | 45 دق |
| 📚 **الأوامس كاملة** | COMMANDS_GUIDE.md | 30 دق |
| 🔧 **حل مشكلة** | TROUBLESHOOTING.md | 10-30 دق |
| 🚀 **نشر حقيقي** | DEPLOYMENT.md | 60 دق |
| 📦 **المتطلبات** | REQUIREMENTS.md | 15 دق |
| 🗺️ **الفهرس** | INDEX.md | 20 دق |
| ✅ **الملفات** | FILES_CREATED.md | 10 دق |

---

## 🎯 حسب الحالة

### "أريد تشغيل البوت الآن!"
```
1. اقرأ: START_HERE.md (5 دقائق)
2. شغّل: setup.bat (2 دقيقة)
3. شغّل: php -S localhost:8000 (5 دقائق)
═ الإجمالي: ~15 دقيقة
```

### "أريد فهماً أفضل"
```
1. اقرأ: README.md (10 دقائق)
2. اقرأ: SETUP_LOCAL_SERVER.md (45 دقيقة)
3. اقرأ: COMMANDS_GUIDE.md (30 دقيقة)
4. شغّل: test.bat (15 دقيقة)
═ الإجمالي: ~100 دقيقة
```

### "حدث لي خطأ"
```
1. اقرأ: TROUBLESHOOTING.md (ابحث عن المشكلة)
2. شغّل: test.bat (اختبر)
3. تحقق من: SETUP_LOCAL_SERVER.md (تفاصيل)
═ الإجمالي: متغير
```

### "أريد نشر البوت"
```
1. اقرأ: DEPLOYMENT.md (60 دقيقة)
2. اقرأ: TROUBLESHOOTING.md (15 دقيقة)
3. ثبّت: على الخادم الحقيقي (ساعة أو أكثر)
═ الإجمالي: 2+ ساعة
```

---

## 🔑 المفاتيح الأساسية

### ملف الإعدادات الرئيسي
```
📁 mobilerechargev2 2/mobilerechargev2/config.php
   ↓
   define('API_KEY', "YOUR_BOT_TOKEN");  ← عدّل هنا!
```

### قاعدة البيانات
```
📁 mr.sql (استيراد)
   ↓
   Database: mr
   User: root
   Password: (empty)
```

### معرفات مهمة
```
🔑 IDBot: 1127341833
🔑 Admins: [5420647695]
🔑 Owners: [787700246, 204378180]
```

---

## ⚡ الأوامس السريعة

### فحص وتشغيل
```bash
# فحص المتطلبات
setup.bat

# اختبار شامل
test.bat

# تشغيل السرفر
cd "mobilerechargev2 2\mobilerechargev2"
php -S localhost:8000
```

### اختبار الاتصالات
```bash
# تحقق من PHP
php -v

# تحقق من MySQL
mysql -u root -e "SELECT VERSION();"

# تحقق من MySQLi
php -r "echo extension_loaded('mysqli') ? 'OK' : 'Missing';"

# تحقق من cURL
php -r "echo extension_loaded('curl') ? 'OK' : 'Missing';"
```

---

## 🎯 أوامس البوت الرئيسية

### المستخدم
```
/start      - البدء
/request    - طلب شحن
/account    - الحساب
/history    - السجل
```

### المسؤول
```
/admin      - لوحة التحكم
/users      - قائمة المستخدمين
/stats      - الإحصائيات
/profit     - الأرباح
```

---

## 🐛 المشاكل الشائعة والحلول السريعة

### MySQL لا يعمل
```
✅ الحل: شغّل MySQL من XAMPP Control Panel
```

### "PHP غير موجود"
```
✅ الحل: ثبّت XAMPP أو أضف PHP إلى PATH
```

### "API_KEY غير صحيح"
```
✅ الحل: احصل على Token من @BotFather
```

### "لا يمكن الاتصال بـ DB"
```
✅ الحل: اقرأ TROUBLESHOOTING.md (المشكلة الأولى)
```

### "البوت لا يرد"
```
✅ الحل: اقرأ TROUBLESHOOTING.md (المشكلة الثانية)
```

---

## 📂 هيكل الملفات الأساسي

```
TELEBOT/
├── START_HERE.md ..................... ← ابدأ هنا!
├── README.md
├── QUICKSTART.md
├── SETUP_LOCAL_SERVER.md ............ ← الأهم
├── REQUIREMENTS.md
├── TROUBLESHOOTING.md
├── COMMANDS_GUIDE.md
├── DEPLOYMENT.md
├── INDEX.md
├── FILES_CREATED.md
├── setup.bat ......................... ← شغّل أولاً
├── test.bat .......................... ← ثم هذا
├── mr.sql
└── mobilerechargev2 2/
    └── mobilerechargev2/
        └── config.php ................ ← عدّل هنا!
```

---

## ✅ قائمة التحقق السريعة

```
□ قرأت START_HERE.md
□ شغّلت setup.bat بنجاح
□ حديّث API_KEY
□ استوردت قاعدة البيانات
□ MySQL يعمل بدون أخطاء
□ PHP -S localhost:8000 يعمل
□ اختبرت /start في Telegram
□ قرأت COMMANDS_GUIDE.md
□ اختبرت الأوامس الرئيسية
```

---

## 🌐 الروابط والأدوات

### Telegram
- 🤖 [BotFather](https://t.me/BotFather) - للحصول على Token

### التثبيت
- 🔧 [XAMPP](https://www.apachefriends.org/) - PHP + MySQL معاً
- 🐘 [PHP](https://www.php.net/downloads) - وحده
- 🐬 [MySQL](https://dev.mysql.com/downloads/) - وحده

### التطوير
- 📚 [PHP Docs](https://www.php.net/manual/)
- 🐬 [MySQL Docs](https://dev.mysql.com/doc/)
- 🤖 [Telegram API](https://core.telegram.org/bots/api)

---

## 🎓 خطوات التعلم

### الأسبوع الأول
- يوم 1: اقرأ START_HERE + QUICKSTART
- يوم 2-3: اتبع SETUP_LOCAL_SERVER
- يوم 4-5: شغّل واختبر البوت
- يوم 6-7: اقرأ COMMANDS_GUIDE

### الأسبوع الثاني
- اقرأ TROUBLESHOOTING
- أضف ميزات بسيطة
- اختبر جميع الأوامس
- افهم هيكل قاعدة البيانات

### الأسبوع الثالث+
- اقرأ DEPLOYMENT
- خطّط للإطلاق
- أضف ميزات متقدمة
- انشر على خادم حقيقي

---

## 💡 نصائح وحيل

### اقتصد الوقت
```
✓ استخدم setup.bat و test.bat للتشخيص السريع
✓ ابحث في TROUBLESHOOTING قبل محاولة إصلاح الأخطاء
✓ احفظ كل الملفات - قد تحتاجها لاحقاً
```

### تجنب الأخطاء
```
✓ اتبع الخطوات بالترتيب
✓ لا تتسرع في القراءة
✓ اختبر كل خطوة قبل المرور للتالية
✓ احفظ نسخة من البيانات
```

### تحسّن الأداء
```
✓ استخدم PHP 8+ للأداء الأفضل
✓ فعّل caching في قاعدة البيانات
✓ راقب استهلاك الموارد
```

---

## 📈 مستويات الصعوبة

| المستوى | الملفات | الوقت | المتطلبات |
|---------|--------|-------|-----------|
| 🟢 سهل | START_HERE, QUICKSTART | 20 دق | Windows فقط |
| 🟡 متوسط | SETUP, COMMANDS, TROUBLESHOOTING | 2 ساعة | PHP أساسي |
| 🔴 متقدم | DEPLOYMENT, كل الملفات | 5+ ساعات | PHP متقدم |

---

## 🚀 أسرع طريقة للبدء

```
1. اقرأ هذا الملف (2 دقيقة)
2. اقرأ START_HERE.md (5 دقائق)
3. شغّل setup.bat (2 دقيقة)
4. شغّل test.bat (5 دقائق)
5. شغّل السرفر (1 دقيقة)
6. جرّب البوت (5 دقائق)

═ المجموع: 20 دقيقة من البداية إلى النهاية!
```

---

## 🎯 الخطوات التالية

بعد البدء:
1. ✅ ثبّت البوت
2. ✅ شغّل الاختبارات
3. ✅ افهم الأوامس
4. ✅ أضف ميزات بسيطة
5. ✅ اختبر الأداء
6. ✅ انشر على الإنتاج

---

## 📞 عند الحاجة للمساعدة

```
1️⃣ ابحث في: TROUBLESHOOTING.md
2️⃣ شغّل: test.bat
3️⃣ اقرأ: SETUP_LOCAL_SERVER.md
4️⃣ تحقق من: السجلات والأخطاء
```

---

**آخر تحديث:** January 15, 2026  
**النسخة:** Quick Reference 2.0  
**الحالة:** ✅ جاهز للاستخدام الفوري
