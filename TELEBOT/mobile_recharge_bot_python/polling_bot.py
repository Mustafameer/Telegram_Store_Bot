#!/usr/bin/env python
"""
بوت شحن الهاتف - بصيغة Polling
Mobile Recharge Bot - Polling Mode
"""
import os
import sys
import logging
import time
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# استيراد المتطلبات
from config import API_KEY, LOG_LEVEL
from telegram_api import TelegramAPI
from handlers import handle_message, handle_callback

# إعداد السجلات
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class PollingBot:
    def __init__(self):
        self.api = TelegramAPI(API_KEY)
        self.update_offset = 0
        self.running = True
        
    def start(self):
        """بدء البوت بصيغة polling"""
        logger.info("=" * 60)
        logger.info("🤖 بوت شحن الهاتف المحمول")
        logger.info("Mobile Recharge Bot - Polling Mode")
        logger.info("=" * 60)
        
        # حذف webhook القديم
        logger.info("🔄 جاري حذف webhook القديم...")
        self.api.delete_webhook()
        time.sleep(1)
        
        # الحصول على معلومات البوت
        me = self.api.get_me()
        if me:
            logger.info(f"✅ البوت: @{me.get('username', 'unknown')}")
            logger.info(f"✅ ID: {me.get('id')}")
        
        logger.info("=" * 60)
        logger.info("🚀 بدء الاستقبال...")
        logger.info("اضغط Ctrl+C للإيقاف / Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # حلقة الاستقبال
        while self.running:
            try:
                updates = self.api.get_updates(self.update_offset)
                
                if updates and isinstance(updates, list):
                    for update in updates:
                        self.process_update(update)
                        self.update_offset = update.get('update_id', 0) + 1
                
                time.sleep(0.5)  # تجنب overload
                
            except KeyboardInterrupt:
                logger.info("\n🛑 جاري إيقاف البوت...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"❌ خطأ: {e}")
                time.sleep(5)
    
    def process_update(self, update):
        """معالجة التحديث"""
        try:
            logger.info(f"📨 تحديث جديد: {update.get('update_id')}")
            
            # معالجة الرسائل
            if 'message' in update:
                handle_message(update['message'], update)
            
            # معالجة callback queries
            elif 'callback_query' in update:
                handle_callback(update['callback_query'], update)
                
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة التحديث: {e}")
    
    def stop(self):
        """إيقاف البوت"""
        self.running = False
        logger.info("✅ تم إيقاف البوت")


if __name__ == '__main__':
    bot = PollingBot()
    try:
        bot.start()
    except Exception as e:
        logger.error(f"❌ خطأ في البوت: {e}")
        sys.exit(1)
