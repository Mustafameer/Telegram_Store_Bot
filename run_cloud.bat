@echo off
set PYTHONIOENCODING=utf-8
echo Starting Telegram Bot in Cloud Mode...
echo Connecting to Railway PostgreSQL...

set TELEGRAM_BOT_TOKEN=8562406465:AAEudEf_n6ZDnMlVy_UTwJ7eG1hBdDb1Tgw 
set DATABASE_URL=postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway

python %*
pause
