"""
نقطة الدخول الرئيسية للبوت
Main Entry Point for Railway Deployment
"""
import os
import logging
from webhook import app
from config import HOST, PORT, LOG_LEVEL

# إعداد السجلات
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # تشغيل التطبيق
    port = int(os.getenv('PORT', PORT))
    host = os.getenv('HOST', HOST)
    
    logger.info(f"Starting bot on {host}:{port}")
    logger.info("For production, use: gunicorn --bind 0.0.0.0:$PORT webhook:app")
    
    # في بيئة التطوير فقط
    app.run(host=host, port=port, debug=False)
