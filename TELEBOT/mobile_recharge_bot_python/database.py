"""
إدارة قاعدة البيانات
Database Management with SQLite
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from config import DB_PATH, DB_TIMEOUT
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """إدارة قاعدة البيانات بشكل آمن"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.timeout = DB_TIMEOUT
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال آمن بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """إنشاء الجداول الأساسية"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL DEFAULT 0,
                    status INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    report TEXT DEFAULT '{"asiacell":{},"zain":{},"korek":{},"iraqsell":{},"alkafil":{}}'
                )
            ''')
            
            # جدول الحالات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    state TEXT DEFAULT 'menu',
                    param TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # جدول الأسعار الفورية
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices_now (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    type TEXT NOT NULL,
                    charge_value REAL NOT NULL,
                    price REAL NOT NULL,
                    selected INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الأسعار المؤجلة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices_later (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    type TEXT NOT NULL,
                    charge_value REAL NOT NULL,
                    price REAL NOT NULL,
                    selected INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول العمليات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    company TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    amount REAL NOT NULL,
                    charge INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # جدول الصور
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    charge_value REAL NOT NULL,
                    photo_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول إعدادات البوت
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول السجل
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # ============ User Operations ============
    
    def get_user_by_id(self, from_id):
        """الحصول على مستخدم من معرف Telegram"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE from_id = ?', (from_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    
    def create_user(self, from_id, username, first_name, last_name):
        """إنشاء مستخدم جديد"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (from_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (from_id, username, first_name, last_name))
            return cursor.lastrowid
    
    def update_user(self, from_id, **kwargs):
        """تحديث بيانات المستخدم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [from_id]
            cursor.execute(f'UPDATE users SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE from_id = ?', values)
    
    def get_all_users(self):
        """الحصول على جميع المستخدمين"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ State Operations ============
    
    def get_user_state(self, user_id):
        """الحصول على حالة المستخدم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT state, param FROM states WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if result:
                return dict(result['state']), json.loads(result['param'])
            return None, {}
    
    def set_user_state(self, user_id, state, param=None):
        """تعيين حالة المستخدم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            param = json.dumps(param or {})
            cursor.execute('''
                INSERT INTO states (user_id, state, param)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                state=excluded.state, param=excluded.param
            ''', (user_id, state, param))
    
    def delete_user_state(self, user_id):
        """حذف حالة المستخدم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM states WHERE user_id = ?', (user_id,))
    
    # ============ Bot Settings Operations ============
    
    def get_setting(self, key):
        """الحصول على إعداد"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return json.loads(result['value']) if result else None
    
    def set_setting(self, key, value):
        """تعيين إعداد"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            value_json = json.dumps(value)
            cursor.execute('''
                INSERT INTO bot_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                value=excluded.value, updated_at=CURRENT_TIMESTAMP
            ''', (key, value_json))
    
    def get_all_settings(self):
        """الحصول على جميع الإعدادات"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM bot_settings')
            return {row['key']: json.loads(row['value']) for row in cursor.fetchall()}
    
    # ============ Transaction Operations ============
    
    def create_transaction(self, user_id, company, phone_number, amount, charge):
        """إنشاء عملية جديدة"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, company, phone_number, amount, charge)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, company, phone_number, amount, charge))
            return cursor.lastrowid
    
    def get_user_transactions(self, user_id, limit=10):
        """الحصول على عمليات المستخدم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM transactions WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ Logging Operations ============
    
    def log_action(self, user_id, action, details=None):
        """تسجيل إجراء"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, json.dumps(details) if details else None))
    
    def get_logs(self, limit=100, user_id=None):
        """الحصول على السجلات"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute('''
                    SELECT * FROM logs WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]


# إنشاء instance عام
db = DatabaseManager()
