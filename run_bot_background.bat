@echo off
REM تشغيل البوت في الخلفية دون نافذة ظاهرة

cd /d "C:\Users\Hp\Desktop\TelegramStoreBot"

REM تشغيل pythonw بدلاً من python (بدون نافذة console)
pythonw.exe bot.py

REM إذا لم تعمل pythonw، استخدم هذه الطريقة البديلة:
REM python bot.py
