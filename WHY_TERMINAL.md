# ❓ لماذا يجب تشغيل البوت من Terminal؟

## 🔴 السبب:

البوت يستخدم **polling (استطلاع مستمر)**:
- يطلب تحديثات من Telegram باستمرار
- يتطلب عملية Python نشطة
- عند إغلاق Terminal → البوت يتوقف

---

## ✅ الحل (3 طرق):

### 1️⃣ **الأسرع** (بدون تشغيل تلقائي):
```
Double-click: run_bot_background.bat
```
- ✅ بسيط جداً
- ✅ بدون نافذة Terminal
- ⏱️ يعمل حتى تغلق النافذة

### 2️⃣ **الأفضل** (تشغيل تلقائي):
Task Scheduler:
1. اضغط: `Windows Key + R`
2. اكتب: `taskschd.msc`
3. انقر "Create Task"
4. Program: `python.exe`
5. Arguments: `bot.py`
6. Location: `C:\Users\Hp\Desktop\TelegramStoreBot`
7. Trigger: At Startup

- ✅ تشغيل تلقائي عند بدء Windows
- ✅ يعمل دائماً

### 3️⃣ **الأكثر استقراراً** (مع Auto-Restart):
```
Double-click: run_with_service_wrapper.bat
```
- ✅ إعادة تشغيل تلقائي عند التعطل
- ✅ Logging مفصل
- ✅ الأكثر أماناً

---

## 🎯 التوصية:

**للإنتاج:** استخدم **Task Scheduler** (الطريقة 2)
- الأفضل والأكثر موثوقية
- تشغيل تلقائي دائم

---

**للمزيد:** اقرأ [AUTORUN_GUIDE.md](AUTORUN_GUIDE.md)
