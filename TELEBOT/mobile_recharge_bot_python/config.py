"""
إعدادات البيئة والبوت الرئيسية
Updated for Railway deployment
"""
import os
from datetime import timezone
from dotenv import load_dotenv

# تحميل متغيرات البيئة من .env
load_dotenv()

# Telegram Bot Configuration
API_KEY = os.getenv("TELEGRAM_API_KEY", "1127341833:AAHHpf_rrxrsr70g07Xxz4flDSPWcJZ4eEg")
BOT_ID = int(API_KEY.split(":")[0])
BOT_NAME = os.getenv("BOT_NAME", "Mobile Recharge Bot")

# Server Configuration (Railway)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook")

# Database Configuration (SQLite or PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_data.db")

# استخدام SQLite محلياً أو PostgreSQL على Railway
if DATABASE_URL.startswith("postgres"):
    DB_TYPE = "postgresql"
    DB_PATH = DATABASE_URL
else:
    DB_TYPE = "sqlite"
    DB_PATH = os.getenv("DB_PATH", "bot_data.db")

DB_TIMEOUT = 10

# Timezone
TIMEZONE = "Asia/Baghdad"

# Admin IDs (يمكن تحديثها من متغيرات البيئة)
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "5420647695").split(",")))
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "787700246,204378180").split(",")))  # قائمة معرفات المالكين

# Telegram IP Ranges (للتحقق من Telegram)
TELEGRAM_IP_RANGES = [
    ('149.154.160.0', '149.154.175.255'),
    ('91.108.4.0', '91.108.7.255')
]

# Available Companies
COMPANIES = {
    'asiacell': 'Asiacell (آسيا سيل)',
    'zain': 'Zain (زين)',
    'korek': 'Korek (كورك)',
    'iraqsell': 'Iraqsell (عراق سيل)',
    'alkafil': 'Alkafil (الكفيل)',
    'creditrequest': 'Credit Request (طلب رصيد)',
    'others': 'Others (أخرى)',
    'netzain': 'Net Zain (نت زين)',
    'netasiacell': 'Net Asiacell (نت آسيا)',
}

# Available Charges
CHARGES = [1, 2, 3, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 100, 250, 500]

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Features
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "True").lower() == "true"
CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", 300))  # 5 minutes

# Language (ar = Arabic ONLY, en = English)
# اللغة الافتراضية: عربي فقط
DEFAULT_LANGUAGE = 'ar'  # مثبت على العربية
SUPPORTED_LANGUAGES = ['ar']  # اللغة الوحيدة المدعومة

# API Endpoints
TELEGRAM_API_URL = "https://api.telegram.org/bot"
TELEGRAM_API_TIMEOUT = 30

# Maintenance Mode
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "False").lower() == "true"
MAINTENANCE_MESSAGE = "تحت الصيانة 🚫\n🚫 Under maintenance"

# Flask Configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
TESTING = os.getenv("TESTING", "False").lower() == "true"

# Railway specific
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "local")  # local, preview, production
IS_PRODUCTION = RAILWAY_ENVIRONMENT == "production"
