@echo off
REM Kill all Python processes
taskkill /F /IM python.exe 2>NUL
timeout /t 3 /nobreak

REM Navigate to bot directory and start the bot
cd /d "c:\Users\Hp\Desktop\TelegramStoreBot"
python bot.py
pause
