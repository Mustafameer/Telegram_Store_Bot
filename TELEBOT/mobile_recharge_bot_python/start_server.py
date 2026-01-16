#!/usr/bin/env python
"""
تشغيل السرفر المحلي مباشرة
Direct Local Server Startup
"""
import os
import sys
import logging

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# استيراد المتطلبات
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

from webhook import app
from config import HOST, PORT, LOG_LEVEL

# إعداد السجلات
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        # قراءة الإعدادات من البيئة
        port = int(os.getenv('PORT', PORT))
        host = os.getenv('HOST', HOST)
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        logger.info("=" * 60)
        logger.info("🤖 بوت شحن الهاتف المحمول")
        logger.info("Mobile Recharge Bot - Local Server")
        logger.info("=" * 60)
        logger.info(f"🌐 Server: http://{host}:{port}")
        logger.info(f"📍 Webhook: http://{host}:{port}/webhook")
        logger.info(f"💾 Database: bot_data.db (SQLite)")
        logger.info(f"🔧 Debug Mode: {debug}")
        logger.info("=" * 60)
        logger.info("اضغط Ctrl+C للإيقاف / Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # تشغيل التطبيق
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء السرفر: {str(e)}")
        logger.error(f"❌ Error starting server: {str(e)}")
        sys.exit(1)
