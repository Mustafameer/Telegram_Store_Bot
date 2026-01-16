"""
التعامل مع Telegram API
Telegram API Handler
"""
import requests
import json
import logging
from config import API_KEY, TELEGRAM_API_URL, TELEGRAM_API_TIMEOUT

logger = logging.getLogger(__name__)


class TelegramAPI:
    """فئة التعامل مع Telegram API"""
    
    def __init__(self, api_key=API_KEY):
        self.api_key = api_key
        self.base_url = f"{TELEGRAM_API_URL}{api_key}"
        self.timeout = TELEGRAM_API_TIMEOUT
    
    def _make_request(self, method, data=None, files=None):
        """إرسال طلب إلى Telegram API"""
        try:
            url = f"{self.base_url}/{method}"
            
            if files:
                # إرسال الملفات
                response = requests.post(
                    url,
                    data=data,
                    files=files,
                    timeout=self.timeout
                )
            else:
                # إرسال JSON
                response = requests.post(
                    url,
                    json=data,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get('ok'):
                logger.error(f"Telegram API Error: {result}")
                return None
            
            return result.get('result')
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def send_message(self, chat_id, text, parse_mode="HTML", 
                     reply_markup=None, disable_web_page_preview=False):
        """إرسال رسالة نصية"""
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        return self._make_request('sendMessage', data)
    
    def edit_message_text(self, chat_id, message_id, text, 
                         parse_mode="HTML", reply_markup=None):
        """تحرير نص رسالة"""
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        return self._make_request('editMessageText', data)
    
    def send_document(self, chat_id, document, caption=None):
        """إرسال ملف"""
        data = {
            'chat_id': chat_id,
            'caption': caption or ''
        }
        
        files = {'document': open(document, 'rb')}
        return self._make_request('sendDocument', data, files)
    
    def get_chat(self, chat_id):
        """الحصول على معلومات المحادثة"""
        data = {'chat_id': chat_id}
        return self._make_request('getChat', data)
    
    def get_me(self):
        """الحصول على معلومات البوت"""
        return self._make_request('getMe', {})
    
    def set_webhook(self, url, certificate=None, drop_pending_updates=True):
        """تعيين webhook"""
        data = {
            'url': url,
            'drop_pending_updates': drop_pending_updates
        }
        return self._make_request('setWebhook', data)
    
    def delete_webhook(self, drop_pending_updates=True):
        """حذف webhook"""
        data = {'drop_pending_updates': drop_pending_updates}
        return self._make_request('deleteWebhook', data)
    
    def get_webhook_info(self):
        """الحصول على معلومات webhook"""
        return self._make_request('getWebhookInfo', {})
    
    def answer_callback_query(self, callback_query_id, text=None, 
                             show_alert=False):
        """الرد على استعلام callback"""
        data = {
            'callback_query_id': callback_query_id,
            'text': text or '',
            'show_alert': show_alert
        }
        return self._make_request('answerCallbackQuery', data)
    
    def send_photo(self, chat_id, photo, caption=None, reply_markup=None):
        """إرسال صورة"""
        data = {
            'chat_id': chat_id,
            'caption': caption or ''
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        # إذا كان photo هو file_id
        if isinstance(photo, str) and not photo.startswith('http'):
            data['photo'] = photo
            return self._make_request('sendPhoto', data)
        else:
            # إذا كان file path أو URL
            files = {'photo': open(photo, 'rb') if not photo.startswith('http') else None}
            return self._make_request('sendPhoto', data, files)
    
    def get_updates(self, offset=None, limit=100):
        """الحصول على التحديثات (للـ polling)"""
        data = {
            'limit': limit,
            'allowed_updates': ['message', 'callback_query']
        }
        
        if offset:
            data['offset'] = offset
        
        return self._make_request('getUpdates', data)


# إنشاء instance عام
telegram_api = TelegramAPI()
