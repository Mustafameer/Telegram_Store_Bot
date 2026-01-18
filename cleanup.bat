@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

set DATABASE_URL=postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway

echo Deleting images, messages, and orders from database...
python cleanup_safe.py --auto

pause
