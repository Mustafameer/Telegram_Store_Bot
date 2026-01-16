"""
الفئة الرئيسية للبوت
Main Bot Class
"""
import logging
import json
from datetime import datetime
from config import (
    API_KEY, BOT_ID, MAINTENANCE_MODE, ADMIN_IDS, 
    OWNER_IDS, COMPANIES, CHARGES, TELEGRAM_IP_RANGES
)
from database import db
from telegram_api import telegram_api
from languages import get_text

logger = logging.getLogger(__name__)


class MobileRechargeBot:
    """فئة البوت الرئيسية"""
    
    def __init__(self):
        self.api = telegram_api
        self.db = db
    
    # ============ Utility Methods ============
    
    def is_telegram_ip(self, ip):
        """التحقق من أن IP تابع لـ Telegram"""
        for start, end in TELEGRAM_IP_RANGES:
            start_int = self._ip_to_int(start)
            end_int = self._ip_to_int(end)
            ip_int = self._ip_to_int(ip)
            
            if start_int <= ip_int <= end_int:
                return True
        
        return False
    
    @staticmethod
    def _ip_to_int(ip):
        """تحويل IP إلى رقم صحيح"""
        parts = ip.split('.')
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + \
               (int(parts[2]) << 8) + int(parts[3])
    
    def is_admin(self, user_id):
        """التحقق من أن المستخدم مسؤول"""
        return user_id in ADMIN_IDS
    
    def is_owner(self, user_id):
        """التحقق من أن المستخدم مالك"""
        return user_id in OWNER_IDS
    
    def is_authorized(self, user_id):
        """التحقق من تفويض المستخدم"""
        return self.is_admin(user_id) or self.is_owner(user_id)
    
    # ============ User Management ============
    
    def get_or_create_user(self, update_data):
        """الحصول على أو إنشاء مستخدم"""
        from_id = update_data['from']['id']
        username = update_data['from'].get('username', '')
        first_name = update_data['from'].get('first_name', '')
        last_name = update_data['from'].get('last_name', '')
        
        user = self.db.get_user_by_id(from_id)
        
        if not user:
            user_id = self.db.create_user(from_id, username, first_name, last_name)
            user = self.db.get_user_by_id(from_id)
            logger.info(f"Created new user: {from_id}")
            # فرض اللغة العربية للمستخدمين الجدد
            self.set_user_language(from_id, 'ar')
        
        return user
    
    def set_user_language(self, user_id, language='ar'):
        """تعيين لغة المستخدم (دائماً عربي)"""
        self.db.set_setting(f"lang_{user_id}", 'ar')
        return 'ar'
    
    def get_user_language(self, user_id):
        """الحصول على لغة المستخدم"""
        lang = self.db.get_setting(f"lang_{user_id}")
        return lang if lang in ['ar', 'en'] else 'ar'
    
    def get_user_display_name(self, user_data):
        """الحصول على اسم عرض المستخدم"""
        if isinstance(user_data, dict):
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
        else:
            first_name = user_data.first_name
            last_name = user_data.last_name
        
        name = f"{first_name} {last_name}".strip()
        return name or str(user_data.get('from_id') or user_data.from_id)
    
    # ============ Message Sending ============
    
    def send_message(self, chat_id, text, **kwargs):
        """إرسال رسالة"""
        return self.api.send_message(chat_id, text, **kwargs)
    
    def edit_message(self, chat_id, message_id, text, **kwargs):
        """تحرير رسالة"""
        return self.api.edit_message_text(chat_id, message_id, text, **kwargs)
    
    def answer_callback(self, callback_query_id, text=None, show_alert=False):
        """الرد على callback"""
        return self.api.answer_callback_query(
            callback_query_id, text, show_alert
        )
    
    # ============ Keyboard Building ============
    
    @staticmethod
    def build_inline_keyboard(buttons):
        """بناء لوحة مفاتيح inline
        
        Args:
            buttons: قائمة من الأزرار
                    [{'text': 'Text', 'callback_data': 'data'}, ...]
        
        Returns:
            dict: لوحة المفاتيح
        """
        return {
            'inline_keyboard': [[button] for button in buttons]
        }
    
    @staticmethod
    def build_row_keyboard(buttons, cols=2):
        """بناء لوحة مفاتيح بصفوف
        
        Args:
            buttons: قائمة من الأزرار
            cols: عدد الأعمدة
        """
        rows = []
        for i in range(0, len(buttons), cols):
            rows.append(buttons[i:i+cols])
        
        return {'inline_keyboard': rows}
    
    # ============ Company & Price Management ============
    
    def get_companies(self):
        """الحصول على قائمة الشركات"""
        return list(COMPANIES.keys())
    
    def get_company_name(self, company_code):
        """الحصول على اسم الشركة"""
        return COMPANIES.get(company_code, company_code)
    
    def get_charges(self):
        """الحصول على قائمة المبالغ"""
        return CHARGES
    
    # ============ State Management ============
    
    def get_user_state(self, user_id):
        """الحصول على حالة المستخدم"""
        return self.db.get_user_state(user_id)
    
    def set_user_state(self, user_id, state, param=None):
        """تعيين حالة المستخدم"""
        self.db.set_user_state(user_id, state, param)
    
    def clear_user_state(self, user_id):
        """حذف حالة المستخدم"""
        self.db.delete_user_state(user_id)
    
    # ============ Settings Management ============
    
    def get_setting(self, key):
        """الحصول على إعداد"""
        return self.db.get_setting(key)
    
    def set_setting(self, key, value):
        """تعيين إعداد"""
        self.db.set_setting(key, value)
    
    def get_bot_status(self):
        """الحصول على حالة البوت"""
        status = self.get_setting('status')
        return status or {'ok': True}
    
    def get_owners(self):
        """الحصول على قائمة المالكين"""
        owners = self.get_setting('owners')
        return owners or OWNER_IDS
    
    def get_admins(self):
        """الحصول على قائمة المسؤولين"""
        admins = self.get_setting('admins')
        return admins or ADMIN_IDS
    
    def get_profit(self):
        """الحصول على الأرباح"""
        profit = self.get_setting('profit')
        if not profit:
            profit = {comp: 0 for comp in COMPANIES.keys()}
            self.set_setting('profit', profit)
        return profit
    
    # ============ Transaction Management ============
    
    def create_transaction(self, user_id, company, phone, charge):
        """إنشاء عملية"""
        return self.db.create_transaction(
            user_id, company, phone, charge, 0
        )
    
    def get_user_transactions(self, user_id, limit=10):
        """الحصول على عمليات المستخدم"""
        return self.db.get_user_transactions(user_id, limit)
    
    # ============ Logging ============
    
    def log_action(self, user_id, action, details=None):
        """تسجيل إجراء"""
        self.db.log_action(user_id, action, details)
    
    def get_logs(self, limit=100, user_id=None):
        """الحصول على السجلات"""
        return self.db.get_logs(limit, user_id)
    
    # ============ Helpers ============
    
    def get_text(self, key, language='ar', *args):
        """الحصول على نص مترجم"""
        return get_text(key, language, *args)


# إنشاء instance عام
bot = MobileRechargeBot()
