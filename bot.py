import telebot
from telebot import types
import sqlite3
import os
import time
import uuid
import traceback
from datetime import datetime
import base64

# ----------------- إعداد البوت وملفات -----------------
import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ FATAL ERROR: TELEGRAM_BOT_TOKEN environment variable is NOT set! Using default token.")
    TOKEN = "8562406465:AAHHaUMALVMjfgVKlAYNh8nziTwIeg5GDCs" # Fallback to default
else:
    print(f"✅ DEBUG: TELEGRAM_BOT_TOKEN found. Starts with: {TOKEN[:10]}... Ends with: ...{TOKEN[-5:]}")
    print(f"✅ DEBUG: Token Length: {len(TOKEN)}")
bot = telebot.TeleBot(TOKEN)
IS_POSTGRES = os.environ.get('DATABASE_URL') is not None

# إضافة معرف صاحب البوت (أدمن) - للتحكم التقني فقط
BOT_ADMIN_ID = 1041977029  # ضع هنا معرف التليجرام الخاص بأدمن البوت

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed_data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "store.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# ----------------- استعادة البيانات عند إضافة Volume جديد -----------------
import shutil
import psycopg2
import urllib.parse
from contextlib import contextmanager

# ===================== Database Wrapper =====================
class DBWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        return CursorWrapper(self.conn.cursor(), self.is_postgres)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

class CursorWrapper:
    def __init__(self, cursor, is_postgres=False):
        self.cursor = cursor
        self.is_postgres = is_postgres
        self.lastrowid = None # Placeholder

    def execute(self, query, params=None):
        if self.is_postgres:
            # Replace ? with %s
            query = query.replace('?', '%s')
            # Handle AUTOINCREMENT replacement for Postgres compatibility
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            query = query.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            query = query.replace('DATETIME', 'TIMESTAMP')
        
        try:
            if params is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, params)
                
            # Try to capture lastrowid if supported
            if not self.is_postgres:
                self.lastrowid = self.cursor.lastrowid
            else:
                # Psycopg2: lastrowid is often OID, not PK. 
                # If RETURNING was used, we need to fetchone to get it.
                if query.strip().upper().startswith("INSERT") and "RETURNING" in query.upper():
                    res = self.cursor.fetchone()
                    if res:
                        self.lastrowid = res[0]
        except Exception as e:
            raise e
            
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()
        
    def close(self):
        self.cursor.close()

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            # NUCLEAR OPTION: If we are supposed to use Postgres, KILL the local DB to prevent confusion
            if os.path.exists(DB_FILE):
                print("⚠️ FOUND LOCAL DB IN CLOUD MODE - DELETING IT TO FORCE POSTGRES ⚠️")
                try:
                    os.remove(DB_FILE)
                except:
                    pass

            result = urllib.parse.urlparse(database_url)
            username = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port
            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                port=port
            )
            return DBWrapper(conn, is_postgres=True)
        except Exception as e:
            print(f"❌ CRITICAL ERROR connecting to Postgres: {e}")
            # DO NOT FALLBACK TO SQLITE. FAIL LOUDLY.
            raise e
    else:
        # Local development mode (no DATABASE_URL)
        return DBWrapper(sqlite3.connect(DB_FILE), is_postgres=False)

# Remove the restore logic entirely or guard it carefully
if not os.path.exists(DB_FILE) and os.path.exists(os.path.join(SEED_DIR, "store.db")) and not os.environ.get('DATABASE_URL'):
    print("🔄 استعادة قاعدة البيانات من النسخة الاحتياطية (Seed)...")
    shutil.copy(os.path.join(SEED_DIR, "store.db"), DB_FILE)
    if os.path.exists(os.path.join(SEED_DIR, "Images")):
         if os.path.exists(IMAGES_FOLDER):
             shutil.rmtree(IMAGES_FOLDER)
         shutil.copytree(os.path.join(SEED_DIR, "Images"), IMAGES_FOLDER)
    print("✅ تم استعادة البيانات بنجاح!")

# ===================== قاعدة البيانات =====================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # جدول الزبائن الآجل (الاسم، رقم التلفون)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CreditCustomers(
            CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            FullName TEXT NOT NULL,
            PhoneNumber TEXT,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(SellerID, PhoneNumber),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # جدول جديد: حدود الائتمان
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CreditLimits (
            LimitID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            MaxCreditAmount REAL DEFAULT 1000000,
            WarningThreshold REAL DEFAULT 0.8,
            CurrentUsedAmount REAL DEFAULT 0,
            IsActive BOOLEAN DEFAULT 1,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID),
            UNIQUE(CustomerID, SellerID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users(
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            TelegramID INTEGER UNIQUE,
            UserName TEXT,
            UserType TEXT,
            PhoneNumber TEXT,
            FullName TEXT,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Sellers(
            SellerID INTEGER PRIMARY KEY AUTOINCREMENT,
            TelegramID INTEGER UNIQUE,
            UserName TEXT,
            StoreName TEXT,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            Status TEXT DEFAULT 'active',
            SuspensionReason TEXT,
            SuspendedBy INTEGER,
            SuspendedAt DATETIME,
            FOREIGN KEY (SuspendedBy) REFERENCES Users(TelegramID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CustomerCredit(
            CreditID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            TransactionType TEXT,
            Amount REAL,
            Description TEXT,
            BalanceBefore REAL,
            BalanceAfter REAL,
            TransactionDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories(
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            Name TEXT,
            OrderIndex INTEGER DEFAULT 0,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Products(
            ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            CategoryID INTEGER,
            Name TEXT,
            Description TEXT,
            Price REAL,
            WholesalePrice REAL,
            Quantity INTEGER,
            ImagePath TEXT,
            Status TEXT DEFAULT 'active',
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID),
            FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Carts(
            CartID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER,
            ProductID INTEGER,
            Quantity INTEGER,
            Price REAL,
            AddedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(UserID, ProductID),
            FOREIGN KEY (UserID) REFERENCES Users(TelegramID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Orders(
            OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
            BuyerID INTEGER,
            SellerID INTEGER,
            Total REAL,
            Status TEXT DEFAULT 'Pending',
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            DeliveryAddress TEXT,
            Notes TEXT,
            PaymentMethod TEXT DEFAULT 'cash',
            FullyPaid BOOLEAN DEFAULT 0,
            FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS OrderItems(
            OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            ProductID INTEGER,
            Quantity INTEGER,
            Price REAL,
            ReturnedQuantity INTEGER DEFAULT 0,
            ReturnReason TEXT,
            ReturnDate DATETIME,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Returns(
            ReturnID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            ProductID INTEGER,
            Quantity INTEGER,
            Reason TEXT,
            Status TEXT DEFAULT 'Pending',
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            ProcessedBy INTEGER,
            ProcessedAt DATETIME,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
            FOREIGN KEY (ProcessedBy) REFERENCES Users(TelegramID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messages(
            MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            SellerID INTEGER,
            MessageType TEXT,
            MessageText TEXT,
            IsRead BOOLEAN DEFAULT 0,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    conn.commit()
    conn.close()

init_db()

def check_and_fix_db():
    """التحقق من وجود جميع الجداول وإصلاح النواقص"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tables = ['CreditCustomers', 'CreditLimits', 'Users', 'Sellers', 'CustomerCredit', 'Categories', 'Products', 
              'Carts', 'Orders', 'OrderItems', 'Returns', 'Messages']
    
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"⚠️ جدول {table} غير موجود، سيتم إنشاؤه في المرة القادمة")
    
    conn.close()

check_and_fix_db()

# ===================== نظام حدود الائتمان =====================

def check_credit_limit(customer_id, seller_id, new_amount):
    """التحقق إذا كان يمكن للزبون تحمل مبلغ جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الحد الحالي
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount 
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive=1
    """, (customer_id, seller_id))
    
    limit_data = cursor.fetchone()
    
    if not limit_data:
        # إذا لم يكن للزبون حد محدد، نعود لقيمة افتراضية كبيرة
        conn.close()
        return True, "لا يوجد حد ائتماني محدد", 0, 0, 0
    
    max_limit, current_used = limit_data
    
    # حساب المبلغ الجديد الكلي
    new_total = current_used + new_amount
    
    if new_total > max_limit:
        remaining = max_limit - current_used
        conn.close()
        return False, f"❌ تجاوز الحد الائتماني! الحد الأقصى: {max_limit:,.0f} دينار، المستخدم: {current_used:,.0f} دينار، المتبقي: {remaining:,.0f} دينار", max_limit, current_used, remaining
    
    # التحقق من عتبة التحذير
    warning_percentage = current_used / max_limit if max_limit > 0 else 0
    
    if warning_percentage >= 0.8:
        conn.close()
        return True, f"⚠️ تحذير: وصلت إلى {warning_percentage*100:.0f}% من حدك الائتماني", max_limit, current_used, max_limit - current_used
    
    conn.close()
    return True, f"✅ الحد الائتماني مناسب. المتبقي: {max_limit - current_used:,.0f} دينار", max_limit, current_used, max_limit - current_used

def update_credit_usage(customer_id, seller_id, amount, transaction_type):
    """تحديث المبلغ المستخدم من الحد الائتماني"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الحد الحالي أو إنشاء واحد جديد
    cursor.execute("""
        SELECT CurrentUsedAmount FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive=1
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    
    if result:
        current_used = result[0]
        
        if transaction_type == 'purchase':
            new_used = current_used + amount
        elif transaction_type == 'payment':
            new_used = current_used - amount
            if new_used < 0:
                new_used = 0
        else:
            new_used = current_used
        
        cursor.execute("""
            UPDATE CreditLimits 
            SET CurrentUsedAmount=?, UpdatedAt=CURRENT_TIMESTAMP
            WHERE CustomerID=? AND SellerID=? AND IsActive=1
        """, (new_used, customer_id, seller_id))
    else:
        # إنشاء سجل جديد
        if transaction_type == 'purchase':
            current_used = amount
        else:
            current_used = 0
        
        cursor.execute("""
            INSERT INTO CreditLimits 
            (CustomerID, SellerID, MaxCreditAmount, CurrentUsedAmount, IsActive)
            VALUES (?, ?, 1000000, ?, 1)
        """, (customer_id, seller_id, current_used))
    
    conn.commit()
    conn.close()
    return True

def set_credit_limit(customer_id, seller_id, max_amount, warning_percentage=0.8):
    """تعيين حد ائتماني للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على المبلغ المستخدم الحالي
    cursor.execute("""
        SELECT CurrentUsedAmount FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    current_used = result[0] if result else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO CreditLimits 
        (CustomerID, SellerID, MaxCreditAmount, WarningThreshold, CurrentUsedAmount, IsActive)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (customer_id, seller_id, max_amount, warning_percentage, current_used))
    
    conn.commit()
    conn.close()
    return True

def get_credit_limit_info(customer_id, seller_id):
    """الحصول على معلومات الحد الائتماني"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount, WarningThreshold,
               CASE 
                   WHEN CurrentUsedAmount >= MaxCreditAmount THEN '❌ ممتلئ'
                   WHEN CurrentUsedAmount >= MaxCreditAmount * WarningThreshold THEN '⚠️ تحذير'
                   ELSE '✅ متاح'
               END as Status,
               MaxCreditAmount - CurrentUsedAmount as Available
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive=1
    """, (customer_id, seller_id))
    
    info = cursor.fetchone()
    conn.close()
    
    if info:
        return {
            'max_limit': info[0],
            'current_used': info[1],
            'warning_threshold': info[2],
            'status': info[3],
            'available': info[4]
        }
    else:
        return {
            'max_limit': 1000000,
            'current_used': 0,
            'warning_threshold': 0.8,
            'status': '✅ غير محدد',
            'available': 1000000
        }

def reset_credit_usage(customer_id, seller_id):
    """إعادة تعيين المبلغ المستخدم للصفر"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE CreditLimits 
        SET CurrentUsedAmount=0, UpdatedAt=CURRENT_TIMESTAMP
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    conn.commit()
    conn.close()
    return True

def deactivate_credit_limit(customer_id, seller_id):
    """تعطيل الحد الائتماني للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE CreditLimits 
        SET IsActive=0, UpdatedAt=CURRENT_TIMESTAMP
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    conn.commit()
    conn.close()
    return True

# ===================== دوال إدارة الحسابات =====================
def suspend_seller(seller_id, suspended_by, reason=None):
    """تعليق حساب بائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE Sellers 
        SET Status = 'suspended',
            SuspensionReason = ?,
            SuspendedBy = ?,
            SuspendedAt = CURRENT_TIMESTAMP
        WHERE SellerID = ?
    """, (reason, suspended_by, seller_id))
    
    conn.commit()
    conn.close()
    
    # إرسال إشعار للبائع
    seller = get_seller_by_id(seller_id)
    if seller:
        try:
            bot.send_message(seller[1],
                           f"⚠️ **تم تعليق حسابك**\n\n"
                           f"🏪 المتجر: {seller[3]}\n"
                           f"📋 السبب: {reason if reason else 'غير محدد'}\n"
                           f"⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                           f"للمزيد من المعلومات، يرجى التواصل مع الإدارة.")
        except:
            pass
    
    return True

def activate_seller(seller_id, activated_by):
    """تنشيط حساب بائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE Sellers 
        SET Status = 'active',
            SuspensionReason = NULL,
            SuspendedBy = NULL,
            SuspendedAt = NULL
        WHERE SellerID = ?
    """, (seller_id,))
    
    conn.commit()
    conn.close()
    
    # إرسال إشعار للبائع
    seller = get_seller_by_id(seller_id)
    if seller:
        try:
            bot.send_message(seller[1],
                           f"✅ **تم تنشيط حسابك**\n\n"
                           f"🏪 المتجر: {seller[3]}\n"
                           f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                           f"يمكنك الآن استخدام حسابك بشكل طبيعي.")
        except:
            pass
    
    return True

def is_seller_active(seller_telegram_id):
    """التحقق من نشاط حساب البائع"""
    seller = get_seller_by_telegram(seller_telegram_id)
    return seller and seller[5] == 'active'

def get_seller_status(seller_id):
    """الحصول على حالة البائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Status, SuspensionReason, SuspendedAt FROM Sellers WHERE SellerID=?", (seller_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_suspended_sellers():
    """الحصول على قائمة الحسابات المعلقة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, u.UserName as SuspenderName
        FROM Sellers s
        LEFT JOIN Users u ON s.SuspendedBy = u.TelegramID
        WHERE s.Status = 'suspended'
        ORDER BY s.SuspendedAt DESC
    """)
    sellers = cursor.fetchall()
    conn.close()
    return sellers

# ===================== نظام الزبائن الآجل =====================
def add_credit_customer(seller_id, full_name, phone_number):
    """إضافة زبون آجل"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO CreditCustomers (SellerID, FullName, PhoneNumber)
            VALUES (?, ?, ?)
        """, (seller_id, full_name, phone_number))
        conn.commit()
        customer_id = cursor.lastrowid
        conn.close()
        return customer_id
    except:
        conn.close()
        return None

def get_credit_customer(seller_id, phone_number=None, full_name=None):
    """الحصول على زبون آجل بالهاتف أو الاسم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if phone_number:
        cursor.execute("""
            SELECT * FROM CreditCustomers 
            WHERE SellerID=? AND PhoneNumber=?
        """, (seller_id, phone_number))
    elif full_name:
        cursor.execute("""
            SELECT * FROM CreditCustomers 
            WHERE SellerID=? AND FullName LIKE ?
        """, (seller_id, f"%{full_name}%"))
    else:
        conn.close()
        return None
    
    customer = cursor.fetchone()
    conn.close()
    return customer

def get_all_credit_customers(seller_id):
    """الحصول على جميع الزبائن الآجلين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cc.*, 
               COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
               COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
               COALESCE(cl.IsActive, 1) as LimitActive
        FROM CreditCustomers cc
        LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
        WHERE cc.SellerID=? 
        ORDER BY cc.FullName
    """, (seller_id,))
    
    customers = cursor.fetchall()
    conn.close()
    return customers

def is_credit_customer(seller_id, phone_number, full_name):
    """التحقق إذا كان زبون آجل"""
    customer = get_credit_customer(seller_id, phone_number, full_name)
    return customer is not None

# ===================== نظام كشف حساب الزبائن الآجل =====================
def add_credit_transaction(customer_id, seller_id, transaction_type, amount, description=""):
    """إضافة معاملة ائتمانية للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الرصيد الحالي
    cursor.execute("""
        SELECT BalanceAfter 
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC LIMIT 1
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    balance_before = result[0] if result else 0
    
    if transaction_type == 'purchase':
        balance_after = balance_before + amount
    elif transaction_type == 'payment':
        balance_after = balance_before - amount
    elif transaction_type == 'adjustment':
        balance_after = amount
    else:
        balance_after = balance_before
    
    # إضافة المعاملة
    query = """
        INSERT INTO CustomerCredit 
        (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if IS_POSTGRES:
        query += " RETURNING CreditID"
    
    cursor.execute(query, (customer_id, seller_id, transaction_type, amount, description, balance_before, balance_after))
    
    # تحديث الحد الائتماني
    if transaction_type in ['purchase', 'payment']:
        update_credit_usage(customer_id, seller_id, amount, transaction_type)
    
    conn.commit()
    conn.close()
    
    return True

def get_customer_balance(customer_id, seller_id):
    """الحصول على رصيد الزبون لدى بائع معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT BalanceAfter 
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC LIMIT 1
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

def get_customer_statement(customer_id, seller_id, limit=10):
    """الحصول على كشف حساب الزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            TransactionType,
            Amount,
            Description,
            BalanceBefore,
            BalanceAfter,
            TransactionDate
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC
        LIMIT ?
    """, (customer_id, seller_id, limit))
    
    transactions = cursor.fetchall()
    conn.close()
    
    return transactions

def get_all_customers_with_balance(seller_id):
    """الحصول على جميع الزبائن الذين لهم رصيد لدى البائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cc.CustomerID,
            cc.FullName,
            cc.PhoneNumber,
            cc.CreatedAt,
            COALESCE((
                SELECT BalanceAfter 
                FROM CustomerCredit 
                WHERE CustomerID = cc.CustomerID AND SellerID = cc.SellerID
                ORDER BY TransactionDate DESC LIMIT 1
            ), 0) as Balance,
            COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
            COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
            COALESCE(cl.IsActive, 1) as LimitActive
        FROM CreditCustomers cc
        LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
        WHERE cc.SellerID = ?
        ORDER BY Balance DESC
    """, (seller_id,))
    
    customers = cursor.fetchall()
    conn.close()
    
    return customers

# ===================== دوال النظام =====================
def add_user(telegram_id, username, usertype, phone_number=None, full_name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, username, usertype, phone_number, full_name))
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE TelegramID=?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_info(telegram_id, phone_number=None, full_name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if phone_number is not None:
        updates.append("PhoneNumber = ?")
        params.append(phone_number)
    
    if full_name is not None:
        updates.append("FullName = ?")
        params.append(full_name)
    
    if updates:
        params.append(telegram_id)
        query = f"UPDATE Users SET {', '.join(updates)} WHERE TelegramID = ?"
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def is_bot_admin(telegram_id):
    return telegram_id == BOT_ADMIN_ID

def add_seller(telegram_id, username, store_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO Sellers (TelegramID, UserName, StoreName)
        VALUES (?, ?, ?)
    """, (telegram_id, username, store_name))
    
    cursor.execute("""
        UPDATE Sellers SET StoreName=?, UserName=?
        WHERE TelegramID=?
    """, (store_name, username, telegram_id))
    conn.commit()
    conn.close()

def get_seller_by_telegram(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
    seller = cursor.fetchone()
    conn.close()
    
    # إذا لم يتم العثور على البائع، حاول البحث في جدول Users
    if not seller:
        user = get_user(telegram_id)
        if user and user[3] == 'seller':
            # إذا كان المستخدم مسجلاً كبائع ولكن ليس في جدول البائعين
            # أضفه إلى جدول البائعين باسم افتراضي
            username = user[2] or user[5] or "بائع"
            store_name = f"متجر {username}"
            add_seller(telegram_id, username, store_name)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
            seller = cursor.fetchone()
            conn.close()
    
    return seller

def get_seller_by_id(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Sellers WHERE SellerID=?", (seller_id,))
    seller = cursor.fetchone()
    conn.close()
    return seller

def is_main_store(telegram_id):
    seller = get_seller_by_telegram(telegram_id)
    return seller is not None

def is_seller(telegram_id):
    seller = get_seller_by_telegram(telegram_id)
    return seller is not None

def get_user_type(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT UserType FROM Users WHERE TelegramID=?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def add_category(seller_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Categories (SellerID, Name) VALUES (?, ?)",
                   (seller_id, name))
    conn.commit()
    conn.close()

def update_category(category_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Categories SET Name = ? WHERE CategoryID = ?", (name, category_id))
    conn.commit()
    conn.close()

def get_categories(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CategoryID, Name FROM Categories WHERE SellerID=? ORDER BY OrderIndex", (seller_id,))
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_category_by_id(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CategoryID, SellerID, Name FROM Categories WHERE CategoryID=?", (category_id,))
    category = cursor.fetchone()
    conn.close()
    return category

def add_product_db(seller_id, category_id, name, description, price, wholesale_price, quantity, image_path=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (seller_id, category_id, name, description, price, wholesale_price, quantity, image_path))
    conn.commit()
    conn.close()

def update_product(product_id, name=None, description=None, price=None, wholesale_price=None, quantity=None, category_id=None, image_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if name is not None:
        updates.append("Name = ?")
        params.append(name)
    
    if description is not None:
        updates.append("Description = ?")
        params.append(description)
    
    if price is not None:
        updates.append("Price = ?")
        params.append(price)
    
    if wholesale_price is not None:
        updates.append("WholesalePrice = ?")
        params.append(wholesale_price)
    
    if quantity is not None:
        updates.append("Quantity = ?")
        params.append(quantity)
    
    if category_id is not None:
        updates.append("CategoryID = ?")
        params.append(category_id)
    
    if image_path is not None:
        updates.append("ImagePath = ?")
        params.append(image_path)
    
    if updates:
        params.append(product_id)
        query = f"UPDATE Products SET {', '.join(updates)} WHERE ProductID = ?"
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def get_products(seller_id=None, category_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if seller_id and category_id:
        cursor.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND CategoryID=? AND Status='active'", 
                      (seller_id, category_id))
    elif seller_id:
        cursor.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND Status='active'", (seller_id,))
    elif category_id:
        cursor.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND CategoryID=? AND Status='active'", (category_id,))
    else:
        cursor.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND Status='active'")
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_by_id(pid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ProductID, SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE ProductID=?", (pid,))
    product = cursor.fetchone()
    conn.close()
    return product

def get_product_price_for_customer(product_id, seller_id, phone_number=None, full_name=None):
    """الحصول على سعر المنتج للزبون (سعر الجملة إذا كان زبوناً آجلاً)"""
    product = get_product_by_id(product_id)
    if not product:
        return None
    
    # التحقق إذا كان الزبون آجلاً (فقط للمستخدمين المسجلين)
    if phone_number or full_name:
        if is_credit_customer(seller_id, phone_number, full_name):
            # إرجاع سعر الجملة إذا كان موجوداً
            return product[6] if product[6] is not None and product[6] > 0 else product[5]
    
    # إرجاع سعر البيع العادي
    return product[5]

def add_to_cart_db(user_id, product_id, quantity=1, price=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if price is None:
        product = get_product_by_id(product_id)
        if not product:
            conn.close()
            return False
        price = product[5]
    
    cursor.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
    existing = cursor.fetchone()
    
    if existing:
        new_quantity = existing[0] + quantity
        cursor.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", 
                      (new_quantity, price, user_id, product_id))
    else:
        cursor.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                      (user_id, product_id, quantity, price))
    
    conn.commit()
    conn.close()
    return True

def get_cart_items_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT C.ProductID, C.Quantity, C.Price, P.Name, P.Description, P.ImagePath, 
               P.Quantity as AvailableQty, P.SellerID, S.StoreName
        FROM Carts C
        JOIN Products P ON C.ProductID = P.ProductID
        JOIN Sellers S ON P.SellerID = S.SellerID
        WHERE C.UserID = ?
        ORDER BY C.AddedAt DESC
    """, (user_id,))
    
    items = cursor.fetchall()
    conn.close()
    return items

def create_order(buyer_id, seller_id, cart_items, delivery_address=None, notes=None, payment_method='cash', fully_paid=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    total = 0
    
    for pid, qty, price in cart_items:
        total += price * qty

    query = """
        INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if IS_POSTGRES:
        query += " RETURNING OrderID"
    
    cursor.execute(query, (buyer_id, seller_id, total, delivery_address, notes, payment_method, fully_paid))
    order_id = cursor.lastrowid

    for pid, qty, price in cart_items:
        product = get_product_by_id(pid)
        if not product:
            continue
        cursor.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                       (order_id, pid, qty, price))
        new_qty = product[7] - qty
        if new_qty < 0:
            new_qty = 0
        cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
    
    # إذا كان الشراء على الحساب ولم يكن مدفوعاً بالكامل، نضيف المعاملة
    if payment_method == 'credit' and not fully_paid:
        # البحث عن الزبون الآجل
        buyer_info = get_user(buyer_id)
        if buyer_info:
            phone = buyer_info[4]
            full_name = buyer_info[5]
            customer = get_credit_customer(seller_id, phone, full_name)
            if customer:
                # التحقق من الحد الائتماني قبل إتمام الشراء
                can_purchase, message, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, total)
                if not can_purchase:
                    # إرجاع الطلب
                    conn.rollback()
                    conn.close()
                    return None, message
                
                add_credit_transaction(customer[0], seller_id, 'purchase', total, f"شراء طلب #{order_id}")

    conn.commit()
    conn.close()
    
    notify_seller_of_order(order_id, buyer_id, seller_id)
    return order_id, total

def get_orders_by_seller(seller_id, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT O.OrderID, O.BuyerID, O.Total, O.Status, O.CreatedAt, 
               O.DeliveryAddress, O.Notes, O.PaymentMethod, O.FullyPaid, 
               U.FullName, U.PhoneNumber
        FROM Orders O
        LEFT JOIN Users U ON O.BuyerID = U.TelegramID
        WHERE O.SellerID = ?
    """
    
    params = [seller_id]
    
    if status:
        query += " AND O.Status = ?"
        params.append(status)
    
    query += " ORDER BY O.CreatedAt DESC"
    
    cursor.execute(query, params)
    orders = cursor.fetchall()
    conn.close()
    return orders

def update_order_status(order_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Orders SET Status=? WHERE OrderID=?", (new_status, order_id))
    conn.commit()
    conn.close()

def get_order_details(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, u.FullName, u.PhoneNumber, u.UserName, s.StoreName
        FROM Orders o
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        LEFT JOIN Sellers s ON o.SellerID = s.SellerID
        WHERE o.OrderID = ?
    """, (order_id,))
    order = cursor.fetchone()
    
    cursor.execute("""
        SELECT oi.*, p.Name, p.Description, p.ImagePath
        FROM OrderItems oi
        JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = ?
    """, (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    return order, items

def clear_cart_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Carts WHERE UserID=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def create_message(order_id, seller_id, message_type, message_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Messages (OrderID, SellerID, MessageType, MessageText) 
        VALUES (?, ?, ?, ?)
    """, (order_id, seller_id, message_type, message_text))
    conn.commit()
    conn.close()

def get_unread_messages(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, o.OrderID, o.BuyerID, o.Status, o.CreatedAt,
               u.FullName, u.PhoneNumber
        FROM Messages m
        JOIN Orders o ON m.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE m.SellerID = ? AND m.IsRead = 0
        ORDER BY m.CreatedAt DESC
    """, (seller_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def mark_message_as_read(message_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET IsRead = 1 WHERE MessageID = ?", (message_id,))
    conn.commit()
    conn.close()

def create_return_request(order_id, product_id, quantity, reason, buyer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT oi.Quantity, oi.ReturnedQuantity 
        FROM OrderItems oi 
        WHERE oi.OrderID = ? AND oi.ProductID = ?
    """, (order_id, product_id))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return False, "المنتج غير موجود في الطلب"
    
    total_quantity = item[0]
    returned_quantity = item[1] or 0
    
    if quantity > (total_quantity - returned_quantity):
        conn.close()
        return False, f"الكمية المطلوبة للإرجاع ({quantity}) أكبر من الكمية المتبقية ({total_quantity - returned_quantity})"
    
    query = """
        INSERT INTO Returns (OrderID, ProductID, Quantity, Reason, Status) 
        VALUES (?, ?, ?, ?, 'Pending')
    """
    if IS_POSTGRES:
        query += " RETURNING ReturnID"
    
    cursor.execute(query, (order_id, product_id, quantity, reason))
    
    return_id = cursor.lastrowid
    
    product = get_product_by_id(product_id)
    if product:
        seller_id = product[1]
        message_text = f"طلب إرجاع جديد للطلب #{order_id}\nالمنتج: {product[3]}\nالكمية: {quantity}\nالسبب: {reason}"
        create_message(order_id, seller_id, 'return_request', message_text)
    
    conn.commit()
    conn.close()
    return True, return_id

def process_return_request(return_id, status, processed_by, notes=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT OrderID, ProductID, Quantity FROM Returns WHERE ReturnID = ?", (return_id,))
    return_request = cursor.fetchone()
    
    if not return_request:
        conn.close()
        return False, "طلب الإرجاع غير موجود"
    
    order_id, product_id, quantity = return_request
    
    if status == 'Approved':
        cursor.execute("""
            UPDATE OrderItems 
            SET ReturnedQuantity = ReturnedQuantity + ?, 
                ReturnReason = ?,
                ReturnDate = CURRENT_TIMESTAMP
            WHERE OrderID = ? AND ProductID = ?
        """, (quantity, notes, order_id, product_id))
        
        cursor.execute("UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?", (quantity, product_id))
        
        cursor.execute("""
            UPDATE Returns 
            SET Status = 'Approved', ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (processed_by, return_id))
        
        product = get_product_by_id(product_id)
        product_name = product[3] if product else "المنتج"
        message = f"✅ تمت الموافقة على إرجاع {quantity} من {product_name}\nملاحظات: {notes if notes else 'لا توجد ملاحظات'}"
        
    elif status == 'Rejected':
        cursor.execute("""
            UPDATE Returns 
            SET Status = 'Rejected', ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (processed_by, return_id))
        
        message = f"❌ تم رفض طلب الإرجاع\nملاحظات: {notes if notes else 'لا توجد ملاحظات'}"
    
    else:
        cursor.execute("""
            UPDATE Returns 
            SET Status = ?, ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (status, processed_by, return_id))
        
        message = f"📝 تم تحديث حالة الإرجاع إلى {status}"
    
    conn.commit()
    conn.close()
    
    order_details = get_order_details(order_id)
    if order_details[0]:
        buyer_id = order_details[0][1]
        try:
            bot.send_message(buyer_id, f"📦 **تحديث حالة الإرجاع**\n\n{message}")
        except:
            pass
    
    return True, "تم تحديث حالة الإرجاع بنجاح"

def get_pending_returns(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, p.Name as ProductName, o.OrderID, o.BuyerID, 
               u.FullName, u.PhoneNumber
        FROM Returns r
        JOIN Products p ON r.ProductID = p.ProductID
        JOIN Orders o ON r.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE p.SellerID = ? AND r.Status = 'Pending'
        ORDER BY r.CreatedAt DESC
    """, (seller_id,))
    
    returns = cursor.fetchall()
    conn.close()
    return returns


def send_privacy_instructions(message, user_id):
    """إرسال تعليمات إعدادات الخصوصية للمستخدم"""
    instructions = """
🔧 **إعدادات الخصوصية المطلوبة:**

للتأكد من استلامك لجميع رسائل البوت، يرجى اتباع الخطوات التالية:

1. **فتح إعدادات تليجرام:**
   - اضغط على ☰ (القائمة)
   - اختر Settings / الإعدادات
   - اختر Privacy and Security / الخصوصية والأمان

2. **إعدادات المجموعات والقنوات:**
   - اضغط على Groups and Channels / المجموعات والقنوات
   - اختر Everybody / الجميع

3. **رسائل البوتات:**
   - تأكد من أن إعدادات الخصوصية تسمح برسائل البوتات

4. **إضافة البوت كجهة اتصال:**
   - ابحث عن البوت: @{}
   - اضغط على Start / بدء المحادثة
   - اضغط على /start

5. **إذا كنت تستخدم تليجرام X أو إصدارات معدلة:**
   - تأكد من أن إعدادات الخصوصية تسمح برسائل البوتات
   - أضف البوت إلى قائمة الجهات المسموح بها

📌 **ملاحظة:** إذا كنت لا تستلم الرسائل، حاول حذف المحادثة مع البوت وإعادة الضغط على /start
    """.format(bot.get_me().username if hasattr(bot, 'get_me') else "اسم_البوت")
    
    try:
        bot.send_message(message.chat.id, instructions, parse_mode='Markdown')
    except:
        # إذا لم نستطع إرسالها للمستخدم، نرسلها للأدمن
        try:
            bot.send_message(BOT_ADMIN_ID, f"تعليمات الخصوصية للمستخدم {user_id}:\n\n{instructions}", parse_mode='Markdown')
        except:
            pass

def notify_seller_of_order(order_id, buyer_id, seller_id):
    """إرسال إشعار للبائع عن الطلب الجديد"""
    order_details, items = get_order_details(order_id)
    
    if not order_details:
        return
    
    seller_info = get_seller_by_id(seller_id)
    if not seller_info or seller_info[5] != 'active':
        return
    
    seller_telegram_id = seller_info[1]
    store_name = seller_info[3]
    
    buyer_info = get_user(buyer_id)
    buyer_name = buyer_info[5] if buyer_info and buyer_info[5] else buyer_info[2] if buyer_info else "مشتري"
    buyer_phone = buyer_info[4] if buyer_info and buyer_info[4] else "غير متوفر"
    
    notification = f"🛎️ **طلب جديد!**\n\n"
    notification += f"🏪 المتجر: {store_name}\n"
    notification += f"🆔 رقم الطلب: {order_id}\n"
    notification += f"👤 المشتري: {buyer_name}\n"
    notification += f"📞 رقم الهاتف: {buyer_phone}\n"
    notification += f"💰 الإجمالي: {order_details[3]} IQD\n"
    notification += f"💳 طريقة الدفع: {'نقداً' if order_details[8] == 'cash' else 'على الحساب'}\n"
    notification += f"💵 حالة الدفع: {'مدفوع بالكامل' if order_details[9] == 1 else 'غير مدفوع بالكامل'}\n"
    notification += f"📅 تاريخ الطلب: {order_details[5]}\n"
    
    if order_details[6]:
        notification += f"📍 العنوان: {order_details[6]}\n"
    
    notification += f"\n📦 **المنتجات:**\n"
    
    for item in items:
        item_id, order_id, product_id, quantity, price, returned_qty, return_reason, return_date = item[:8]
        product_name = item[8] if len(item) > 8 else "منتج"
        notification += f"• {product_name} × {quantity} = {quantity * price} IQD\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{buyer_id}"),
        types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_order_{order_id}"),
        types.InlineKeyboardButton("🚚 تم الشحن", callback_data=f"ship_order_{order_id}"),
        types.InlineKeyboardButton("✅ تم التسليم", callback_data=f"deliver_order_{order_id}"),
        types.InlineKeyboardButton("🗑️ رفض الطلب", callback_data=f"reject_order_{order_id}")
    )
    
    create_message(order_id, seller_id, 'new_order', notification)
    
    try:
        bot.send_message(seller_telegram_id, notification, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للبائع {seller_telegram_id}: {e}")

        
# ===================== بوت التليجرام ====================
user_states = {}
carts = {}

def save_photo_from_message(message):
    """يحفظ الصورة المرسلة"""
    try:
        if not message.photo:
            return None
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        ext = os.path.splitext(file_info.file_path)[1]
        if not ext:
            ext = ".jpg"
        filename = f"{int(time.time())}_{uuid.uuid4().hex}{ext}"
        path = os.path.join(IMAGES_FOLDER, filename)
        with open(path, "wb") as f:
            f.write(downloaded)
        return path
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الصورة: {e}")
        traceback.print_exc()
        return None

def get_bot_info():
    """الحصول على معلومات البوت"""
    try:
        me = bot.get_me()
        return {
            'id': me.id,
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name if hasattr(me, 'last_name') else ''
        }
    except Exception as e:
        print(f"⚠️ خطأ في الحصول على معلومات البوت: {e}")
        return {'id': None, 'username': None, 'first_name': 'Bot'}

def format_seller_mention(username, seller_telegram_id):
    """Return a safe display for seller username. Do not prefix @ for admin store."""
    try:
        if not username:
            return ''
        if seller_telegram_id == BOT_ADMIN_ID:
            return username
        return f"@{username}"
    except:
        return username or ''

def generate_store_link(telegram_id):
    """توليد رابط المتجر"""
    bot_info = get_bot_info()
    if bot_info['username']:
        return f"https://t.me/{bot_info['username']}?start=store_{telegram_id}"
    return None

# ====== دالة لعرض المنتجات مع صورها ======
def send_product_with_image(chat_id, product, markup=None, seller_name=""):
    """إرسال منتج مع صورته"""
    try:
        pid, name, desc, price, wholesale_price, qty, img_path = product
        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD"
        if wholesale_price and wholesale_price > 0:
            caption += f"\n💰 سعر الجملة: {wholesale_price} IQD"
        caption += f"\n📦 متاح: {qty}"
        if seller_name:
            caption += f"\n🏪 {seller_name}"
        if desc:
            caption += f"\n📝 {desc[:100]}{'...' if len(desc) > 100 else ''}"
        
        if img_path and os.path.exists(img_path):
            try:
                with open(img_path, 'rb') as photo:
                    if markup:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    else:
                        bot.send_photo(chat_id, photo, caption=caption, parse_mode='Markdown')
            except Exception as e:
                print(f"⚠️ خطأ في إرسال الصورة: {e}")
                # إذا فشل إرسال الصورة، أرسل النص فقط
                if markup:
                    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
                else:
                    bot.send_message(chat_id, caption, parse_mode='Markdown')
        else:
            # إذا لم توجد صورة
            if markup:
                bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, caption, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ خطأ في send_product_with_image: {e}")
        traceback.print_exc()

# ====== دالة لعرض عناصر السلة مع الصور ======
def send_cart_item_with_image(chat_id, cart_item, markup=None):
    """إرسال عنصر في السلة مع صورته"""
    try:
        product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = cart_item
        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD\n📦 الكمية: {quantity}\n💰 المجموع: {price * quantity} IQD"
        caption += f"\n🏪 {seller_name}"
        
        if desc:
            caption += f"\n📝 {desc[:50]}{'...' if len(desc) > 50 else ''}"
        
        if img_path and os.path.exists(img_path):
            try:
                with open(img_path, 'rb') as photo:
                    if markup:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    else:
                        bot.send_photo(chat_id, photo, caption=caption, parse_mode='Markdown')
            except Exception as e:
                print(f"⚠️ خطأ في إرسال صورة السلة: {e}")
                if markup:
                    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
                else:
                    bot.send_message(chat_id, caption, parse_mode='Markdown')
        else:
            if markup:
                bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, caption, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ خطأ في send_cart_item_with_image: {e}")
        traceback.print_exc()

# ====== /start ======
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    text = message.text or ""
    
    if "store_" in text:
        try:
            idx = text.index("store_")
            token = text[idx+len("store_"):].strip()
            token = token.split()[0]
            seller_telegram_id = int(token)
            send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id)
            return
        except Exception:
            pass

    if is_bot_admin(telegram_id):
        add_user(telegram_id, username, "bot_admin")
        show_bot_admin_menu(message)
        return
    
    user = get_user(telegram_id)
    
    # ====== التعديل الجديد ======
    # إذا لم يكن المستخدم مسجل، نعطيه خيار التسجيل أو التصفح بدون تسجيل
    if not user:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("تسجيل حساب جديد 📝", "تصفح بدون تسجيل 👀")
        markup.row("🏠 الرئيسية")
        
        bot.send_message(message.chat.id,
                        "👋 **مرحباً بك في متجرنا!**\n\n"
                        "يمكنك:\n"
                        "1. **تسجيل حساب جديد** للاستفادة من جميع المزايا\n"
                        "2. **تصفح المتاجر بدون تسجيل** وإضافة المنتجات للسلة\n\n"
                        "💡 **ملاحظة:** التسجيل مجاني ويوفر لك:\n"
                        "• حفظ طلباتك السابقة\n"
                        "• إمكانية الشراء على الحساب\n"
                        "• كشف حسابك الآجل\n"
                        "• متابعة مرتجعاتك",
                        reply_markup=markup)
        return
    
    user_type = user[3]
    
    if user_type == 'bot_admin':
        show_bot_admin_menu(message)
    elif user_type == 'seller':
        show_seller_menu(message)
    elif user_type == 'buyer':
        show_buyer_main_menu(message)
    else:
        add_user(telegram_id, username, "buyer")
        show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "تسجيل حساب جديد 📝")
def register_new_user(message):
    msg = bot.send_message(message.chat.id, 
                          "👋 **مرحباً بك في تسجيل حساب جديد!**\n\n"
                          "يرجى إدخال اسمك الكامل:")
    bot.register_next_step_handler(msg, get_user_full_name_register, message.from_user.id, message.from_user.username)

def get_user_full_name_register(message, telegram_id, username):
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return start(message)
    
    msg = bot.send_message(message.chat.id, 
                          f"شكراً {full_name}!\n\n"
                          "يرجى إدخال رقم هاتفك للتواصل (اختياري):")
    bot.register_next_step_handler(msg, get_user_phone_register, telegram_id, username, full_name)

def get_user_phone_register(message, telegram_id, username, full_name):
    phone_number = message.text.strip() if message.text else None
    
    add_user(telegram_id, username, "buyer", phone_number, full_name)
    
    bot.send_message(message.chat.id, 
                    f"✅ **تم تسجيل معلوماتك بنجاح!**\n\n"
                    f"👤 الاسم: {full_name}\n"
                    f"📞 الهاتف: {phone_number if phone_number else 'غير محدد'}\n\n"
                    "يمكنك الآن البدء في التسوق 🛍️")
    
    show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "تصفح بدون تسجيل 👀")
def browse_without_registration(message):
    telegram_id = message.from_user.id
    
    # تخزين حالة المستخدم كزائر
    user_states[telegram_id] = {
        'is_guest': True,
        'name': message.from_user.first_name,
        'username': message.from_user.username
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
    markup.row("👤 تسجيل حساب جديد", "🏠 الرئيسية")
    
    bot.send_message(message.chat.id,
                    "👀 **مرحباً بك كزائر!**\n\n"
                    "يمكنك تصفح المتاجر وإضافة المنتجات للسلة.\n"
                    "عند إنهاء الطلب، سيُطلب منك إدخال معلوماتك.\n\n"
                    "💡 **للاستفادة من جميع المزايا:**\n"
                    "• حفظ طلباتك السابقة\n"
                    "• الشراء على الحساب\n"
                    "• متابعة مرتجعاتك\n\n"
                    "اختر '👤 تسجيل حساب جديد' للتسجيل.",
                    reply_markup=markup)

# ====== القوائم الرئيسية ======
def show_bot_admin_menu(message):
    telegram_id = message.from_user.id
    
    # التحقق إذا كان أدمن البوت لديه متجر
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🏪 إنشاء متجر خاص بي", callback_data="create_admin_store"),
            types.InlineKeyboardButton("👑 الوضع الإداري فقط", callback_data="admin_mode_only")
        )
        bot.send_message(message.chat.id, 
                        "👑 **مرحباً بأدمن البوت!**\n\n"
                        "يمكنك الاختيار بين:\n"
                        "1. إنشاء متجر خاص بك وإدارته\n"
                        "2. البقاء في الوضع الإداري فقط",
                        reply_markup=markup)
        return
    
    # إذا كان لديه متجر
    store_name = seller[3] if seller else "المتجر الإداري"
    
    unread_count = len(get_unread_messages(seller[0])) if seller else 0
    messages_badge = f" 📨({unread_count})" if unread_count > 0 else ""
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row("👑 لوحة التحكم الإدارية")
    markup.row("➕ إضافة منتج", "✏️ تعديل منتج")
    markup.row("➕ إضافة قسم", "✏️ تعديل قسم")
    markup.row(f"📩 الرسائل{messages_badge}", "📊 كشف حساب الزبائن")
    markup.row("🏪 إدارة الزبائن الآجلين", "📁 الأقسام", "🏪 منتجاتي")
    markup.row("🔗 رابط المتجر")
    markup.row("📦 إرجاع المنتجات", "🛍️ وضع المشتري")
    markup.row("➕ إضافة متجر", "📋 قائمة المتاجر")
    markup.row("👑 إدارة الحسابات", "📊 إحصائيات النظام")
    markup.row("🏠 الرئيسية")
    
    welcome_msg = f"👑🏪 **مرحباً بأدمن البوت وصاحب المتجر!**\n\n"
    welcome_msg += f"🏪 متجرك: {store_name}\n"
    welcome_msg += f"👑 صلاحياتك: إدارة النظام الكاملة"
    
    if unread_count > 0:
        welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

def show_admin_dashboard(message):
    """لوحة التحكم الإدارية فقط"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    markup.row("👑 إدارة الحسابات", "📊 إحصائيات النظام")
    markup.row("➕ إضافة متجر", "📋 قائمة المتاجر")
    markup.row("🛍️ وضع المشتري", "🏠 الرئيسية")
    
    bot.send_message(
        message.chat.id,
        "👑 **لوحة التحكم الإدارية**\n\n"
        "يمكنك إدارة النظام من هنا:\n\n"
        "• 👑 إدارة الحسابات - تعليق/تنشيط المتاجر\n"
        "• 📊 إحصائيات النظام - إحصائيات النظام\n"
        "• ➕ إضافة متجر - إضافة متجر جديد\n"
        "• 📋 قائمة المتاجر - عرض جميع المتاجر\n"
        "• 🛍️ وضع المشتري - التبديل لوضع المشتري",
        reply_markup=markup,
        parse_mode='Markdown'
    )

def show_seller_menu(message):
    telegram_id = message.from_user.id
    
    # التحقق أولاً إذا كان المستخدم مسجل كبائع
    seller = get_seller_by_telegram(telegram_id)
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست صاحب متجر مسجل!")
        return
    
    if not is_seller_active(telegram_id):
        bot.send_message(message.chat.id,
                        "⛔ **حسابك معطل**\n\n"
                        "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                        "يرجى التواصل مع الإدارة.")
        return
    
    store_name = seller[3] if seller else "متجرك"
    
    unread_count = len(get_unread_messages(seller[0])) if seller else 0
    messages_badge = f" 📨({unread_count})" if unread_count > 0 else ""
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ إضافة منتج", "✏️ تعديل منتج")
    markup.row("➕ إضافة قسم", "✏️ تعديل قسم")
    markup.row(f"📩 الرسائل{messages_badge}", "📊 كشف حساب الزبائن")
    markup.row("🏪 إدارة الزبائن الآجلين", "📁 الأقسام", "🏪 منتجاتي")
    markup.row("📊 لوحة التحكم", "🔗 رابط المتجر")
    markup.row("📦 إرجاع المنتجات", "🛍️ وضع المشتري")
    markup.row("🏠 الرئيسية")
    
    welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
    welcome_msg += f"🏪 متجرك: {store_name}"
    if unread_count > 0:
        welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

def show_buyer_main_menu(message):
    telegram_id = message.from_user.id
    user = get_user(telegram_id)
    
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    if telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest'):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
        markup.row("👤 تسجيل حساب جديد", "🏠 الرئيسية")
        
        bot.send_message(message.chat.id,
                        "👀 **مرحباً بك كزائر!**\n\n"
                        "يمكنك تصفح المتاجر وإضافة المنتجات للسلة.\n"
                        "عند إنهاء الطلب، سيُطلب منك إدخال معلوماتك.\n\n"
                        "💡 **للاستفادة من جميع المزايا:**\n"
                        "• حفظ طلباتك السابقة\n"
                        "• الشراء على الحساب\n"
                        "• متابعة مرتجعاتك\n\n"
                        "اختر '👤 تسجيل حساب جديد' للتسجيل.",
                        reply_markup=markup)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
    markup.row("📋 طلباتي", "📦 مرتجعاتي")
    markup.row("💰 كشف حسابي الآجل", "👤 تعديل بياناتي")
    markup.row("🏠 الرئيسية")
    
    welcome_msg = "👋 **مرحباً بك كـ مشتري!**\nاختر من القائمة:"
    
    if user and (user[4] or user[5]):
        welcome_msg += f"\n\n👤 الاسم: {user[5] if user[5] else 'غير محدد'}"
        welcome_msg += f"\n📞 الهاتف: {user[4] if user[4] else 'غير محدد'}"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# ====== معالجة اختيارات أدمن البوت ======
@bot.callback_query_handler(func=lambda call: call.data == "create_admin_store")
def handle_create_admin_store(call):
    user_states[call.from_user.id] = {
        "step": "create_admin_store_name"
    }
    
    bot.send_message(call.message.chat.id,
                    "🏪 **إنشاء متجر خاص بأدمن البوت**\n\n"
                    "يرجى إدخال اسم المتجر:")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_mode_only")
def handle_admin_mode_only(call):
    show_admin_dashboard(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "create_admin_store_name")
def process_admin_store_name(message):
    user_id = message.from_user.id
    store_name = message.text.strip()
    
    if not store_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمتجر.")
        return
    
    # إنشاء متجر لأدمن البوت
    username = message.from_user.username or message.from_user.first_name
    add_seller(user_id, username, store_name)
    add_user(user_id, username, "bot_admin")
    
    bot.send_message(message.chat.id,
                    f"✅ **تم إنشاء متجرك بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, user_id)}\n"
                    f"👑 الصلاحية: أدمن البوت وصاحب المتجر\n\n"
                    f"يمكنك الآن:\n"
                    f"1. إدارة متجرك\n"
                    f"2. الوصول للوظائف الإدارية الكاملة\n"
                    f"3. التبديل بين وضع المشتري والإدارة")
    
    del user_states[user_id]
    show_bot_admin_menu(message)

# ====== معالجة قائمة أدمن البوت ======
@bot.message_handler(func=lambda message: message.text == "👑 لوحة التحكم الإدارية" and is_bot_admin(message.from_user.id))
def admin_dashboard_menu(message):
    show_admin_dashboard(message)

@bot.message_handler(func=lambda message: message.text == "👑 إدارة الحسابات" and is_bot_admin(message.from_user.id))
def manage_accounts(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 قائمة المتاجر النشطة", callback_data="list_active_stores"),
        types.InlineKeyboardButton("⚠️ قائمة المتاجر المعلقة", callback_data="list_suspended_stores"),
        types.InlineKeyboardButton("⏸️ تعليق متجر", callback_data="suspend_store_menu"),
        types.InlineKeyboardButton("▶️ تنشيط متجر", callback_data="activate_store_menu")
    )
    
    bot.send_message(message.chat.id, "👑 **إدارة حسابات المتاجر**", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📊 إحصائيات النظام" and is_bot_admin(message.from_user.id))
def system_stats(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # إحصائيات المستخدمين
    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'buyer'")
    total_buyers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'seller'")
    total_sellers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'bot_admin'")
    total_bot_admins = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Sellers WHERE Status = 'active'")
    active_sellers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Sellers WHERE Status = 'suspended'")
    suspended_sellers = cursor.fetchone()[0]
    
    # إحصائيات المنتجات
    cursor.execute("SELECT COUNT(*) FROM Products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Products WHERE Quantity > 0")
    available_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(Quantity) FROM Products")
    total_quantity = cursor.fetchone()[0] or 0
    
    # إحصائيات الطلبات
    cursor.execute("SELECT COUNT(*) FROM Orders")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE Status = 'Pending'")
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE Status = 'Delivered'")
    delivered_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(Total) FROM Orders WHERE Status = 'Delivered'")
    total_sales = cursor.fetchone()[0] or 0
    
    # إحصائيات الائتمان
    cursor.execute("SELECT SUM(BalanceAfter) FROM CustomerCredit")
    total_credit = cursor.fetchone()[0] or 0
    
    # إحصائيات الزبائن الآجلين
    cursor.execute("SELECT COUNT(*) FROM CreditCustomers")
    total_credit_customers = cursor.fetchone()[0]
    
    # إحصائيات الحدود الائتمانية
    cursor.execute("SELECT COUNT(*) FROM CreditLimits WHERE IsActive = 1")
    active_credit_limits = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(MaxCreditAmount), SUM(CurrentUsedAmount) FROM CreditLimits WHERE IsActive = 1")
    limits = cursor.fetchone()
    total_max_credit = limits[0] or 0
    total_used_credit = limits[1] or 0
    
    conn.close()
    
    text = "📊 **إحصائيات النظام**\n\n"
    text += "👥 **المستخدمين:**\n"
    text += f"• إجمالي المستخدمين: {total_users}\n"
    text += f"• المشترين: {total_buyers}\n"
    text += f"• البائعين: {total_sellers}\n"
    text += f"• أدمن البوت: {total_bot_admins}\n\n"
    
    text += "🏪 **المتاجر:**\n"
    text += f"• النشطة: {active_sellers}\n"
    text += f"• المعلقة: {suspended_sellers}\n\n"
    
    text += "🛒 **المنتجات:**\n"
    text += f"• إجمالي المنتجات: {total_products}\n"
    text += f"• المنتجات المتاحة: {available_products}\n"
    text += f"• إجمالي الكمية: {total_quantity}\n\n"
    
    text += "📦 **الطلبات:**\n"
    text += f"• إجمالي الطلبات: {total_orders}\n"
    text += f"• قيد الانتظار: {pending_orders}\n"
    text += f"• تم التسليم: {delivered_orders}\n"
    text += f"• إجمالي المبيعات: {total_sales} IQD\n\n"
    
    text += "💰 **الائتمان:**\n"
    text += f"• إجمالي الديون: {total_credit} IQD\n"
    text += f"• عدد الزبائن الآجلين: {total_credit_customers}\n"
    text += f"• عدد الحدود النشطة: {active_credit_limits}\n"
    text += f"• إجمالي الحدود المسموحة: {total_max_credit:,.0f} IQD\n"
    text += f"• إجمالي المبالغ المستخدمة: {total_used_credit:,.0f} IQD\n"
    text += f"• النسبة المستخدمة: {(total_used_credit/total_max_credit*100 if total_max_credit > 0 else 0):.1f}%\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ====== إضافة متجر جديد (للأدمن فقط) ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة متجر" and is_bot_admin(message.from_user.id))
def add_main_store_step1(message):
    msg = bot.send_message(message.chat.id, "أرسل معرف التليجرام الخاص بصاحب المتجر الجديد:")
    bot.register_next_step_handler(msg, add_main_store_step2)

def add_main_store_step2(message):
    try:
        telegram_id = int(message.text)
        msg = bot.send_message(message.chat.id, "أرسل اسم المتجر الجديد:")
        bot.register_next_step_handler(msg, add_main_store_step3, telegram_id)
    except:
        bot.send_message(message.chat.id, "معرّف غير صالح. الرجاء إدخال رقم.")
        if is_bot_admin(message.from_user.id):
            show_bot_admin_menu(message)
        else:
            show_admin_dashboard(message)

def add_main_store_step3(message, telegram_id):
    store_name = message.text
    
    try:
        # محاولة الحصول على معلومات المستخدم
        chat_member = bot.get_chat(telegram_id)
        username = chat_member.username if hasattr(chat_member, 'username') and chat_member.username else chat_member.first_name
    except Exception as e:
        print(f"⚠️ خطأ في الحصول على معلومات المستخدم {telegram_id}: {e}")
        username = "مستخدم"
    
    # إضافة المتجر
    add_seller(telegram_id, username, store_name)
    add_user(telegram_id, username, "seller")
    
    # توليد رابط المتجر
    store_link = generate_store_link(telegram_id)
    
    links_text = ""
    markup = types.InlineKeyboardMarkup()
    
    if store_link:
        links_text += f"🔗 **رابط المتجر:**\n`{store_link}`\n\n"
        markup.add(types.InlineKeyboardButton("📋 نسخ رابط المتجر", callback_data=f"copy_store_link_{telegram_id}"))
    
    # إرسال الرسالة للأدمن
    bot.send_message(message.chat.id, 
                    f"✅ **تم إضافة المتجر بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, telegram_id)}\n"
                    f"🆔 المعرف: {telegram_id}\n\n"
                    f"{links_text}", 
                    reply_markup=markup,
                    parse_mode='Markdown')
    
    # محاولة إرسال رسالة لصاحب المتجر الجديد
    try:
        bot.send_message(telegram_id, 
                        f"🎉 **تهانينا!**\n\n"
                        f"تمت إضافتك كصاحب متجر!\n"
                        f"🏪 متجرك: {store_name}\n\n"
                        f"يمكنك الآن:\n"
                        f"1. إضافة منتجات للمتجر\n"
                        f"2. إدارة طلبات العملاء\n"
                        f"3. متابعة كشف حساب الزبائن\n\n"
                        f"🔗 رابط متجرك:\n{store_link if store_link else 'سيتم إرساله لاحقاً'}\n\n"
                        f"📝 **لبدء استخدام المتجر:**\n"
                        f"1. اضغط /start لبدء الاستخدام\n"
                        f"2. اختر '🏪 إضافة منتج' لإضافة منتجات\n"
                        f"3. شارك رابط متجرك مع عملائك")
        
        # إرسال قائمة البائع
        show_seller_menu_for_new_seller(telegram_id, store_name)
    except Exception as e:
        print(f"⚠️ تعذر إرسال رسالة لصاحب المتجر {telegram_id}: {e}")
        bot.send_message(message.chat.id, 
                        f"⚠️ **ملاحظة:** تعذر إرسال رسالة لصاحب المتجر الجديد.\n"
                        f"يرجى إبلاغه بأنه تمت إضافته كصاحب متجر وتزويده برابط المتجر:\n{store_link if store_link else 'سيتم توليد الرابط لاحقاً'}")
    
    if is_bot_admin(message.from_user.id):
        show_bot_admin_menu(message)
    else:
        show_admin_dashboard(message)

def show_seller_menu_for_new_seller(telegram_id, store_name):
    """إظهار قائمة البائع للمستخدم الجديد"""
    try:
        # التحقق أولاً إذا كان المستخدم مسجلاً كبائع
        seller = get_seller_by_telegram(telegram_id)
        if not seller:
            return
        
        if not is_seller_active(telegram_id):
            bot.send_message(telegram_id,
                            "⛔ **حسابك معطل**\n\n"
                            "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                            "يرجى التواصل مع الإدارة.")
            return
        
        store_name = seller[3] if seller else "متجرك"
        
        unread_count = len(get_unread_messages(seller[0])) if seller else 0
        messages_badge = f" 📨({unread_count})" if unread_count > 0 else ""
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("➕ إضافة منتج", "✏️ تعديل منتج")
        markup.row("➕ إضافة قسم", "✏️ تعديل قسم")
        markup.row(f"📩 الرسائل{messages_badge}", "📊 كشف حساب الزبائن")
        markup.row("🏪 إدارة الزبائن الآجلين", "📁 الأقسام", "🏪 منتجاتي")
        markup.row("📊 لوحة التحكم", "🔗 رابط المتجر")
        markup.row("📦 إرجاع المنتجات", "🛍️ وضع المشتري")
        markup.row("🏠 الرئيسية")
        
        welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
        welcome_msg += f"🏪 متجرك: {store_name}"
        if unread_count > 0:
            welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
        
        bot.send_message(telegram_id, welcome_msg, reply_markup=markup)
    except Exception as e:
        print(f"⚠️ خطأ في إظهار قائمة البائع لـ {telegram_id}: {e}")

# ====== دالة handle_copy_store_link محسنة ======
def handle_copy_store_link(call):
    try:
        telegram_id = int(call.data.split("_")[3])
        store_link = generate_store_link(telegram_id)
        
        if store_link:
            # نسخ الرابط إلى الحافظة (محاكاة)
            bot.answer_callback_query(call.id, f"✅ تم نسخ رابط المتجر\n\n{store_link}", show_alert=False)
            
            # إرسال رسالة تأكيد
            try:
                seller = get_seller_by_telegram(telegram_id)
                store_name = seller[3] if seller else "المتجر"
                
                bot.send_message(call.message.chat.id,
                               f"✅ **تم نسخ رابط متجرك**\n\n"
                               f"🏪 {store_name}\n"
                               f"🔗 **الرابط:** `{store_link}`\n\n"
                               f"يمكنك الآن مشاركة الرابط مع عملائك.")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "⚠️ تعذر توليد رابط المتجر")
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)}")

# ====== إصلاح مشكلة /start للمتاجر ======
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    text = message.text or ""
    
    if "store_" in text:
        try:
            idx = text.index("store_")
            token = text[idx+len("store_"):].strip()
            token = token.split()[0]
            seller_telegram_id = int(token)
            
            # التحقق إذا كان المستخدم الحالي هو صاحب المتجر
            if telegram_id == seller_telegram_id:
                # إذا كان صاحب المتجر، نعرض له قائمة البائع
                seller = get_seller_by_telegram(telegram_id)
                if seller:
                    if is_seller_active(telegram_id):
                        show_seller_menu(message)
                    else:
                        bot.send_message(message.chat.id,
                                        "⛔ **حسابك معطل**\n\n"
                                        "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                                        "يرجى التواصل مع الإدارة.")
                else:
                    # إذا لم يكن مسجلاً كبائع بعد
                    bot.send_message(message.chat.id,
                                    "⚠️ **لست مسجلاً كبائع**\n\n"
                                    "يبدو أنك لست مسجلاً كصاحب متجر.\n"
                                    "يرجى التواصل مع الإدارة.")
            else:
                # إذا كان زائراً للمتجر، نعرض له المنتجات
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id)
            return
        except Exception as e:
            print(f"⚠️ خطأ في فتح رابط المتجر: {e}")
            pass

    if is_bot_admin(telegram_id):
        add_user(telegram_id, username, "bot_admin")
        show_bot_admin_menu(message)
        return
    
    user = get_user(telegram_id)
    
    # ====== التعديل الجديد ======
    # إذا لم يكن المستخدم مسجل، نعطيه خيار التسجيل أو التصفح بدون تسجيل
    if not user:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("تسجيل حساب جديد 📝", "تصفح بدون تسجيل 👀")
        markup.row("🏠 الرئيسية")
        
        bot.send_message(message.chat.id,
                        "👋 **مرحباً بك في متجرنا!**\n\n"
                        "يمكنك:\n"
                        "1. **تسجيل حساب جديد** للاستفادة من جميع المزايا\n"
                        "2. **تصفح المتاجر بدون تسجيل** وإضافة المنتجات للسلة\n\n"
                        "💡 **ملاحظة:** التسجيل مجاني ويوفر لك:\n"
                        "• حفظ طلباتك السابقة\n"
                        "• إمكانية الشراء على الحساب\n"
                        "• كشف حسابك الآجل\n"
                        "• متابعة مرتجعاتك",
                        reply_markup=markup)
        return
    
    user_type = user[3]
    
    if user_type == 'bot_admin':
        show_bot_admin_menu(message)
    elif user_type == 'seller':
        seller = get_seller_by_telegram(telegram_id)
        if seller:
            if is_seller_active(telegram_id):
                show_seller_menu(message)
            else:
                bot.send_message(message.chat.id,
                                "⛔ **حسابك معطل**\n\n"
                                "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                                "يرجى التواصل مع الإدارة.")
        else:
            # إذا كان مسجلاً كبائع ولكن ليس في جدول البائعين
            add_user(telegram_id, username, "buyer")
            show_buyer_main_menu(message)
    elif user_type == 'buyer':
        show_buyer_main_menu(message)
    else:
        add_user(telegram_id, username, "buyer")
        show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "📋 قائمة المتاجر" and is_bot_admin(message.from_user.id))
def list_stores(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, 
               CASE WHEN s.Status = 'active' THEN '✅' ELSE '⏸️' END as StatusIcon
        FROM Sellers s
        ORDER BY s.CreatedAt DESC
    """)
    stores = cursor.fetchall()
    conn.close()
    
    if not stores:
        bot.send_message(message.chat.id, "لا توجد متاجر مسجلة بعد.")
        return
    
    text = "📋 **قائمة جميع المتاجر:**\n\n"
    
    for store in stores:
        seller_id, telegram_id, username, store_name, created_at, status = store[:6]
        status_icon = store[6] if len(store) > 6 else ""
        
        text += f"{status_icon} **المتجر:** {store_name}\n"
        text += f"👤 المالك: {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📅 تاريخ الإنشاء: {created_at}\n"
        text += f"📊 الحالة: {'نشط' if status == 'active' else 'معلق'}\n"
        text += "────\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🛍️ وضع المشتري")
def admin_switch_to_buyer_mode(message):
    show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية" and is_bot_admin(message.from_user.id))
def admin_main_menu(message):
    show_bot_admin_menu(message)

# ====== وظائف إضافة وتعديل القسم ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة قسم" and is_seller(message.from_user.id))
def add_category_step1(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    user_states[telegram_id] = {
        "step": "add_category",
        "seller_id": seller[0]
    }
    
    bot.send_message(message.chat.id, "📁 **إضافة قسم جديد**\n\nيرجى إدخال اسم القسم:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_category")
def add_category_step2(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    category_name = message.text.strip()
    
    if not category_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للقسم.")
        return
    
    # إضافة القسم إلى قاعدة البيانات
    add_category(state["seller_id"], category_name)
    
    bot.send_message(message.chat.id, f"✅ **تم إضافة القسم بنجاح!**\n\n📁 القسم: {category_name}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.text == "✏️ تعديل قسم" and is_seller(message.from_user.id))
def edit_category_step1(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام لتعديلها.\n\nيمكنك إضافة قسم جديد أولاً.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for category_id, category_name in categories:
        markup.add(types.InlineKeyboardButton(category_name, callback_data=f"edit_cat_{category_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "📁 **تعديل قسم**\n\n"
                    "اختر القسم الذي تريد تعديله:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_cat_"))
def handle_edit_category(call):
    try:
        category_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        category = get_category_by_id(category_id)
        if not category:
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
        
        user_states[telegram_id] = {
            "step": "edit_category_name",
            "category_id": category_id
        }
        
        bot.send_message(call.message.chat.id,
                        f"📁 **تعديل قسم**\n\n"
                        f"القسم الحالي: {category[2]}\n\n"
                        f"يرجى إدخال الاسم الجديد للقسم:")
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_category_name")
def edit_category_step2(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_name = message.text.strip()
    
    if not new_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للقسم.")
        return
    
    # تحديث اسم القسم
    update_category(state["category_id"], new_name)
    
    bot.send_message(message.chat.id, f"✅ **تم تعديل القسم بنجاح!**\n\n📁 الاسم الجديد: {new_name}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def handle_back_to_menu(call):
    telegram_id = call.from_user.id
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(call.message)
    elif is_seller(telegram_id):
        show_seller_menu(call.message)
    else:
        show_buyer_main_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "📁 الأقسام" and is_seller(message.from_user.id))
def view_categories(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام بعد.\n\nيمكنك إضافة قسم جديد من القائمة.")
        return
    
    text = "📁 **أقسام متجرك:**\n\n"
    
    for i, category in enumerate(categories, 1):
        category_id, category_name = category
        text += f"{i}. **{category_name}**\n"
        text += f"   🆔 معرف القسم: {category_id}\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="add_new_category"))
    markup.add(types.InlineKeyboardButton("✏️ تعديل قسم", callback_data="go_to_edit_category"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "add_new_category")
def handle_add_new_category(call):
    add_category_step1(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "go_to_edit_category")
def handle_go_to_edit_category(call):
    edit_category_step1(call.message)
    bot.answer_callback_query(call.id)

# ====== وظائف إضافة وتعديل المنتج ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة منتج" and is_seller(message.from_user.id))
def add_product_step1(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام بعد.\n\nيرجى إضافة قسم أولاً قبل إضافة المنتجات.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for category_id, category_name in categories:
        markup.add(types.InlineKeyboardButton(category_name, callback_data=f"select_category_{category_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🛒 **إضافة منتج جديد**\n\n"
                    "اختر القسم الذي ترغب بإضافة المنتج إليه:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_category_"))
def handle_select_category_for_product(call):
    try:
        category_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        seller = get_seller_by_telegram(telegram_id)
        if not seller:
            bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
            return
        
        user_states[telegram_id] = {
            "step": "add_product_name",
            "category_id": category_id,
            "seller_id": seller[0]
        }
        
        bot.send_message(call.message.chat.id, 
                        "🛒 **إضافة منتج جديد**\n\n"
                        "الآن، يرجى إدخال اسم المنتج:")
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_name")
def add_product_step2(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    product_name = message.text.strip()
    
    if not product_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمنتج.")
        return
    
    user_states[telegram_id]["product_name"] = product_name
    user_states[telegram_id]["step"] = "add_product_description"
    
    bot.send_message(message.chat.id, 
                    "📝 **وصف المنتج**\n\n"
                    "الآن، يرجى إدخال وصف للمنتج (اختياري):\n\n"
                    "يمكنك كتابة وصف تفصيلي أو كتابة 'تخطي' للاستمرار.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_description")
def add_product_step3(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    description = message.text.strip()
    if description.lower() == "تخطي":
        description = ""
    
    user_states[telegram_id]["description"] = description
    user_states[telegram_id]["step"] = "add_product_price"
    
    bot.send_message(message.chat.id, 
                    "💰 **سعر المنتج**\n\n"
                    "الآن، يرجى إدخال سعر المنتج (بالدينار العراقي):")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_price")
def add_product_step4(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        price = float(message.text)
        if price <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
        return
    
    user_states[telegram_id]["price"] = price
    user_states[telegram_id]["step"] = "add_product_wholesale_price"
    
    bot.send_message(message.chat.id, 
                    "💰 **سعر الجملة**\n\n"
                    "الآن، يرجى إدخال سعر الجملة (بالدينار العراقي):\n"
                    "يمكنك كتابة 'تخطي' إذا لم يكن هناك سعر جملة.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_wholesale_price")
def add_product_step4b(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    wholesale_price_text = message.text.strip()
    
    if wholesale_price_text.lower() == "تخطي":
        wholesale_price = None
    else:
        try:
            wholesale_price = float(wholesale_price_text)
            if wholesale_price <= 0:
                bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
                return
        except:
            bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
            return
    
    user_states[telegram_id]["wholesale_price"] = wholesale_price
    user_states[telegram_id]["step"] = "add_product_quantity"
    
    bot.send_message(message.chat.id, 
                    "📦 **كمية المنتج**\n\n"
                    "الآن، يرجى إدخال كمية المنتج المتاحة:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_quantity")
def add_product_step5(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        quantity = int(message.text)
        if quantity < 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة (صفر أو أكبر).")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    user_states[telegram_id]["quantity"] = quantity
    user_states[telegram_id]["step"] = "add_product_image"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("📸 إرسال صورة", "⏭️ تخطي بدون صورة")
    
    bot.send_message(message.chat.id, 
                    "📸 **صورة المنتج**\n\n"
                    "الآن، يمكنك إرسال صورة للمنتج (اختياري):\n\n"
                    "• اضغط '📸 إرسال صورة' لإرسال صورة\n"
                    "• أو اضغط '⏭️ تخطي بدون صورة' للمتابعة بدون صورة",
                    reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_image")
def add_product_step6(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "📸 إرسال صورة":
        user_states[telegram_id]["step"] = "waiting_for_product_image"
        bot.send_message(message.chat.id, "📤 الرجاء إرسال صورة المنتج الآن:")
        return
    elif message.text == "⏭️ تخطي بدون صورة":
        image_path = ""
        finish_adding_product(message, image_path)
        return
    else:
        if message.content_type == 'text':
            image_path = ""
            finish_adding_product(message, image_path)
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("📸 إرسال صورة", "⏭️ تخطي بدون صورة")
        bot.send_message(message.chat.id, 
                        "⚠️ الرجاء اختيار أحد الخيارين:\n\n"
                        "• اضغط '📸 إرسال صورة' لإرسال صورة\n"
                        "• أو اضغط '⏭️ تخطي بدون صورة' للمتابعة بدون صورة",
                        reply_markup=markup)
        return

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_product_image")
def handle_product_image_photo(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        image_path = save_photo_from_message(message)
        if not image_path:
            bot.send_message(message.chat.id, "⚠️ حدث خطأ في حفظ الصورة، سيتم المتابعة بدون صورة.")
            image_path = ""
        
        finish_adding_product(message, image_path)
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الصورة: {e}")
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في معالجة الصورة، سيتم المتابعة بدون صورة.")
        finish_adding_product(message, "")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_product_image" and 
                     message.content_type == 'text')
def handle_product_image_text(message):
    telegram_id = message.from_user.id
    if message.text.lower() in ['تخطي', 'تخطي بدون صورة', 'skip', 'الغاء']:
        finish_adding_product(message, "")
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'تخطي' للمتابعة بدون صورة.")

def finish_adding_product(message, image_path=""):
    telegram_id = message.from_user.id
    if telegram_id not in user_states:
        bot.send_message(message.chat.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    state = user_states[telegram_id]
    
    # التحقق من وجود جميع البيانات المطلوبة
    required_fields = ["seller_id", "category_id", "product_name", "price", "quantity"]
    for field in required_fields:
        if field not in state:
            bot.send_message(message.chat.id, f"⚠️ بيانات غير مكتملة: {field}")
            del user_states[telegram_id]
            show_seller_menu(message)
            return
    
    # حفظ المنتج في قاعدة البيانات
    seller_id = state["seller_id"]
    category_id = state["category_id"]
    product_name = state["product_name"]
    description = state.get("description", "")
    price = state["price"]
    wholesale_price = state.get("wholesale_price")
    quantity = state["quantity"]
    
    try:
        add_product_db(seller_id, category_id, product_name, description, price, wholesale_price, quantity, image_path)
    except Exception as e:
        print(f"⚠️ خطأ في حفظ المنتج: {e}")
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في حفظ المنتج، يرجى المحاولة مرة أخرى.")
        del user_states[telegram_id]
        return
    
    # الحصول على اسم القسم
    category = get_category_by_id(category_id)
    category_name = category[2] if category else "غير محدد"
    
    success_msg = f"✅ **تم إضافة المنتج بنجاح!**\n\n"
    success_msg += f"🛒 **المنتج:** {product_name}\n"
    success_msg += f"📁 **القسم:** {category_name}\n"
    success_msg += f"💰 **السعر:** {price} IQD\n"
    if wholesale_price:
        success_msg += f"💰 **سعر الجملة:** {wholesale_price} IQD\n"
    success_msg += f"📦 **الكمية:** {quantity}\n"
    
    if description:
        success_msg += f"📝 **الوصف:** {description}\n"
    
    if image_path and os.path.exists(image_path):
        success_msg += "📸 **تم رفع صورة المنتج**"
    else:
        success_msg += "📷 **بدون صورة**"
    
    # إرسال الصورة مع التفاصيل إذا كان هناك صورة
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=success_msg, parse_mode='Markdown')
        except Exception as e:
            print(f"⚠️ خطأ في إرسال الصورة: {e}")
            bot.send_message(message.chat.id, success_msg, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, success_msg, parse_mode='Markdown')
    
    del user_states[telegram_id]
    show_seller_menu(message)

# ====== تعديل المنتج ======
@bot.message_handler(func=lambda message: message.text == "✏️ تعديل منتج" and is_seller(message.from_user.id))
def edit_product_step1(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    products = get_products(seller_id=seller[0])
    
    if not products:
        bot.send_message(message.chat.id, "📭 لا توجد منتجات لتعديلها.\n\nيمكنك إضافة منتجات أولاً.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for product in products[:10]:
        pid, name, desc, price, wholesale_price, qty, img_path = product
        markup.add(types.InlineKeyboardButton(f"{name[:15]}...", callback_data=f"edit_product_{pid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🛒 **تعديل منتج**\n\n"
                    "اختر المنتج الذي تريد تعديله:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_product_"))
def handle_select_product_to_edit(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return
        
        user_states[telegram_id] = {
            "step": "edit_product_select_field",
            "product_id": product_id,
            "product_data": product
        }
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data="edit_prod_name"),
            types.InlineKeyboardButton("📝 تعديل الوصف", callback_data="edit_prod_desc"),
            types.InlineKeyboardButton("💰 تعديل السعر", callback_data="edit_prod_price"),
            types.InlineKeyboardButton("💰 تعديل سعر الجملة", callback_data="edit_prod_wholesale"),
            types.InlineKeyboardButton("📦 تعديل الكمية", callback_data="edit_prod_qty"),
            types.InlineKeyboardButton("📁 تغيير القسم", callback_data="edit_prod_cat"),
            types.InlineKeyboardButton("📸 تغيير الصورة", callback_data="edit_prod_img"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_edit_product")
        )
        
        pid, seller_id, category_id, name, desc, price, wholesale_price, qty, img_path = product
        
        category = get_category_by_id(category_id)
        category_name = category[2] if category else "غير محدد"
        
        text = f"🛒 **تعديل المنتج**\n\n"
        text += f"**المنتج:** {name}\n"
        text += f"**القسم:** {category_name}\n"
        text += f"**الوصف:** {desc[:50] if desc else 'لا يوجد وصف'}...\n"
        text += f"**السعر:** {price} IQD\n"
        if wholesale_price:
            text += f"**سعر الجملة:** {wholesale_price} IQD\n"
        text += f"**الكمية:** {qty}\n\n"
        text += "اختر ما تريد تعديله:"
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_edit_product")
def handle_back_to_edit_product(call):
    edit_product_step1(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_prod_"))
def handle_edit_product_field(call):
    telegram_id = call.from_user.id
    if telegram_id not in user_states:
        bot.answer_callback_query(call.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    state = user_states[telegram_id]
    product_id = state["product_id"]
    product = state["product_data"]
    
    field = call.data.split("_")[2]
    
    if field == "name":
        user_states[telegram_id]["step"] = "edit_product_name"
        bot.send_message(call.message.chat.id,
                        f"✏️ **تعديل اسم المنتج**\n\n"
                        f"الاسم الحالي: {product[3]}\n\n"
                        f"يرجى إدخال الاسم الجديد:")
    
    elif field == "desc":
        user_states[telegram_id]["step"] = "edit_product_description"
        current_desc = product[4] if product[4] else "لا يوجد وصف"
        bot.send_message(call.message.chat.id,
                        f"📝 **تعديل وصف المنتج**\n\n"
                        f"الوصف الحالي: {current_desc}\n\n"
                        f"يرجى إدخال الوصف الجديد (أو 'حذف' لحذف الوصف):")
    
    elif field == "price":
        user_states[telegram_id]["step"] = "edit_product_price"
        bot.send_message(call.message.chat.id,
                        f"💰 **تعديل سعر المنتج**\n\n"
                        f"السعر الحالي: {product[5]} IQD\n\n"
                        f"يرجى إدخال السعر الجديد (بالدينار العراقي):")
    
    elif field == "wholesale":
        user_states[telegram_id]["step"] = "edit_product_wholesale"
        current_wholesale = product[6] if product[6] else "لا يوجد"
        bot.send_message(call.message.chat.id,
                        f"💰 **تعديل سعر الجملة**\n\n"
                        f"سعر الجملة الحالي: {current_wholesale if current_wholesale != 'لا يوجد' else current_wholesale} IQD\n\n"
                        f"يرجى إدخال سعر الجملة الجديد (بالدينار العراقي):\n"
                        f"أو اكتب 'حذف' لحذف سعر الجملة.")
    
    elif field == "qty":
        user_states[telegram_id]["step"] = "edit_product_quantity"
        bot.send_message(call.message.chat.id,
                        f"📦 **تعديل كمية المنتج**\n\n"
                        f"الكمية الحالية: {product[7]}\n\n"
                        f"يرجى إدخال الكمية الجديدة:")
    
    elif field == "cat":
        user_states[telegram_id]["step"] = "edit_product_category"
        seller = get_seller_by_telegram(telegram_id)
        categories = get_categories(seller[0])
        
        if not categories:
            bot.send_message(call.message.chat.id, "📭 لا توجد أقسام متاحة.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            markup.add(types.InlineKeyboardButton(cat_name, callback_data=f"select_new_cat_{cat_id}"))
        
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_edit_product"))
        
        current_category = get_category_by_id(product[2])
        current_cat_name = current_category[2] if current_category else "غير محدد"
        
        bot.send_message(call.message.chat.id,
                        f"📁 **تغيير قسم المنتج**\n\n"
                        f"القسم الحالي: {current_cat_name}\n\n"
                        f"اختر القسم الجديد:",
                        reply_markup=markup)
    
    elif field == "img":
        user_states[telegram_id]["step"] = "edit_product_image"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("📸 إرسال صورة جديدة", "🗑️ حذف الصورة الحالية", "⏭️ إلغاء")
        
        bot.send_message(call.message.chat.id,
                        f"📸 **تغيير صورة المنتج**\n\n"
                        f"اختر الإجراء المناسب:",
                        reply_markup=markup)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_new_cat_"))
def handle_select_new_category(call):
    telegram_id = call.from_user.id
    if telegram_id not in user_states:
        bot.answer_callback_query(call.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    try:
        category_id = int(call.data.split("_")[3])
        state = user_states[telegram_id]
        
        update_product(state["product_id"], category_id=category_id)
        
        category = get_category_by_id(category_id)
        category_name = category[2] if category else "غير محدد"
        
        bot.send_message(call.message.chat.id,
                        f"✅ **تم تغيير قسم المنتج بنجاح!**\n\n"
                        f"القسم الجديد: {category_name}")
        
        del user_states[telegram_id]
        handle_select_product_to_edit(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_name")
def process_edit_product_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_name = message.text.strip()
    
    if not new_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمنتج.")
        return
    
    update_product(state["product_id"], name=new_name)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل اسم المنتج بنجاح!**\n\n"
                    f"الاسم الجديد: {new_name}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_description")
def process_edit_product_description(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_description = message.text.strip()
    
    if new_description.lower() == "حذف":
        new_description = ""
    
    update_product(state["product_id"], description=new_description)
    
    if new_description:
        bot.send_message(message.chat.id,
                        f"✅ **تم تعديل وصف المنتج بنجاح!**\n\n"
                        f"الوصف الجديد: {new_description[:100]}...")
    else:
        bot.send_message(message.chat.id,
                        "✅ **تم حذف وصف المنتج بنجاح!**")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_price")
def process_edit_product_price(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        new_price = float(message.text)
        if new_price <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
        return
    
    update_product(state["product_id"], price=new_price)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل سعر المنتج بنجاح!**\n\n"
                    f"السعر الجديد: {new_price} IQD")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_wholesale")
def process_edit_product_wholesale(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    wholesale_text = message.text.strip()
    
    if wholesale_text.lower() == "حذف":
        new_wholesale_price = None
    else:
        try:
            new_wholesale_price = float(wholesale_text)
            if new_wholesale_price <= 0:
                bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
                return
        except:
            bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
            return
    
    update_product(state["product_id"], wholesale_price=new_wholesale_price)
    
    if new_wholesale_price is None:
        bot.send_message(message.chat.id,
                        "✅ **تم حذف سعر الجملة بنجاح!**")
    else:
        bot.send_message(message.chat.id,
                        f"✅ **تم تعديل سعر الجملة بنجاح!**\n\n"
                        f"سعر الجملة الجديد: {new_wholesale_price} IQD")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_quantity")
def process_edit_product_quantity(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        new_quantity = int(message.text)
        if new_quantity < 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة (صفر أو أكبر).")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    update_product(state["product_id"], quantity=new_quantity)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل كمية المنتج بنجاح!**\n\n"
                    f"الكمية الجديدة: {new_quantity}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_image")
def process_edit_product_image(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "📸 إرسال صورة جديدة":
        user_states[telegram_id]["step"] = "waiting_for_new_product_image"
        bot.send_message(message.chat.id, "📤 الرجاء إرسال الصورة الجديدة الآن:")
        return
    
    elif message.text == "🗑️ حذف الصورة الحالية":
        update_product(state["product_id"], image_path="")
        
        bot.send_message(message.chat.id,
                        "✅ **تم حذف صورة المنتج بنجاح!**")
        
        del user_states[telegram_id]
        show_seller_menu(message)
        return
    
    elif message.text == "⏭️ إلغاء":
        bot.send_message(message.chat.id,
                        "❌ **تم إلغاء تغيير الصورة**")
        
        del user_states[telegram_id]
        show_seller_menu(message)
        return

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_new_product_image")
def handle_new_product_image_photo(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    image_path = save_photo_from_message(message)
    if not image_path:
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في حفظ الصورة، لم يتم تغيير الصورة.")
    else:
        update_product(state["product_id"], image_path=image_path)
        
        bot.send_message(message.chat.id,
                        "✅ **تم تغيير صورة المنتج بنجاح!**")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_new_product_image" and 
                     message.content_type == 'text')
def handle_new_product_image_text(message):
    if message.text.lower() in ['إلغاء', 'الغاء', 'cancel']:
        bot.send_message(message.chat.id, "❌ **تم إلغاء تغيير الصورة**")
        telegram_id = message.from_user.id
        del user_states[telegram_id]
        show_seller_menu(message)
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'إلغاء'.")

# ====== عرض منتجات المتجر ======
@bot.message_handler(func=lambda message: message.text == "🏪 منتجاتي" and is_seller(message.from_user.id))
def view_my_products(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام بعد، وبالتالي لا توجد منتجات.\n\nيمكنك إضافة قسم ثم إضافة منتجات.")
        return
    
    all_products = []
    
    for category_id, category_name in categories:
        products = get_products(seller_id=seller[0], category_id=category_id)
        if products:
            all_products.append((category_name, products))
    
    if not all_products:
        bot.send_message(message.chat.id, "📭 لا توجد منتجات في متجرك بعد.\n\nيمكنك إضافة منتجات من القائمة.")
        return
    
    text = f"🏪 **منتجات متجرك**\n\n"
    
    for category_name, products in all_products:
        text += f"📁 **{category_name}:**\n"
        
        for product in products:
            pid, name, desc, price, wholesale_price, qty, img_path = product
            text += f"🛒 **{name}**\n"
            text += f"   🆔 معرف المنتج: {pid}\n"
            text += f"   💰 السعر: {price} IQD\n"
            if wholesale_price:
                text += f"   💰 سعر الجملة: {wholesale_price} IQD\n"
            text += f"   📦 الكمية: {qty}\n"
            
            if desc:
                text += f"   📝 الوصف: {desc[:50]}...\n" if len(desc) > 50 else f"   📝 الوصف: {desc}\n"
            
            text += "   ────\n"
        
        text += "\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ====== زر نسخ رابط المتجر ======
@bot.message_handler(func=lambda message: message.text == "🔗 رابط المتجر" and (is_seller(message.from_user.id) or is_bot_admin(message.from_user.id)))
def get_store_link(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "لم يتم العثور على معلومات المتجر.")
        return
    
    store_name = seller[3]
    store_link = generate_store_link(telegram_id)
    
    if not store_link:
        bot.send_message(message.chat.id, "⚠️ تعذر توليد رابط المتجر.")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 نسخ رابط المتجر", callback_data=f"copy_store_link_{telegram_id}"))
    
    bot.send_message(message.chat.id,
                    f"🔗 **رابط متجرك**\n\n"
                    f"🏪 المتجر: {store_name}\n\n"
                    f"**الرابط:**\n`{store_link}`\n\n"
                    f"يمكنك مشاركة هذا الرابط مع عملائك لزيارة متجرك.",
                    reply_markup=markup,
                    parse_mode='Markdown')

# ====== نظام كشف حساب الزبائن الآجل مع الحدود ======
@bot.message_handler(func=lambda message: message.text == "📊 كشف حساب الزبائن" and is_seller(message.from_user.id))
def customer_credit_dashboard(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.send_message(message.chat.id, "📭 لا يوجد زبائن لهم رصيد آجل حالياً.")
        return
    
    text = f"💰 **كشف حساب الزبائن الآجل**\n🏪 المتجر: {seller[3]}\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    total_balance = 0
    total_max_credit = 0
    total_used_credit = 0
    
    for customer in customers:
        customer_id, full_name, phone, created_at, balance, max_credit, current_used, limit_active = customer
        total_balance += balance
        total_max_credit += max_credit
        total_used_credit += current_used
        
        text += f"👤 **{full_name}**\n"
        text += f"📞 {phone if phone else 'لا يوجد'}\n"
        text += f"💰 الرصيد: {balance} IQD\n"
        
        if limit_active == 1:
            percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
            if percentage_used >= 100:
                status = "❌ ممتلئ"
            elif percentage_used >= 80:
                status = "⚠️ تحذير"
            else:
                status = "✅ جيد"
            
            text += f"💳 الحد الائتماني: {max_credit:,.0f} دينار\n"
            text += f"📊 المستخدم: {current_used:,.0f} دينار ({percentage_used:.1f}%) {status}\n"
        
        text += "────\n\n"
        
        markup.add(types.InlineKeyboardButton(f"👤 {full_name[:10]}", callback_data=f"view_customer_statement_{customer_id}"))
    
    text += f"\n💰 **إجمالي المديونيات:** {total_balance} IQD"
    text += f"\n💳 **إجمالي الحدود:** {total_max_credit:,.0f} دينار"
    text += f"\n📊 **إجمالي المستخدم:** {total_used_credit:,.0f} دينار"
    
    percentage_total = (total_used_credit / total_max_credit * 100) if total_max_credit > 0 else 0
    text += f"\n📈 **نسبة الاستخدام:** {percentage_total:.1f}%"
    
    markup.add(types.InlineKeyboardButton("➕ تسجيل دفعة", callback_data="record_payment"))
    markup.add(types.InlineKeyboardButton("💳 إدارة الحدود", callback_data="manage_credit_limits"))
    markup.add(types.InlineKeyboardButton("📊 الإحصائيات", callback_data="credit_stats"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🏪 إدارة الزبائن الآجلين" and is_seller(message.from_user.id))
def manage_credit_customers(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_credit_customers(seller[0])
    
    if not customers:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ إضافة زبون آجل", callback_data="add_credit_customer"))
        bot.send_message(message.chat.id, "📭 لا يوجد زبائن آجلين مسجلين.\n\nيمكنك إضافة زبون آجل جديد:", reply_markup=markup)
        return
    
    text = f"🏪 **الزبائن الآجلين**\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for customer in customers:
        customer_id, seller_id, full_name, phone, created_at, max_credit, current_used, limit_active = customer
        
        text += f"👤 **{full_name}**\n"
        text += f"📞 {phone if phone else 'لا يوجد'}\n"
        
        if limit_active == 1:
            percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
            text += f"💳 الحد: {max_credit:,.0f} دينار ({percentage_used:.1f}%)\n"
        
        text += f"📅 تاريخ الإضافة: {created_at}\n"
        text += "────\n\n"
        
        markup.add(types.InlineKeyboardButton(f"👤 {full_name[:10]}", callback_data=f"view_credit_customer_{customer_id}"))
    
    markup.add(types.InlineKeyboardButton("➕ إضافة زبون آجل", callback_data="add_credit_customer"))
    markup.add(types.InlineKeyboardButton("💳 إدارة الحدود", callback_data="manage_credit_limits"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "add_credit_customer")
def handle_add_credit_customer(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    user_states[telegram_id] = {
        "step": "add_credit_customer_name",
        "seller_id": seller[0]
    }
    
    bot.send_message(call.message.chat.id,
                    "👤 **إضافة زبون آجل**\n\n"
                    "يرجى إدخال اسم الزبون الكامل:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_credit_customer_name")
def process_credit_customer_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return
    
    user_states[telegram_id]["full_name"] = full_name
    user_states[telegram_id]["step"] = "add_credit_customer_phone"
    
    bot.send_message(message.chat.id,
                    "📞 **رقم هاتف الزبون**\n\n"
                    "يرجى إدخال رقم هاتف الزبون (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم يكن هناك رقم هاتف.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_credit_customer_phone")
def process_credit_customer_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    phone = message.text.strip()
    if phone.lower() == "تخطي":
        phone = None
    
    seller_id = state["seller_id"]
    full_name = state["full_name"]
    
    customer_id = add_credit_customer(seller_id, full_name, phone)
    
    if customer_id:
        bot.send_message(message.chat.id,
                        f"✅ **تم إضافة الزبون الآجل بنجاح!**\n\n"
                        f"👤 الاسم: {full_name}\n"
                        f"📞 الهاتف: {phone if phone else 'غير محدد'}\n"
                        f"🆔 معرف الزبون: {customer_id}\n\n"
                        f"💡 **تلميح:** يمكنك تعيين حد ائتماني للزبون من خلال قائمة '💳 إدارة الحدود'")
    else:
        bot.send_message(message.chat.id,
                        "⚠️ **حدث خطأ**\n\n"
                        "تعذر إضافة الزبون. قد يكون رقم الهاتف مسجلاً مسبقاً.")
    
    del user_states[telegram_id]
    manage_credit_customers(message)

@bot.callback_query_handler(func=lambda call: call.data == "manage_credit_limits")
def handle_manage_credit_limits(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_credit_customers(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن آجلين")
        return
    
    text = f"💳 **إدارة الحدود الائتمانية**\n🏪 المتجر: {seller[3]}\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for customer in customers:
        customer_id, seller_id, full_name, phone, created_at, max_credit, current_used, limit_active = customer
        
        text += f"👤 **{full_name}**\n"
        
        if limit_active == 1:
            percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
            status = "✅ نشط" if limit_active == 1 else "⏸️ غير نشط"
            text += f"💳 الحد: {max_credit:,.0f} دينار\n"
            text += f"📊 المستخدم: {current_used:,.0f} دينار ({percentage_used:.1f}%)\n"
            text += f"📊 الحالة: {status}\n"
        else:
            text += f"💳 الحد: غير محدد\n"
            text += f"📊 الحالة: ⏸️ غير مفعل\n"
        
        text += "────\n\n"
        
        markup.add(types.InlineKeyboardButton(f"💳 {full_name[:10]}", callback_data=f"set_credit_limit_{customer_id}"))
    
    markup.add(types.InlineKeyboardButton("➕ تعيين حد جديد", callback_data="add_new_credit_limit"))
    markup.add(types.InlineKeyboardButton("📊 تقرير الحدود", callback_data="credit_limits_report"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_credit_menu"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_credit_limit_"))
def handle_set_credit_limit(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    user_states[telegram_id] = {
        "step": "set_credit_limit_amount",
        "customer_id": customer_id,
        "seller_id": seller[0]
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    current_limit_info = get_credit_limit_info(customer_id, seller[0])
    
    bot.send_message(call.message.chat.id,
                    f"💳 **تعيين حد ائتماني للزبون**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 الحد الحالي: {current_limit_info['max_limit']:,.0f} دينار\n"
                    f"📊 المستخدم: {current_limit_info['current_used']:,.0f} دينار\n"
                    f"📈 الحالة: {current_limit_info['status']}\n\n"
                    f"يرجى إدخال الحد الائتماني الجديد (بالدينار العراقي):\n"
                    f"أو اكتب 'تعطيل' لتعطيل الحد الائتماني")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "set_credit_limit_amount")
def process_credit_limit_amount(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    amount_text = message.text.strip().lower()
    
    if amount_text == "تعطيل":
        deactivate_credit_limit(state["customer_id"], state["seller_id"])
        bot.send_message(message.chat.id,
                        "✅ **تم تعطيل الحد الائتماني للزبون**\n\n"
                        "سيتمكن الزبون الآن من الشراء بدون حدود.")
        
        del user_states[telegram_id]
        manage_credit_customers(message)
        return
    
    try:
        max_amount = float(amount_text)
        if max_amount <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال مبلغ صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للمبلغ.")
        return
    
    user_states[telegram_id]["max_amount"] = max_amount
    user_states[telegram_id]["step"] = "set_warning_threshold"
    
    bot.send_message(message.chat.id,
                    "📊 **عتبة التحذير**\n\n"
                    "يرجى إدخال نسبة التحذير كنسبة مئوية (مثال: 80 يعني 80%):\n"
                    "سيتم إرسال تحذير عندما يصل استخدام الزبون لهذه النسبة.\n\n"
                    "القيمة الافتراضية: 80")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "set_warning_threshold")
def process_warning_threshold(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        warning_percentage = float(message.text)
        if warning_percentage <= 0 or warning_percentage > 100:
            bot.send_message(message.chat.id, "الرجاء إدخال نسبة بين 1 و 100.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للنسبة.")
        return
    
    max_amount = state["max_amount"]
    warning_threshold = warning_percentage / 100
    
    set_credit_limit(state["customer_id"], state["seller_id"], max_amount, warning_threshold)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (state["customer_id"],))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعيين الحد الائتماني بنجاح!**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 الحد الأقصى: {max_amount:,.0f} دينار\n"
                    f"📊 عتبة التحذير: {warning_percentage}%\n\n"
                    f"💡 **ملاحظة:** سيتم رفض الطلبات الجديدة إذا تجاوزت الحد المسموح.")
    
    del user_states[telegram_id]
    manage_credit_customers(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_credit_customer_"))
def handle_view_credit_customer(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    
    if not customer:
        bot.answer_callback_query(call.id, "الزبون غير موجود")
        return
    
    customer_id, seller_id, full_name, phone, created_at = customer
    
    text = f"👤 **معلومات الزبون الآجل**\n\n"
    text += f"🆔 معرف الزبون: {customer_id}\n"
    text += f"👤 الاسم: {full_name}\n"
    text += f"📞 الهاتف: {phone if phone else 'غير محدد'}\n"
    text += f"📅 تاريخ الإضافة: {created_at}\n\n"
    
    # الحصول على الرصيد الحالي
    balance = get_customer_balance(customer_id, seller_id)
    text += f"💰 **الرصيد الحالي:** {balance} IQD\n"
    
    # الحصول على معلومات الحد الائتماني
    limit_info = get_credit_limit_info(customer_id, seller_id)
    text += f"💳 **الحد الائتماني:** {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 **المستخدم:** {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 **المتبقي:** {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 **الحالة:** {limit_info['status']}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 كشف حساب", callback_data=f"view_customer_statement_{customer_id}"),
        types.InlineKeyboardButton("💰 تسجيل دفعة", callback_data=f"select_customer_payment_{customer_id}"),
        types.InlineKeyboardButton("💳 إدارة الحد", callback_data=f"set_credit_limit_{customer_id}"),
        types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_credit_customer_{customer_id}"),
        types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_credit_customer_{customer_id}")
    )
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "record_payment")
def handle_record_payment(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن لهم رصيد آجل")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for customer in customers:
        customer_id, full_name, phone, created_at, balance, max_credit, current_used, limit_active = customer
        display_name = full_name
        markup.add(types.InlineKeyboardButton(f"👤 {display_name} - {balance} IQD", callback_data=f"select_customer_payment_{customer_id}"))
    
    bot.send_message(call.message.chat.id, "👤 **اختر الزبون لتسجيل دفعة:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_customer_payment_"))
def handle_select_customer_payment(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    user_states[telegram_id] = {
        "step": "record_payment_amount",
        "customer_id": customer_id,
        "seller_id": seller[0]
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName, PhoneNumber FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    current_balance = get_customer_balance(customer_id, seller[0])
    
    # الحصول على معلومات الحد الائتماني
    limit_info = get_credit_limit_info(customer_id, seller[0])
    
    bot.send_message(call.message.chat.id,
                    f"💰 **تسجيل دفعة للزبون**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 الرصيد الحالي: {current_balance} IQD\n"
                    f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
                    f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
                    f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n\n"
                    f"يرجى إدخال مبلغ الدفعة (بالدينار العراقي):")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "record_payment_amount")
def process_payment_amount(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال مبلغ صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للمبلغ.")
        return
    
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    current_balance = get_customer_balance(customer_id, seller_id)
    
    if amount > current_balance:
        bot.send_message(message.chat.id,
                        f"⚠️ **تحذير:** المبلغ المدخل ({amount} IQD) أكبر من الرصيد الحالي ({current_balance} IQD)\n\n"
                        f"هل تريد المتابعة؟ (اكتب 'نعم' للموافقة أو 'لا' للإلغاء)")
        
        user_states[telegram_id]["step"] = "confirm_payment"
        user_states[telegram_id]["amount"] = amount
        return
    
    # تسجيل الدفعة
    add_credit_transaction(customer_id, seller_id, 'payment', amount, f"دفعة نقدية من الزبون")
    
    new_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تسجيل الدفعة بنجاح!**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 المبلغ: {amount} IQD\n"
                    f"💰 الرصيد السابق: {current_balance} IQD\n"
                    f"💰 الرصيد الجديد: {new_balance} IQD\n"
                    f"💳 الحد المتبقي: {limit_info['available']:,.0f} دينار")
    
    del user_states[telegram_id]
    customer_credit_dashboard(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "confirm_payment")
def confirm_payment(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text.lower() not in ['نعم', 'yes']:
        bot.send_message(message.chat.id, "❌ تم إلغاء تسجيل الدفعة.")
        del user_states[telegram_id]
        customer_credit_dashboard(message)
        return
    
    amount = state["amount"]
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    current_balance = get_customer_balance(customer_id, seller_id)
    
    add_credit_transaction(customer_id, seller_id, 'payment', amount, f"دفعة نقدية من الزبون (مبلغ زائد)")
    
    new_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تسجيل الدفعة بنجاح!**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 المبلغ: {amount} IQD\n"
                    f"💰 الرصيد السابق: {current_balance} IQD\n"
                    f"💰 الرصيد الجديد: {new_balance} IQD\n"
                    f"💳 الحد المتبقي: {limit_info['available']:,.0f} دينار\n\n"
                    f"⚠️ **ملاحظة:** الزبون لديه رصيد ائتماني بقيمة {-new_balance} IQD")
    
    del user_states[telegram_id]
    customer_credit_dashboard(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_customer_statement_"))
def handle_view_customer_statement(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName, PhoneNumber FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    customer_phone = customer_info[1] if customer_info and customer_info[1] else "غير متوفر"
    
    statement = get_customer_statement(customer_id, seller[0], limit=20)
    
    if not statement:
        bot.answer_callback_query(call.id, "لا توجد معاملات لهذا الزبون")
        return
    
    current_balance = get_customer_balance(customer_id, seller[0])
    limit_info = get_credit_limit_info(customer_id, seller[0])
    
    text = f"📊 **كشف حساب الزبون**\n\n"
    text += f"👤 الزبون: {customer_name}\n"
    text += f"📞 الهاتف: {customer_phone}\n"
    text += f"💰 الرصيد الحالي: {current_balance} IQD\n"
    text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 الحالة: {limit_info['status']}\n\n"
    text += f"📋 **آخر 20 معاملة:**\n\n"
    
    for trans in statement:
        trans_type, amount, description, balance_before, balance_after, trans_date = trans
        
        trans_type_arabic = {
            'purchase': 'شراء',
            'payment': 'دفعة',
            'adjustment': 'تعديل'
        }.get(trans_type, trans_type)
        
        emoji = "🛒" if trans_type == 'purchase' else "💰" if trans_type == 'payment' else "📝"
        
        text += f"{emoji} **{trans_type_arabic}**\n"
        text += f"📅 {trans_date}\n"
        text += f"💵 المبلغ: {amount} IQD\n"
        
        if description:
            text += f"📝 {description}\n"
        
        text += f"💰 الرصيد: {balance_after} IQD\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ تسجيل دفعة", callback_data=f"select_customer_payment_{customer_id}"))
    markup.add(types.InlineKeyboardButton("💳 إدارة الحد", callback_data=f"set_credit_limit_{customer_id}"))
    markup.add(types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_credit_menu"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "credit_stats")
def handle_credit_stats(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن لهم رصيد آجل")
        return
    
    total_balance = 0
    positive_balance = 0
    negative_balance = 0
    customer_count = len(customers)
    
    total_max_credit = 0
    total_used_credit = 0
    active_limits = 0
    
    for customer in customers:
        balance = customer[4]
        max_credit = customer[5]
        current_used = customer[6]
        limit_active = customer[7]
        
        total_balance += balance
        
        if balance > 0:
            positive_balance += balance
        else:
            negative_balance += balance
        
        if limit_active == 1:
            active_limits += 1
            total_max_credit += max_credit
            total_used_credit += current_used
    
    text = f"📊 **إحصائيات الائتمان**\n🏪 المتجر: {seller[3]}\n\n"
    text += f"👥 عدد الزبائن: {customer_count}\n"
    text += f"💳 عدد الحدود النشطة: {active_limits}\n"
    text += f"💰 إجمالي المديونيات: {positive_balance} IQD\n"
    text += f"💳 إجمالي الرصيد الائتماني: {-negative_balance} IQD\n"
    text += f"⚖️ صافي الرصيد: {total_balance} IQD\n\n"
    
    if active_limits > 0:
        text += f"📈 **إحصائيات الحدود:**\n"
        text += f"• إجمالي الحدود المسموحة: {total_max_credit:,.0f} دينار\n"
        text += f"• إجمالي المبالغ المستخدمة: {total_used_credit:,.0f} دينار\n"
        text += f"• نسبة الاستخدام: {(total_used_credit/total_max_credit*100 if total_max_credit > 0 else 0):.1f}%\n\n"
    
    if positive_balance > 0:
        text += f"📋 **أكبر المديونيات:**\n"
        sorted_customers = sorted(customers, key=lambda x: x[4], reverse=True)[:5]
        
        for customer in sorted_customers:
            customer_id, full_name, phone, created_at, balance = customer[:5]
            if balance > 0:
                display_name = full_name
                text += f"• {display_name}: {balance} IQD\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_credit_menu")
def handle_back_to_credit_menu(call):
    customer_credit_dashboard(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "💰 كشف حسابي الآجل")
def my_credit_statement(message):
    telegram_id = message.from_user.id
    user = get_user(telegram_id)
    
    if not user:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على بياناتك.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT s.SellerID, s.StoreName, 
               COALESCE((
                   SELECT cc.FullName 
                   FROM CreditCustomers cc 
                   WHERE cc.PhoneNumber = ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               ), (
                   SELECT cc.FullName 
                   FROM CreditCustomers cc 
                   WHERE cc.FullName LIKE ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               )) as CustomerName,
               COALESCE((
                   SELECT cc.CustomerID 
                   FROM CreditCustomers cc 
                   WHERE cc.PhoneNumber = ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               ), (
                   SELECT cc.CustomerID 
                   FROM CreditCustomers cc 
                   WHERE cc.FullName LIKE ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               )) as CustomerID
        FROM Sellers s
        WHERE EXISTS (
            SELECT 1 FROM CreditCustomers cc 
            WHERE cc.SellerID = s.SellerID 
            AND (cc.PhoneNumber = ? OR cc.FullName LIKE ?)
        )
    """, (user[4], f"%{user[5]}%", user[4], f"%{user[5]}%", user[4], f"%{user[5]}%"))
    
    sellers_with_customers = cursor.fetchall()
    conn.close()
    
    if not sellers_with_customers:
        bot.send_message(message.chat.id, "💰 **حسابك الآجل**\n\nليس لديك أي مديونيات أو رصيد ائتماني حالياً.")
        return
    
    text = f"💰 **كشف حسابك الآجل**\n👤 {user[5] if user[5] else user[2]}\n\n"
    
    total_balance = 0
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for seller_id, store_name, customer_name, customer_id in sellers_with_customers:
        if customer_id:
            balance = get_customer_balance(customer_id, seller_id)
            total_balance += balance
            
            limit_info = get_credit_limit_info(customer_id, seller_id)
            
            text += f"🏪 **{store_name}**\n"
            text += f"💰 الرصيد: {balance} IQD\n"
            
            if balance > 0:
                text += f"📋 **مدين بمبلغ:** {balance} IQD\n"
            elif balance < 0:
                text += f"💳 **لديك رصيد ائتماني:** {-balance} IQD\n"
            else:
                text += f"✅ **حسابك متوازن**\n"
            
            text += f"💳 **الحد الائتماني:** {limit_info['max_limit']:,.0f} دينار\n"
            text += f"📊 **المستخدم:** {limit_info['current_used']:,.0f} دينار\n"
            text += f"📈 **المتبقي:** {limit_info['available']:,.0f} دينار\n"
            text += f"🚨 **الحالة:** {limit_info['status']}\n"
            
            text += "────\n\n"
            
            if balance != 0 or limit_info['available'] < limit_info['max_limit']:
                markup.add(types.InlineKeyboardButton(f"📊 كشف حساب {store_name}", callback_data=f"view_my_statement_{seller_id}_{customer_id}"))
    
    text += f"💰 **إجمالي الرصيد:** {total_balance} IQD"
    
    if total_balance > 0:
        text += f"\n📋 **إجمالي المديونيات:** {total_balance} IQD"
    elif total_balance < 0:
        text += f"\n💳 **إجمالي الرصيد الائتماني:** {-total_balance} IQD"
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_statement_"))
def handle_view_my_statement(call):
    parts = call.data.split("_")
    seller_id = int(parts[3])
    customer_id = int(parts[4])
    
    seller = get_seller_by_id(seller_id)
    if not seller:
        bot.answer_callback_query(call.id, "المتجر غير موجود")
        return
    
    statement = get_customer_statement(customer_id, seller_id, limit=15)
    
    if not statement:
        bot.answer_callback_query(call.id, "لا توجد معاملات لديك مع هذا المتجر")
        return
    
    current_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    text = f"📊 **كشف حسابك مع المتجر**\n\n"
    text += f"🏪 المتجر: {seller[3]}\n"
    text += f"💰 الرصيد الحالي: {current_balance} IQD\n"
    text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 الحالة: {limit_info['status']}\n\n"
    text += f"📋 **آخر 15 معاملة:**\n\n"
    
    for trans in statement:
        trans_type, amount, description, balance_before, balance_after, trans_date = trans
        
        trans_type_arabic = {
            'purchase': 'شراء',
            'payment': 'دفعة',
            'adjustment': 'تعديل'
        }.get(trans_type, trans_type)
        
        emoji = "🛒" if trans_type == 'purchase' else "💰" if trans_type == 'payment' else "📝"
        
        text += f"{emoji} **{trans_type_arabic}**\n"
        text += f"📅 {trans_date}\n"
        text += f"💵 المبلغ: {amount} IQD\n"
        
        if description:
            text += f"📝 {description}\n"
        
        text += f"💰 الرصيد: {balance_after} IQD\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_my_credit"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_my_credit")
def handle_back_to_my_credit(call):
    my_credit_statement(call.message)
    bot.answer_callback_query(call.id)

# ====== معالجة Callback Queries العامة ======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data.startswith("copy_store_link_"):
            handle_copy_store_link(call)
        elif call.data == "create_admin_store":
            handle_create_admin_store(call)
        elif call.data == "admin_mode_only":
            handle_admin_mode_only(call)
        elif call.data == "list_active_stores":
            list_active_stores_callback(call)
        elif call.data == "list_suspended_stores":
            list_suspended_stores_callback(call)
        elif call.data == "suspend_store_menu":
            suspend_store_menu(call)
        elif call.data.startswith("suspend_store_"):
            suspend_store_selected(call)
        elif call.data == "activate_store_menu":
            activate_store_menu(call)
        elif call.data.startswith("activate_store_"):
            activate_store_selected(call)
        elif call.data == "add_new_category":
            handle_add_new_category(call)
        elif call.data == "go_to_edit_category":
            handle_go_to_edit_category(call)
        elif call.data.startswith("edit_cat_"):
            handle_edit_category(call)
        elif call.data.startswith("select_category_"):
            handle_select_category_for_product(call)
        elif call.data.startswith("edit_product_"):
            handle_select_product_to_edit(call)
        elif call.data.startswith("edit_prod_"):
            handle_edit_product_field(call)
        elif call.data.startswith("select_new_cat_"):
            handle_select_new_category(call)
        elif call.data == "back_to_menu":
            handle_back_to_menu(call)
        elif call.data == "back_to_edit_product":
            handle_back_to_edit_product(call)
        elif call.data.startswith("contact_buyer_"):
            handle_contact_buyer(call)
        elif call.data.startswith("order_details_"):
            handle_order_details(call)
        elif call.data.startswith("confirm_order_"):
            handle_confirm_order_seller(call)
        elif call.data.startswith("ship_order_"):
            handle_ship_order(call)
        elif call.data.startswith("deliver_order_"):
            handle_deliver_order(call)
        elif call.data.startswith("reject_order_"):
            handle_reject_order(call)
        elif call.data.startswith("view_return_"):
            handle_view_return(call)
        elif call.data.startswith("approve_return_"):
            handle_approve_return(call)
        elif call.data.startswith("reject_return_"):
            handle_reject_return(call)
        elif call.data.startswith("viewstore_"):
            handle_view_store(call)
        elif call.data.startswith("viewcat_"):
            handle_view_category(call)
        elif call.data.startswith("addtocart_"):
            handle_add_to_cart(call)
        elif call.data == "back_to_returns":
            handle_back_to_returns(call)
        elif call.data.startswith("return_details_"):
            handle_return_details(call)
        elif call.data.startswith("process_return_"):
            handle_process_return(call)
        elif call.data == "checkout_cart":
            handle_checkout_cart(call)
        elif call.data == "clear_cart":
            handle_clear_cart(call)
        elif call.data == "edit_cart_quantities":
            handle_edit_cart_quantities(call)
        elif call.data.startswith("increase_cart_"):
            handle_increase_cart(call)
        elif call.data.startswith("decrease_cart_"):
            handle_decrease_cart(call)
        elif call.data.startswith("remove_cart_"):
            handle_remove_cart(call)
        elif call.data.startswith("set_quantity_"):
            handle_set_quantity(call)
        elif call.data in ["edit_name", "edit_phone"]:
            handle_edit_user_info(call)
        else:
            bot.answer_callback_query(call.id, "هذا الزر غير نشط حالياً")
    except Exception as e:
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

def list_active_stores_callback(call):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, 
               CASE WHEN s.Status = 'active' THEN '✅' ELSE '⏸️' END as StatusIcon
        FROM Sellers s
        WHERE s.Status = 'active'
        ORDER BY s.StoreName
    """)
    stores = cursor.fetchall()
    conn.close()
    
    if not stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر نشطة")
        return
    
    text = "📋 **قائمة المتاجر النشطة**\n\n"
    
    for store in stores:
        seller_id, telegram_id, username, store_name, created_at, status = store[:6]
        status_icon = store[6] if len(store) > 6 else ""
        
        text += f"{status_icon} **المتجر:** {store_name}\n"
        text += f"👤 {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📅 تاريخ الإنشاء: {created_at}\n"
        text += "────\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def list_suspended_stores_callback(call):
    suspended_stores = get_suspended_sellers()
    
    if not suspended_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر معلقة")
        return
    
    text = "⚠️ **قائمة المتاجر المعلقة**\n\n"
    
    for store in suspended_stores:
        seller_id, telegram_id, username, store_name = store[:4]
        reason = store[6] if store[6] else "غير محدد"
        suspended_at = store[8]
        suspender_name = store[9] if store[9] else "غير معروف"
        
        text += f"⏸️ **المتجر:** {store_name}\n"
        text += f"👤 {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📋 السبب: {reason}\n"
        text += f"👮 معلق بواسطة: {suspender_name}\n"
        text += f"⏰ تاريخ التعليق: {suspended_at}\n"
        text += "────\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def suspend_store_menu(call):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.SellerID, s.StoreName, s.UserName, s.TelegramID
        FROM Sellers s
        WHERE s.Status = 'active'
        ORDER BY s.StoreName
    """)
    active_stores = cursor.fetchall()
    conn.close()
    
    if not active_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر نشطة")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for store in active_stores:
        store_id, store_name, username, telegram_id = store
        label = f"{store_name} - {format_seller_mention(username, telegram_id)}"
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"suspend_store_{store_id}"
        ))
    
    bot.send_message(call.message.chat.id, "⚠️ **اختر المتجر لتعليقه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

def suspend_store_selected(call):
    store_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "suspend_store_reason",
        "store_id": store_id
    }
    
    bot.send_message(call.message.chat.id,
                    "📝 **سبب التعليق**\n\n"
                    "يرجى إدخال سبب تعليق المتجر:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "suspend_store_reason")
def process_suspend_reason(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    store_id = state["store_id"]
    reason = message.text
    
    suspend_seller(store_id, user_id, reason)
    
    bot.send_message(message.chat.id, f"✅ تم تعليق المتجر بنجاح")
    
    del user_states[user_id]
    
    if is_bot_admin(message.from_user.id):
        show_bot_admin_menu(message)
    else:
        show_admin_dashboard(message)

def activate_store_menu(call):
    suspended_stores = get_suspended_sellers()
    
    if not suspended_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر معلقة")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for store in suspended_stores:
        store_id = store[0]
        store_name = store[3]
        username = store[2]
        reason = store[6] if store[6] else "غير محدد"
        
        label = f"{store_name} - {format_seller_mention(username, store_id)}"
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"activate_store_{store_id}"
        ))
    
    bot.send_message(call.message.chat.id, "▶️ **اختر المتجر لتنشيطه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

def activate_store_selected(call):
    store_id = int(call.data.split("_")[2])
    
    activate_seller(store_id, call.from_user.id)
    
    bot.answer_callback_query(call.id, "✅ تم تنشيط المتجر بنجاح")
    
    bot.send_message(call.message.chat.id, "✅ تم تنشيط المتجر بنجاح")

# ====== معالجة المتاجر والعرض ======
def send_store_catalog_by_telegram_id(chat_id, seller_telegram_id):
    """إرسال كتالوج المتجر"""
    seller = get_seller_by_telegram(seller_telegram_id)
    
    if not seller or seller[5] != 'active':
        bot.send_message(chat_id, "⚠️ المتجر غير موجود أو معطل حالياً.")
        return
    
    seller_id = seller[0]
    store_name = seller[3]
    username = seller[2] or "بائع"
    is_admin_store = (seller[1] == BOT_ADMIN_ID)
    
    categories = get_categories(seller_id)
    
    if not categories:
        products = get_products(seller_id=seller_id)
        if not products:
            bot.send_message(chat_id, f"🏪 **{store_name}**\n👤 البائع: {format_seller_mention(username, seller_id)}\n\nالمتجر فارغ حالياً.")
            return
        
        bot.send_message(chat_id, f"🏪 **{store_name}**\n👤 البائع: {format_seller_mention(username, seller_id)}\n\n🛍️ المنتجات المتاحة:")
        
        for product in products:
            pid, name, desc, price, wholesale_price, qty, img_path = product
            if qty > 0:
                markup = types.InlineKeyboardMarkup()
                # Do not allow adding admin store products to cart
                if not is_admin_store:
                    markup.add(types.InlineKeyboardButton("🛒 أضف إلى السلة", callback_data=f"addtocart_{pid}"))

                send_product_with_image(chat_id, product, markup, store_name)
    else:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            markup.add(types.InlineKeyboardButton(cat_name, callback_data=f"viewcat_{cat_id}_{seller_id}"))
        
        seller_display = format_seller_mention(username, seller_id)
        bot.send_message(chat_id, 
            f"🏪 **{store_name}**\n👤 البائع: {seller_display}\n\n📁 اختر القسم:", 
            reply_markup=markup, 
            parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "تصفح المتاجر 🛍️")
def browse_stores(message):
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    telegram_id = message.from_user.id
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    
    if is_guest:
        # عرض المتاجر للزوار
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TelegramID, UserName, StoreName 
            FROM Sellers 
            WHERE Status = 'active'
            ORDER BY StoreName
        """)
        sellers = cursor.fetchall()
        conn.close()
        
        if not sellers:
            bot.send_message(message.chat.id, "لا توجد متاجر متاحة حالياً.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for seller in sellers:
            telegram_id, username, store_name = seller
            label = f"🏪 {store_name} - {format_seller_mention(username, telegram_id)}"
            markup.add(types.InlineKeyboardButton(
                label, 
                callback_data=f"viewstore_{telegram_id}"
            ))
        
        bot.send_message(message.chat.id, "🛍️ **المتاجر المتاحة:**", reply_markup=markup)
    else:
        # عرض المتاجر للمستخدمين المسجلين
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TelegramID, UserName, StoreName 
            FROM Sellers 
            WHERE Status = 'active'
            ORDER BY StoreName
        """)
        sellers = cursor.fetchall()
        conn.close()
        
        if not sellers:
            bot.send_message(message.chat.id, "لا توجد متاجر متاحة حالياً.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for seller in sellers:
            telegram_id, username, store_name = seller
            label = f"🏪 {store_name} - {format_seller_mention(username, telegram_id)}"
            markup.add(types.InlineKeyboardButton(
                label, 
                callback_data=f"viewstore_{telegram_id}"
            ))
        
        bot.send_message(message.chat.id, "🛍️ **المتاجر المتاحة:**", reply_markup=markup)

def handle_view_store(call):
    try:
        telegram_id = int(call.data.split("_")[1])
        send_store_catalog_by_telegram_id(call.message.chat.id, telegram_id)
        bot.answer_callback_query(call.id)
    except:
        bot.answer_callback_query(call.id, "خطأ في عرض المتجر")

def handle_view_category(call):
    try:
        parts = call.data.split("_")
        category_id = int(parts[1])
        seller_id = int(parts[2])
        
        category = get_category_by_id(category_id)
        if not category:
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
        
        products = get_products(seller_id=seller_id, category_id=category_id)
        
        if not products:
            bot.send_message(call.message.chat.id, f"📦 لا توجد منتجات في قسم {category[2]}")
            bot.answer_callback_query(call.id)
            return
        
        seller = get_seller_by_id(seller_id)
        seller_name = seller[3] if seller else "المتجر"
        is_admin_store = (seller[1] == BOT_ADMIN_ID) if seller else False
        
        text = f"📁 **قسم: {category[2]}**\n🏪 {seller_name}\n\n🛍️ المنتجات المتاحة:\n\n"
        
        for product in products:
            pid, name, desc, price, wholesale_price, qty, img_path = product
            if qty > 0:
                markup = types.InlineKeyboardMarkup()
                if not is_admin_store:
                    markup.add(types.InlineKeyboardButton("🛒 أضف إلى السلة", callback_data=f"addtocart_{pid}"))

                send_product_with_image(call.message.chat.id, product, markup, seller_name)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_view_category: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("addtocart_"))
def handle_add_to_cart(call):
    try:
        product_id = int(call.data.split("_")[1])
        user_id = call.from_user.id
        
        # ====== التعديل: إزالة شرط التحقق من نوع المستخدم ======
        # يمكن لأي مستخدم (زائر، مشتري، بائع، أدمن) إضافة منتجات للسلة
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return

        # منع الشراء من متجر الأدمن
        seller_id = product[1]
        seller = get_seller_by_id(seller_id)
        if seller and seller[1] == BOT_ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ لا يمكن الشراء من متجر الإدارة")
            return
        
        if product[7] <= 0:
            bot.answer_callback_query(call.id, "⛔ المنتج غير متوفر حالياً")
            return
        
        # الحصول على سعر المنتج المناسب للزبون
        seller_id = product[1]
        phone = None
        full_name = None
        
        # فقط للمستخدمين المسجلين، نحاول الحصول على معلوماتهم
        user = get_user(user_id)
        if user:
            phone = user[4] if user else None
            full_name = user[5] if user else None
        
        price = get_product_price_for_customer(product_id, seller_id, phone, full_name)
        
        add_to_cart_db(user_id, product_id, 1, price)
        
        product_name = product[3]
        bot.answer_callback_query(call.id, f"✅ تمت إضافة {product_name} إلى السلة")
        
    except Exception as e:
        print(f"Error in handle_add_to_cart: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في إضافة المنتج للسلة")

# ====== إدارة السلة ======
@bot.message_handler(func=lambda message: message.text == "سلة المشتريات 🛒")
def view_cart(message, user_id=None):
    try:
        telegram_id = user_id if user_id else message.from_user.id
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        # if not is_guest:
        #     # للمستخدمين المسجلين، التحقق من نوع المستخدم
        #     user = get_user(telegram_id)
        #     if not user or user[3] != 'buyer':
        #         # bot.send_message(message.chat.id, "⛔ يجب أن تكون مشترياً لعرض السلة")
        #         pass
        
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.send_message(message.chat.id, "🛒 **سلة المشتريات**\n\nالسلة فارغة حالياً.")
            return
        
        total = 0
        items_by_seller = {}
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            item_total = price * quantity
            total += item_total
            
            if seller_id not in items_by_seller:
                items_by_seller[seller_id] = {
                    'seller_name': seller_name,
                    'items': [],
                    'subtotal': 0
                }
            
            items_by_seller[seller_id]['items'].append(item)
            items_by_seller[seller_id]['subtotal'] += item_total
        
        text = f"🛒 **سلة المشتريات**\n\n"
        text += f"📋 عدد المنتجات: {len(cart_items)}\n"
        text += f"💰 الإجمالي: {total:,.0f} IQD\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ إنهاء الطلب", callback_data="checkout_cart"),
            types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"),
            types.InlineKeyboardButton("✏️ تعديل الكميات", callback_data="edit_cart_quantities")
        )
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        
        # إرسال كل عنصر في السلة مع صورته
        for seller_id, seller_data in items_by_seller.items():
            # seller_text = f"🏪 **{seller_data['seller_name']}**\n\n"
            
            for item in seller_data['items']:
                product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
                # item_total = price * quantity
                
                item_markup = types.InlineKeyboardMarkup(row_width=2)
                item_markup.add(
                    types.InlineKeyboardButton("➕ زيادة", callback_data=f"increase_cart_{product_id}"),
                    types.InlineKeyboardButton("➖ تقليل", callback_data=f"decrease_cart_{product_id}"),
                    types.InlineKeyboardButton("🗑️ حذف", callback_data=f"remove_cart_{product_id}")
                )
                
                send_cart_item_with_image(message.chat.id, item, item_markup)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض السلة:\n{str(e)}")
        traceback.print_exc()

@bot.callback_query_handler(func=lambda call: call.data == "checkout_cart")
def handle_checkout_cart(call):
    try:
        telegram_id = call.from_user.id
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.answer_callback_query(call.id, "السلة فارغة")
            return

        # إزالة منتجات متجر الأدمن من السلة إن وُجدت
        cleaned_cart = []
        removed_any = False
        for item in cart_items:
            pid = item[0]
            prod = get_product_by_id(pid)
            if not prod:
                continue
            prod_seller_id = prod[1]
            seller = get_seller_by_id(prod_seller_id)
            if seller and seller[1] == BOT_ADMIN_ID:
                # حذف من السلة
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID= ?", (telegram_id, pid))
                conn.commit()
                conn.close()
                removed_any = True
                continue
            cleaned_cart.append(item)

        if removed_any:
            bot.answer_callback_query(call.id, "⚠️ تمت إزالة منتجات من متجر الإدارة من السلة")

        if not cleaned_cart:
            bot.send_message(call.message.chat.id, "⛔ السلة لا تحتوي على منتجات قابلة للشراء حالياً.")
            return

        # استخدم cleaned_cart للمتابعة
        cart_items = cleaned_cart
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        if is_guest:
            # للزوار، نطلب منهم إدخال معلوماتهم أولاً
            user_states[telegram_id] = {
                "step": "guest_checkout_info",
                "is_guest": True,
                "cart_items": cart_items
            }
            
            bot.send_message(call.message.chat.id,
                            "📝 **معلومات الزائر**\n\n"
                            "بما أنك زائر (غير مسجل)، نحتاج لمعلوماتك لإتمام الطلب.\n\n"
                            "يرجى إدخال اسمك الكامل:")
            
            bot.answer_callback_query(call.id)
            return
        
        items_by_seller = {}
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            
            if seller_id not in items_by_seller:
                items_by_seller[seller_id] = {
                    'seller_name': seller_name,
                    'items': [],
                    'subtotal': 0
                }
            
            items_by_seller[seller_id]['items'].append((product_id, quantity, price))
            items_by_seller[seller_id]['subtotal'] += price * quantity
        
        user_states[telegram_id] = {
            "step": "checkout_select_seller",
            "items_by_seller": items_by_seller,
            "current_seller_index": 0
        }
        
        seller_ids = list(items_by_seller.keys())
        first_seller_id = seller_ids[0]
        first_seller_data = items_by_seller[first_seller_id]
        
        start_checkout_for_seller(call.message, telegram_id, first_seller_id, first_seller_data)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        bot.send_message(call.message.chat.id, f"⚠️ خطأ في إتمام الطلب: {e}")
        traceback.print_exc()

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "guest_checkout_info")
def process_guest_checkout_info(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return
    
    state["guest_name"] = full_name
    state["step"] = "guest_checkout_phone"
    
    bot.send_message(message.chat.id,
                    "📞 **رقم الهاتف**\n\n"
                    "يرجى إدخال رقم هاتفك للتواصل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم يكن هناك رقم هاتف.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "guest_checkout_phone")
def process_guest_checkout_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    phone = message.text.strip()
    if phone.lower() == "تخطي":
        phone = None
    
    state["guest_phone"] = phone
    
    # تحويل عناصر السلة إلى تنسيق مناسب
    cart_items = state["cart_items"]
    items_by_seller = {}
    
    for item in cart_items:
        product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
        
        if seller_id not in items_by_seller:
            items_by_seller[seller_id] = {
                'seller_name': seller_name,
                'items': [],
                'subtotal': 0
            }
        
        items_by_seller[seller_id]['items'].append((product_id, quantity, price))
        items_by_seller[seller_id]['subtotal'] += price * quantity
    
    # تحديث حالة المستخدم
    state["step"] = "checkout_select_seller"
    state["items_by_seller"] = items_by_seller
    state["current_seller_index"] = 0
    state["is_guest"] = True
    
    seller_ids = list(items_by_seller.keys())
    first_seller_id = seller_ids[0]
    first_seller_data = items_by_seller[first_seller_id]
    
    start_checkout_for_seller(message, telegram_id, first_seller_id, first_seller_data)

def start_checkout_for_seller(message, user_id, seller_id, seller_data):
    seller = get_seller_by_id(seller_id)
    seller_name = seller[3] if seller else seller_data['seller_name']
    
    subtotal = seller_data['subtotal']
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = user_id in user_states and user_states.get(user_id, {}).get('is_guest', False)
    
    if is_guest:
        text = f"🏪 **إنهاء طلب من المتجر**\n\n"
        text += f"المتجر: {seller_name}\n"
        text += f"💰 المجموع: {subtotal} IQD\n\n"
        text += "🔸 **وضع الزائر:**\n"
        text += "• يمكنك الشراء نقداً فقط\n"
        text += "• لا يمكنك الشراء على الحساب\n"
        text += "• لن يتم حفظ سجل طلباتك\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💵 الدفع نقداً", callback_data=f"payment_cash_{seller_id}"),
            types.InlineKeyboardButton("❌ إلغاء الطلب من هذا المتجر", callback_data=f"skip_seller_{seller_id}")
        )
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        return
    
    # للمستخدمين المسجلين (الكود القديم)
    # التحقق إذا كان الزبون آجلاً
    user_info = get_user(user_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    customer_balance = 0
    limit_info = None
    
    if customer:
        customer_balance = get_customer_balance(customer[0], seller_id)
        limit_info = get_credit_limit_info(customer[0], seller_id)
    
    text = f"🏪 **إنهاء طلب من المتجر**\n\n"
    text += f"المتجر: {seller_name}\n"
    text += f"💰 المجموع: {subtotal} IQD\n"
    
    if customer:
        text += f"💰 رصيدك الآجل: {customer_balance} IQD\n"
        
        if limit_info:
            text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
            text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
            text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
            text += f"🚨 الحالة: {limit_info['status']}\n"
        
        # التحقق من الحد الائتماني
        can_purchase, message_text, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, subtotal)
        
        if not can_purchase:
            text += f"\n❌ **تحذير:** {message_text}\n"
        elif "تحذير" in message_text:
            text += f"\n⚠️ **ملاحظة:** {message_text}\n"
        
        if customer_balance > 0:
            text += f"💰 المبلغ المتبقي بعد خصم الرصيد: {max(0, subtotal - customer_balance)} IQD\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if customer and customer_balance >= subtotal:
        markup.add(
            types.InlineKeyboardButton("💵 الدفع نقداً", callback_data=f"payment_cash_{seller_id}"),
            types.InlineKeyboardButton("💳 الشراء على الحساب", callback_data=f"payment_credit_{seller_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("💵 الدفع نقداً", callback_data=f"payment_cash_{seller_id}"),
            types.InlineKeyboardButton("💳 الشراء على الحساب", callback_data=f"payment_credit_{seller_id}")
        )
    
    markup.add(types.InlineKeyboardButton("❌ إلغاء الطلب من هذا المتجر", callback_data=f"skip_seller_{seller_id}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_cash_"))
def handle_payment_cash(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = state.get('is_guest', False)
    
    if is_guest:
        # للزوار، لا يوجد رصيد آجل
        user_states[telegram_id]["current_seller_payment"] = "cash"
        user_states[telegram_id]["current_seller_id"] = seller_id
        user_states[telegram_id]["fully_paid"] = True
        
        bot.send_message(call.message.chat.id,
                        "📦 **معلومات التوصيل**\n\n"
                        "يرجى إدخال عنوان التوصيل (اختياري):\n"
                        "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
        
        bot.answer_callback_query(call.id)
        return
    
    # للمستخدمين المسجلين (الكود القديم)
    # التحقق إذا كان الزبون آجلاً
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if customer:
        customer_balance = get_customer_balance(customer[0], seller_id)
        subtotal = seller_data['subtotal']
        
        if customer_balance >= subtotal:
            # يمكن الدفع من الرصيد الآجل
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("💵 دفع نقداً كاملاً", callback_data=f"payment_full_cash_{seller_id}"),
                types.InlineKeyboardButton("💳 دفع من الرصيد الآجل", callback_data=f"payment_from_balance_{seller_id}")
            )
            
            bot.send_message(call.message.chat.id,
                            f"💰 **لديك رصيد آجل**\n\n"
                            f"رصيدك الآجل: {customer_balance} IQD\n"
                            f"قيمة الطلب: {subtotal} IQD\n\n"
                            f"اختر طريقة الدفع:",
                            reply_markup=markup)
            bot.answer_callback_query(call.id)
            return
    
    user_states[telegram_id]["current_seller_payment"] = "cash"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_full_cash_"))
def handle_payment_full_cash(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "cash"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_from_balance_"))
def handle_payment_from_balance(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    subtotal = seller_data['subtotal']
    
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if not customer:
        bot.answer_callback_query(call.id, "أنت لست زبوناً آجلاً")
        return
    
    customer_balance = get_customer_balance(customer[0], seller_id)
    
    if customer_balance < subtotal:
        bot.answer_callback_query(call.id, "رصيدك الآجل غير كافٍ")
        return
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    user_states[telegram_id]["use_balance"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_credit_"))
def handle_payment_credit(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    if telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest'):
        bot.answer_callback_query(call.id, "⛔ الزوار لا يمكنهم الشراء على الحساب")
        return
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    seller = get_seller_by_id(seller_id)
    if not seller:
        bot.answer_callback_query(call.id, "المتجر غير موجود")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    subtotal = seller_data['subtotal']
    
    # التحقق إذا كان الزبون آجلاً
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if not customer:
        bot.answer_callback_query(call.id, "⛔ يجب أن تكون زبوناً آجلاً للشراء على الحساب")
        return
    
    # التحقق من الحد الائتماني
    can_purchase, message_text, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, subtotal)
    
    if not can_purchase:
        bot.answer_callback_query(call.id, message_text)
        return
    
    current_balance = get_customer_balance(customer[0], seller_id)
    new_balance = current_balance + subtotal
    
    confirm_text = f"💳 **الشراء على الحساب**\n\n"
    confirm_text += f"المتجر: {seller[3]}\n"
    confirm_text += f"💰 قيمة الطلب: {subtotal} IQD\n"
    confirm_text += f"💰 رصيدك الحالي: {current_balance} IQD\n"
    confirm_text += f"💰 رصيدك بعد الشراء: {new_balance} IQD\n"
    confirm_text += f"💳 الحد المتبقي: {remaining:,.0f} دينار\n\n"
    
    if message_text and "تحذير" in message_text:
        confirm_text += f"⚠️ **ملاحظة:** {message_text}\n\n"
    
    if current_balance >= subtotal:
        confirm_text += f"💡 **ملاحظة:** لديك رصيد كافٍ لتغطية الطلب. هل تريد الدفع من الرصيد الآجل؟\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💳 دفع من الرصيد", callback_data=f"pay_from_balance_{seller_id}"),
            types.InlineKeyboardButton("📝 إضافة للدين", callback_data=f"add_to_credit_{seller_id}")
        )
        
        bot.send_message(call.message.chat.id, confirm_text, reply_markup=markup, parse_mode='Markdown')
    else:
        confirm_text += f"هل تريد إضافة هذا المبلغ للدين؟"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ نعم، إضافة للدين", callback_data=f"add_to_credit_{seller_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_checkout")
        )
        
        bot.send_message(call.message.chat.id, confirm_text, reply_markup=markup, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_from_balance_"))
def handle_pay_from_balance(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    user_states[telegram_id]["use_balance"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_credit_"))
def handle_add_to_credit(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = False
    user_states[telegram_id]["use_balance"] = False
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("skip_seller_"))
def handle_skip_seller(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    
    # حذف عناصر هذا البائع من السلة
    seller_items = state["items_by_seller"][seller_id]['items']
    for product_id, quantity, price in seller_items:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
    
    # حذف البائع من القائمة
    del state["items_by_seller"][seller_id]
    
    if not state["items_by_seller"]:
        bot.send_message(call.message.chat.id, "✅ تم إلغاء جميع الطلبات")
        del user_states[telegram_id]
        show_buyer_main_menu(call.message)
    else:
        seller_ids = list(state["items_by_seller"].keys())
        next_seller_id = seller_ids[0]
        next_seller_data = state["items_by_seller"][next_seller_id]
        
        start_checkout_for_seller(call.message, telegram_id, next_seller_id, next_seller_data)
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     "current_seller_payment" in user_states[message.from_user.id])
def process_delivery_address(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    delivery_address = message.text.strip()
    if delivery_address.lower() == 'تخطي':
        delivery_address = None
    
    seller_id = state["current_seller_id"]
    payment_method = state["current_seller_payment"]
    seller_data = state["items_by_seller"][seller_id]
    fully_paid = state.get("fully_paid", False)
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = state.get('is_guest', False)
    
    if is_guest:
        # للزوار، إنشاء طلب خاص
        guest_name = state.get("guest_name", "زائر")
        guest_phone = state.get("guest_phone")
        
        # إنشاء طلب للزائر
        order_id, total = create_order_for_guest(
            telegram_id, 
            seller_id, 
            seller_data['items'], 
            delivery_address, 
            guest_name, 
            guest_phone, 
            payment_method, 
            fully_paid
        )
        
        if order_id is None:
            bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {total}")
            # حذف البائع من القائمة ومتابعة مع البائع التالي
            del state["items_by_seller"][seller_id]
            
            if state["items_by_seller"]:
                seller_ids = list(state["items_by_seller"].keys())
                next_seller_id = seller_ids[0]
                next_seller_data = state["items_by_seller"][next_seller_id]
                
                start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
            else:
                del user_states[telegram_id]
                browse_without_registration(message)
            return
    else:
        # للمستخدمين المسجلين (الكود القديم)
        # التحقق من الحد الائتماني إذا كان الشراء على الحساب
        if payment_method == 'credit' and not fully_paid:
            user_info = get_user(telegram_id)
            if user_info:
                customer = get_credit_customer(seller_id, user_info[4], user_info[5])
                if customer:
                    subtotal = seller_data['subtotal']
                    can_purchase, message_text, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, subtotal)
                    
                    if not can_purchase:
                        bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {message_text}")
                        # حذف البائع من القائمة ومتابعة مع البائع التالي
                        del state["items_by_seller"][seller_id]
                        
                        if state["items_by_seller"]:
                            seller_ids = list(state["items_by_seller"].keys())
                            next_seller_id = seller_ids[0]
                            next_seller_data = state["items_by_seller"][next_seller_id]
                            
                            start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
                        else:
                            del user_states[telegram_id]
                            show_buyer_main_menu(message)
                        return
        
        # إنشاء الطلب
        order_id, total = create_order(
            telegram_id, 
            seller_id, 
            seller_data['items'], 
            delivery_address, 
            None, 
            payment_method, 
            fully_paid
        )
        
        if order_id is None:
            # فشل إنشاء الطلب بسبب الحد الائتماني
            bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {total}")
            # حذف البائع من القائمة ومتابعة مع البائع التالي
            del state["items_by_seller"][seller_id]
            
            if state["items_by_seller"]:
                seller_ids = list(state["items_by_seller"].keys())
                next_seller_id = seller_ids[0]
                next_seller_data = state["items_by_seller"][next_seller_id]
                
                start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
            else:
                del user_states[telegram_id]
                show_buyer_main_menu(message)
            return
    
    # حذف عناصر هذا البائع من السلة
    for product_id, quantity, price in seller_data['items']:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
    
    # حذف البائع من القائمة
    del state["items_by_seller"][seller_id]
    
    seller = get_seller_by_id(seller_id)
    seller_name = seller[3] if seller else "المتجر"
    
    bot.send_message(message.chat.id,
                    f"✅ **تم إنشاء الطلب بنجاح!**\n\n"
                    f"🆔 رقم الطلب: {order_id}\n"
                    f"🏪 المتجر: {seller_name}\n"
                    f"💰 الإجمالي: {total} IQD\n"
                    f"💳 طريقة الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'}\n"
                    f"💵 حالة الدفع: {'مدفوع بالكامل' if fully_paid else 'غير مدفوع بالكامل'}\n\n"
                    f"سيقوم البائع بالتواصل معك قريباً.")
    
    # الانتقال للبائع التالي إن وجد
    if state["items_by_seller"]:
        seller_ids = list(state["items_by_seller"].keys())
        next_seller_id = seller_ids[0]
        next_seller_data = state["items_by_seller"][next_seller_id]
        
        start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
    else:
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        if is_guest:
            del user_states[telegram_id]
            browse_without_registration(message)
        else:
            del user_states[telegram_id]
            show_buyer_main_menu(message)

def create_order_for_guest(buyer_id, seller_id, cart_items, delivery_address=None, guest_name=None, guest_phone=None, payment_method='cash', fully_paid=False):
    """إنشاء طلب للزوار (غير المسجلين)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    total = 0
    
    for pid, qty, price in cart_items:
        total += price * qty

    # إضافة مستخدم مؤقت للزائر
    temp_user_id = f"guest_{buyer_id}_{int(time.time())}"
    
    # إدراج طلب مع معلومات الزائر
    cursor.execute("""
        INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (temp_user_id, seller_id, total, delivery_address, f"زائر: {guest_name} - {guest_phone}", payment_method, fully_paid))
    
    order_id = cursor.lastrowid

    for pid, qty, price in cart_items:
        product = get_product_by_id(pid)
        if not product:
            continue
        cursor.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                       (order_id, pid, qty, price))
        new_qty = product[7] - qty
        if new_qty < 0:
            new_qty = 0
        cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
    
    conn.commit()
    conn.close()
    
    notify_seller_of_order(order_id, temp_user_id, seller_id)
    return order_id, total

@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def handle_clear_cart(call):
    try:
        telegram_id = call.from_user.id
        clear_cart_db(telegram_id)
        
        bot.answer_callback_query(call.id, "✅ تم تفريغ السلة")
        bot.send_message(call.message.chat.id, "✅ تم تفريغ سلة المشتريات بنجاح.")
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        if is_guest:
            browse_without_registration(call.message)
        else:
            show_buyer_main_menu(call.message)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in clear_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "edit_cart_quantities")
def handle_edit_cart_quantities(call):
    try:
        telegram_id = call.from_user.id
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.answer_callback_query(call.id, "السلة فارغة")
            return
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton(f"الكمية: {quantity}", callback_data=f"set_quantity_{product_id}"),
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️ حذف", callback_data=f"remove_cart_{product_id}")
            )
            
            caption = f"🛒 **{name}**\n💰 السعر: {price} IQD\n📦 الكمية: {quantity}\n💰 المجموع: {price * quantity} IQD\n🏪 {seller_name}"
            
            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                except:
                    bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in edit_cart_quantities: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("increase_cart_"))
def handle_increase_cart(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        cart_items = get_cart_items_db(telegram_id)
        current_quantity = 0
        current_price = 0
        
        for item in cart_items:
            if item[0] == product_id:
                current_quantity = item[1]
                current_price = item[2]
                break
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return
        
        available_qty = product[7]
        
        if current_quantity >= available_qty:
            bot.answer_callback_query(call.id, f"⚠️ الحد الأقصى للكمية المتاحة: {available_qty}")
            return
        
        add_to_cart_db(telegram_id, product_id, 1, current_price)
        bot.answer_callback_query(call.id, "✅ تم زيادة الكمية")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        view_cart(call.message, user_id=telegram_id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        # bot.send_message(call.message.chat.id, f"Error: {e}")
        print(f"Error in increase_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("decrease_cart_"))
def handle_decrease_cart(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        cart_items = get_cart_items_db(telegram_id)
        current_quantity = 0
        
        for item in cart_items:
            if item[0] == product_id:
                current_quantity = item[1]
                break
        
        if current_quantity <= 1:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "✅ تم حذف المنتج من السلة")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE Carts SET Quantity = Quantity - 1 WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "✅ تم تقليل الكمية")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        view_cart(call.message, user_id=telegram_id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in decrease_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_cart_"))
def handle_remove_cart(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ تم حذف المنتج من السلة")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        view_cart(call.message, user_id=telegram_id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in remove_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_quantity_"))
def handle_set_quantity(call):
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    user_states[telegram_id] = {
        "step": "set_cart_quantity",
        "product_id": product_id
    }
    
    bot.send_message(call.message.chat.id,
                    "📦 **تحديد الكمية**\n\n"
                    "يرجى إدخال الكمية الجديدة:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "set_cart_quantity")
def process_set_cart_quantity(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    product_id = state["product_id"]
    
    try:
        new_quantity = int(message.text)
        if new_quantity <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    product = get_product_by_id(product_id)
    if not product:
        bot.send_message(message.chat.id, "المنتج غير موجود")
        del user_states[telegram_id]
        return
    
    available_qty = product[7]
    
    if new_quantity > available_qty:
        bot.send_message(message.chat.id, f"⚠️ الحد الأقصى للكمية المتاحة: {available_qty}")
        del user_states[telegram_id]
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Carts SET Quantity = ? WHERE UserID=? AND ProductID=?", 
                  (new_quantity, telegram_id, product_id))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ تم تحديث الكمية إلى {new_quantity}")
    
    del user_states[telegram_id]
    view_cart(message, user_id=telegram_id)

# ====== نظام الرسائل ======
@bot.message_handler(func=lambda message: "📩 الرسائل" in message.text and is_seller(message.from_user.id))
def seller_messages(message):
    telegram_id = message.from_user.id
    
    if not is_seller_active(telegram_id):
        bot.send_message(message.chat.id,
                        "⛔ **حسابك معطل**\n\n"
                        "لا يمكنك الوصول إلى الرسائل لأن حسابك معطل.")
        return
    
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    unread_messages = get_unread_messages(seller[0])
    
    if not unread_messages:
        bot.send_message(message.chat.id, "📭 لا توجد رسائل جديدة.")
        return
    
    for msg in unread_messages:
        message_id, order_id, seller_id, msg_type, msg_text, is_read, created_at = msg[:7]
        
        mark_message_as_read(message_id)
        
        markup = types.InlineKeyboardMarkup()
        
        if msg_type == 'new_order':
            markup.add(
                types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{order_id}"),
                types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_order_{order_id}"),
                types.InlineKeyboardButton("📋 تفاصيل الطلب", callback_data=f"order_details_{order_id}")
            )
        elif msg_type == 'return_request':
            markup.add(
                types.InlineKeyboardButton("📋 تفاصيل الإرجاع", callback_data=f"return_details_{message_id}"),
                types.InlineKeyboardButton("✅ معالجة الإرجاع", callback_data=f"process_return_{message_id}")
            )
        
        bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode='Markdown')
    
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(message)
    else:
        show_seller_menu(message)

# ====== معالجة Callback Queries للطلبات ======
def handle_contact_buyer(call):
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    
    buyer_id = int(parts[2])
    buyer_info = get_user(buyer_id)
    
    if not buyer_info:
        bot.answer_callback_query(call.id, "معلومات المشتري غير متوفرة")
        return
    
    buyer_name = buyer_info[5] if buyer_info[5] else buyer_info[2]
    buyer_phone = buyer_info[4] if buyer_info[4] else "غير متوفر"
    buyer_username = f"@{buyer_info[2]}" if buyer_info[2] else "لا يوجد"
    
    text = f"📞 **معلومات الاتصال بالمشتري**\n\n"
    text += f"👤 الاسم: {buyer_name}\n"
    text += f"📞 الهاتف: {buyer_phone}\n"
    text += f"🔗 المعرف: {buyer_username}\n"
    text += f"🆔 الرقم: {buyer_id}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    if buyer_phone != "غير متوفر":
        markup.add(types.InlineKeyboardButton("📞 اتصال فوري", url=f"tel:{buyer_phone}"))
    if buyer_info[2]:
        markup.add(types.InlineKeyboardButton("✉️ مراسلة", url=f"https://t.me/{buyer_info[2]}"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def handle_order_details(call):
    order_id = int(call.data.split("_")[2])
    order_details, items = get_order_details(order_id)
    
    if not order_details:
        bot.answer_callback_query(call.id, "الطلب غير موجود")
        return
    
    text = f"📋 **تفاصيل الطلب #{order_id}**\n\n"
    text += f"👤 المشتري: {order_details[8] if order_details[8] else order_details[9]}\n"
    text += f"📞 الهاتف: {order_details[7] if order_details[7] else 'غير متوفر'}\n"
    text += f"💰 الإجمالي: {order_details[3]} IQD\n"
    text += f"💳 طريقة الدفع: {'نقداً' if order_details[8] == 'cash' else 'على الحساب'}\n"
    text += f"💵 حالة الدفع: {'مدفوع بالكامل' if order_details[9] == 1 else 'غير مدفوع بالكامل'}\n"
    text += f"📊 الحالة: {order_details[4]}\n"
    text += f"📅 التاريخ: {order_details[5]}\n"
    
    if order_details[6]:
        text += f"📍 العنوان: {order_details[6]}\n"
    
    text += f"\n📦 **المنتجات:**\n"
    
    for item in items:
        item_id, order_id, product_id, quantity, price, returned_qty, return_reason, return_date = item[:8]
        product_name = item[8] if len(item) > 8 else "منتج"
        
        text += f"\n🛒 المنتج: {product_name}\n"
        text += f"📦 الكمية: {quantity}"
        
        if returned_qty and returned_qty > 0:
            text += f" (تم إرجاع {returned_qty})"
        
        text += f"\n💰 السعر: {price} IQD\n"
        text += f"💰 المجموع: {quantity * price} IQD\n"
        
        if return_reason:
            text += f"📝 سبب الإرجاع: {return_reason}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_order_{order_id}"),
        types.InlineKeyboardButton("🚚 تم الشحن", callback_data=f"ship_order_{order_id}"),
        types.InlineKeyboardButton("✅ تم التسليم", callback_data=f"deliver_order_{order_id}"),
        types.InlineKeyboardButton("🗑️ رفض الطلب", callback_data=f"reject_order_{order_id}")
    )
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def handle_confirm_order_seller(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Confirmed")
    
    bot.answer_callback_query(call.id, "✅ تم تأكيد الطلب")
    
    order_details, _ = get_order_details(order_id)
    if order_details and order_details[1]:
        try:
            bot.send_message(order_details[1], 
                           f"✅ **تم تأكيد طلبك #{order_id}**\n\n"
                           f"تم تأكيد طلبك من قبل البائع. سيتم تجهيزه قريباً.")
        except:
            pass
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n✅ **تم تأكيد الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
    except:
        pass

def handle_ship_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Shipped")
    
    bot.answer_callback_query(call.id, "🚚 تم تحديث حالة الشحن")
    
    order_details, _ = get_order_details(order_id)
    if order_details and order_details[1]:
        try:
            bot.send_message(order_details[1], 
                           f"🚚 **تم شحن طلبك #{order_id}**\n\n"
                           f"تم شحن طلبك وهو في الطريق إليك.")
        except:
            pass
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n🚚 **تم شحن الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
    except:
        pass

def handle_deliver_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Delivered")
    
    bot.answer_callback_query(call.id, "✅ تم تسليم الطلب")
    
    order_details, _ = get_order_details(order_id)
    if order_details and order_details[1]:
        try:
            bot.send_message(order_details[1], 
                           f"🎉 **تم تسليم طلبك #{order_id}**\n\n"
                           f"تم تسليم طلبك بنجاح. شكراً لثقتك بنا! 💝")
        except:
            pass
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n✅ **تم تسليم الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
    except:
        pass

def handle_reject_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Rejected")
    
    bot.answer_callback_query(call.id, "❌ تم رفض الطلب")
    
    order_details, _ = get_order_details(order_id)
    if order_details and order_details[1]:
        try:
            bot.send_message(order_details[1], 
                           f"❌ **تم رفض طلبك #{order_id}**\n\n"
                           f"نعتذر، تم رفض طلبك من قبل البائع.\n"
                           f"للمزيد من المعلومات، يرجى التواصل مع البائع.")
        except:
            pass
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n❌ **تم رفض الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
    except:
        pass

def handle_view_return(call):
    return_id = int(call.data.split("_")[2])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, p.Name as ProductName, o.OrderID, o.BuyerID, 
               u.FullName, u.PhoneNumber, u.UserName
        FROM Returns r
        JOIN Products p ON r.ProductID = p.ProductID
        JOIN Orders o ON r.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE r.ReturnID = ?
    """, (return_id,))
    
    ret = cursor.fetchone()
    conn.close()
    
    if not ret:
        bot.answer_callback_query(call.id, "طلب الإرجاع غير موجود")
        return
    
    text = f"📦 **طلب إرجاع #{return_id}**\n\n"
    text += f"🆔 رقم الطلب: {ret[2]}\n"
    text += f"👤 المشتري: {ret[10] if ret[10] else ret[12]}\n"
    text += f"📞 الهاتف: {ret[11] if ret[11] else 'غير متوفر'}\n"
    text += f"🛒 المنتج: {ret[8]}\n"
    text += f"📦 الكمية: {ret[4]}\n"
    text += f"📝 السبب: {ret[5]}\n"
    text += f"📊 الحالة: {ret[6]}\n"
    text += f"📅 التاريخ: {ret[7]}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if ret[6] == 'Pending':
        markup.add(
            types.InlineKeyboardButton("✅ قبول الإرجاع", callback_data=f"approve_return_{return_id}"),
            types.InlineKeyboardButton("❌ رفض الإرجاع", callback_data=f"reject_return_{return_id}"),
            types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{ret[9]}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{ret[9]}"),
            types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_returns")
        )
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def handle_return_details(call):
    message_id = int(call.data.split("_")[2])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT OrderID, MessageText FROM Messages WHERE MessageID = ?", (message_id,))
    msg = cursor.fetchone()
    conn.close()
    
    if msg:
        order_id = msg[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 تفاصيل الإرجاع", callback_data=f"view_return_{order_id}"))
        bot.send_message(call.message.chat.id, msg[1], reply_markup=markup, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

def handle_process_return(call):
    message_id = int(call.data.split("_")[2])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT OrderID FROM Messages WHERE MessageID = ?", (message_id,))
    msg = cursor.fetchone()
    conn.close()
    
    if msg:
        order_id = msg[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ معالجة الإرجاع", callback_data=f"approve_return_{order_id}"))
        bot.send_message(call.message.chat.id, f"اختر إجراء للإرجاع للطلب #{order_id}:", reply_markup=markup)
    
    bot.answer_callback_query(call.id)

def handle_approve_return(call):
    return_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "approve_return",
        "return_id": return_id
    }
    
    bot.send_message(call.message.chat.id, 
                    "✅ **قبول طلب الإرجاع**\n\n"
                    "يرجى إدخال ملاحظات إضافية (اختياري):")
    
    bot.answer_callback_query(call.id)

def handle_reject_return(call):
    return_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "reject_return",
        "return_id": return_id
    }
    
    bot.send_message(call.message.chat.id, 
                    "❌ **رفض طلب الإرجاع**\n\n"
                    "يرجى إدخال سبب الرفض:")
    
    bot.answer_callback_query(call.id)

def handle_back_to_returns(call):
    telegram_id = call.from_user.id
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(call.message)
    elif is_seller(telegram_id):
        show_seller_menu(call.message)
    else:
        show_buyer_main_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] in ["approve_return", "reject_return"])
def process_return_decision(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    return_id = state["return_id"]
    action = state["step"]
    
    notes = message.text if message.text else "لا توجد ملاحظات"
    
    if action == "approve_return":
        success, result = process_return_request(return_id, 'Approved', user_id, notes)
        response_text = "✅ تم قبول طلب الإرجاع"
    else:
        success, result = process_return_request(return_id, 'Rejected', user_id, notes)
        response_text = "❌ تم رفض طلب الإرجاع"
    
    if success:
        bot.send_message(message.chat.id, response_text)
    else:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {result}")
    
    del user_states[user_id]

# ====== تعديل بيانات المستخدم ======
@bot.message_handler(func=lambda message: message.text == "👤 تعديل بياناتي")
def edit_user_info(message):
    user = get_user(message.from_user.id)
    
    if not user:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على بياناتك.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data="edit_name"),
        types.InlineKeyboardButton("📞 تعديل الهاتف", callback_data="edit_phone")
    )
    
    bot.send_message(message.chat.id,
                    f"👤 **بياناتك الحالية:**\n\n"
                    f"🆔 المعرف: {user[1]}\n"
                    f"👤 الاسم: {user[5] if user[5] else 'غير محدد'}\n"
                    f"📞 الهاتف: {user[4] if user[4] else 'غير محدد'}\n\n"
                    f"اختر ما تريد تعديله:",
                    reply_markup=markup)

def handle_edit_user_info(call):
    if call.data == "edit_name":
        user_states[call.from_user.id] = {"step": "edit_name"}
        bot.send_message(call.message.chat.id, "✏️ **تعديل الاسم**\n\nيرجى إدخال اسمك الكامل الجديد:")
    else:
        user_states[call.from_user.id] = {"step": "edit_phone"}
        bot.send_message(call.message.chat.id, "📞 **تعديل رقم الهاتف**\n\nيرجى إدخال رقم هاتفك الجديد:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] in ["edit_name", "edit_phone"])
def process_edit_user_info(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    
    if state["step"] == "edit_name":
        new_name = message.text.strip()
        if not new_name:
            bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
            return
        update_user_info(user_id, full_name=new_name)
        bot.send_message(message.chat.id, f"✅ تم تحديث اسمك إلى: {new_name}")
    else:
        new_phone = message.text.strip()
        if not new_phone:
            new_phone = None
        update_user_info(user_id, phone_number=new_phone)
        phone_display = new_phone if new_phone else 'غير محدد'
        bot.send_message(message.chat.id, f"✅ تم تحديث رقم هاتفك إلى: {phone_display}")
    
    del user_states[user_id]
    show_buyer_main_menu(message)

# ====== عرض الطلبات للمشتري ======
@bot.message_handler(func=lambda message: message.text == "📋 طلباتي")
def my_orders(message):
    telegram_id = message.from_user.id
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    
    if is_guest:
        bot.send_message(message.chat.id,
                        "📭 **لا توجد طلبات سابقة**\n\n"
                        "بما أنك زائر (غير مسجل)، لن يتم حفظ سجل طلباتك.\n\n"
                        "💡 **لحفظ طلباتك ومتابعتها:**\n"
                        "1. اختر '👤 تسجيل حساب جديد'\n"
                        "2. سجل معلوماتك\n"
                        "3. ستتمكن من رؤية جميع طلباتك السابقة")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, s.StoreName, s.UserName as SellerUsername
        FROM Orders o
        JOIN Sellers s ON o.SellerID = s.SellerID
        WHERE o.BuyerID = ?
        ORDER BY o.CreatedAt DESC
        LIMIT 20
    """, (telegram_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        bot.send_message(message.chat.id, "📭 لا توجد طلبات سابقة.")
        return
    
    text = "📋 **طلباتي السابقة**\n\n"
    
    for order in orders:
        order_id, buyer_id, seller_id, total, status, created_at, delivery_address, notes, payment_method, fully_paid = order[:10]
        store_name = order[10] if len(order) > 10 else "المتجر"
        
        status_emoji = {
            'Pending': '⏳',
            'Confirmed': '✅',
            'Shipped': '🚚',
            'Delivered': '🎉',
            'Rejected': '❌'
        }.get(status, '📝')
        
        payment_status = "💵 مدفوع" if fully_paid == 1 else "💳 غير مدفوع"
        
        text += f"{status_emoji} **الطلب #{order_id}**\n"
        text += f"🏪 المتجر: {store_name}\n"
        text += f"💰 الإجمالي: {total} IQD\n"
        text += f"💳 الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'} ({payment_status})\n"
        text += f"📊 الحالة: {status}\n"
        text += f"📅 التاريخ: {created_at}\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📋 تفاصيل الطلبات الأخيرة", callback_data="view_recent_orders"),
        types.InlineKeyboardButton("📦 طلب إرجاع", callback_data="request_return")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "view_recent_orders")
def handle_view_recent_orders(call):
    telegram_id = call.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, o.PaymentMethod, o.FullyPaid,
               s.StoreName,
               (SELECT GROUP_CONCAT(p.Name || ' × ' || oi.Quantity, ', ')
                FROM OrderItems oi
                JOIN Products p ON oi.ProductID = p.ProductID
                WHERE oi.OrderID = o.OrderID) as Products
        FROM Orders o
        JOIN Sellers s ON o.SellerID = s.SellerID
        WHERE o.BuyerID = ?
        ORDER BY o.CreatedAt DESC
        LIMIT 5
    """, (telegram_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        bot.answer_callback_query(call.id, "لا توجد طلبات سابقة")
        return
    
    for order in orders:
        order_id, total, status, created_at, payment_method, fully_paid, store_name, products = order
        
        status_emoji = {
            'Pending': '⏳',
            'Confirmed': '✅',
            'Shipped': '🚚',
            'Delivered': '🎉',
            'Rejected': '❌'
        }.get(status, '📝')
        
        payment_status = "💵 مدفوع" if fully_paid == 1 else "💳 غير مدفوع"
        
        text = f"{status_emoji} **الطلب #{order_id}**\n\n"
        text += f"🏪 المتجر: {store_name}\n"
        text += f"💰 الإجمالي: {total} IQD\n"
        text += f"💳 الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'} ({payment_status})\n"
        text += f"📊 الحالة: {status}\n"
        text += f"📅 التاريخ: {created_at}\n"
        
        if products:
            text += f"\n📦 المنتجات:\n{products}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📞 اتصل بالبائع", callback_data=f"contact_seller_{order_id}"),
            types.InlineKeyboardButton("📦 طلب إرجاع", callback_data=f"request_return_order_{order_id}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("request_return_order_"))
def handle_request_return_order(call):
    order_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id] = {
        "step": "request_return_order",
        "order_id": order_id
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.ProductID, p.Name, oi.Quantity, oi.Price, oi.ReturnedQuantity
        FROM OrderItems oi
        JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = ?
    """, (order_id,))
    
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        bot.answer_callback_query(call.id, "لا توجد منتجات في هذا الطلب")
        return
    
    text = "📦 **طلب إرجاع منتج**\n\n"
    text += f"🆔 رقم الطلب: {order_id}\n\n"
    text += "📋 **المنتجات في الطلب:**\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for item in items:
        product_id, name, quantity, price, returned_qty = item
        available_qty = quantity - (returned_qty or 0)
        
        if available_qty > 0:
            text += f"🛒 {name}\n"
            text += f"   📦 الكمية: {quantity} (متاح للإرجاع: {available_qty})\n"
            text += f"   💰 السعر: {price} IQD\n"
            
            markup.add(types.InlineKeyboardButton(f"📦 إرجاع {name[:15]}", callback_data=f"select_return_product_{product_id}_{order_id}"))
            text += "────\n\n"
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_return_product_"))
def handle_select_return_product(call):
    parts = call.data.split("_")
    product_id = int(parts[3])
    order_id = int(parts[4])
    telegram_id = call.from_user.id
    
    user_states[telegram_id] = {
        "step": "return_quantity",
        "order_id": order_id,
        "product_id": product_id
    }
    
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "المنتج غير موجود")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT oi.Quantity, oi.ReturnedQuantity 
        FROM OrderItems oi 
        WHERE oi.OrderID = ? AND oi.ProductID = ?
    """, (order_id, product_id))
    
    item = cursor.fetchone()
    conn.close()
    
    if not item:
        bot.answer_callback_query(call.id, "المنتج غير موجود في الطلب")
        return
    
    quantity, returned_qty = item
    available_qty = quantity - (returned_qty or 0)
    
    bot.send_message(call.message.chat.id,
                    f"📦 **إرجاع المنتج**\n\n"
                    f"🛒 المنتج: {product[3]}\n"
                    f"📦 الكمية المتاحة للإرجاع: {available_qty}\n\n"
                    f"يرجى إدخال الكمية المراد إرجاعها:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "return_quantity")
def process_return_quantity(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    order_id = state["order_id"]
    product_id = state["product_id"]
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT oi.Quantity, oi.ReturnedQuantity 
        FROM OrderItems oi 
        WHERE oi.OrderID = ? AND oi.ProductID = ?
    """, (order_id, product_id))
    
    item = cursor.fetchone()
    conn.close()
    
    if not item:
        bot.send_message(message.chat.id, "المنتج غير موجود في الطلب")
        del user_states[telegram_id]
        return
    
    total_quantity, returned_qty = item
    available_qty = total_quantity - (returned_qty or 0)
    
    if quantity > available_qty:
        bot.send_message(message.chat.id, f"⚠️ الكمية المطلوبة للإرجاع ({quantity}) أكبر من الكمية المتاحة ({available_qty})")
        return
    
    state["return_quantity"] = quantity
    state["step"] = "return_reason"
    
    bot.send_message(message.chat.id,
                    "📝 **سبب الإرجاع**\n\n"
                    "يرجى إدخال سبب إرجاع المنتج:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "return_reason")
def process_return_reason(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    reason = message.text.strip()
    
    if not reason:
        bot.send_message(message.chat.id, "الرجاء إدخال سبب الإرجاع.")
        return
    
    order_id = state["order_id"]
    product_id = state["product_id"]
    quantity = state["return_quantity"]
    
    success, result = create_return_request(order_id, product_id, quantity, reason, telegram_id)
    
    if success:
        bot.send_message(message.chat.id,
                        f"✅ **تم تقديم طلب الإرجاع بنجاح!**\n\n"
                        f"🆔 رقم طلب الإرجاع: {result}\n"
                        f"📦 الكمية: {quantity}\n"
                        f"📝 السبب: {reason}\n\n"
                        f"سيقوم البائع بمراجعة طلبك والرد قريباً.")
    else:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {result}")
    
    del user_states[telegram_id]

# ====== الأوامر الإضافية ======
@bot.message_handler(commands=['myid'])
def get_my_id(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "لا يوجد"
    
    user_type = get_user_type(user_id)
    user_type_display = {
        'bot_admin': '👑 أدمن البوت',
        'seller': '🏪 بائع',
        'buyer': '🛍️ مشتري'
    }.get(user_type, 'مستخدم')
    
    bot.send_message(
        message.chat.id,
        f"👤 **معلومات حسابك:**\n\n"
        f"🆔 **معرفك:** `{user_id}`\n"
        f"👤 **الاسم:** {first_name}\n"
        f"🔗 **اليوزر:** @{username}\n"
        f"🎭 **النوع:** {user_type_display}\n\n"
        f"يمكنك استخدام هذا المعرف في إعدادات البوت.",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = """
🆘 **مساعدة بوت المتجر** 🆘

🔹 **الأوامر المتاحة:**
/start - بدء الاستخدام
/myid - عرض معرفك
/help - عرض هذه الرسالة

🔹 **للمشترين والزوار:**
• تصفح المتاجر المتاحة
• إضافة المنتجات للسلة
• إنهاء الطلبات
• الشراء نقداً (للجميع)
• الشراء على الحساب (للمسجلين فقط)

🔹 **للمسجلين فقط:**
• حفظ طلباتك السابقة
• كشف الحساب الآجل
• متابعة الحدود الائتمانية
• طلب إرجاع المنتجات
• تعديل بياناتك الشخصية

🔹 **للبائعين:**
• إدارة المنتجات والأقسام
• متابعة الطلبات الجديدة
• إدارة كشف حساب الزبائن الآجل
• إدارة مرتجعات العملاء
• إدارة الحدود الائتمانية للزبائن

🔹 **لأدمن البوت:**
• إدارة حسابات المتاجر
• عرض إحصائيات النظام
• إنشاء متاجر جديدة
• تعليق/تنشيط المتاجر

🔹 **نظام الدفع:**
• الدفع نقداً (للجميع)
• الشراء على الحساب (للمسجلين فقط)
• متابعة المديونيات
• نظام الحدود الائتمانية

🔹 **التسجيل:**
• التسجيل مجاني
• يوفر جميع المزايا
• يمكن التصفح بدون تسجيل
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية")
def handle_main_menu(message):
    telegram_id = message.from_user.id
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    
    if is_guest:
        browse_without_registration(message)
        return
    
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(message)
    elif is_seller(telegram_id):
        show_seller_menu(message)
    else:
        show_buyer_main_menu(message)

# ====== تشغيل البوت ======
print("🚀 بدأ تشغيل بوت متجرنا...")
print("✅ النظام الجديد شامل جميع الميزات:")
print("   👑 إدارة النظام الكاملة لأدمن البوت")
print("   🏪 إنشاء متجر خاص لأدمن البوت")
print("   🔗 نسخ رابط المتجر")
print("   📦 نظام مرتجع الشراء")
print("   📩 نظام الرسائل")
print("   💰 نظام كشف حساب الزبائن الآجل")
print("   💳 **نظام الحدود الائتمانية الجديد**")
print("   📊 إحصائيات النظام الكاملة")
print("   🛒 نظام إضافة وتعديل المنتجات والأقسام للبائعين")
print("   📸 نظام الصور المحسن مع إصلاح المشاكل")
print("   💳 نظام الدفع النقدي والآجل")
print("   👤 نظام الزبائن الآجلين")
print("   💰 سعر الجملة للزبائن الآجلين")
print("   👀 **الميزات الجديدة:**")
print("   • تصفح المتاجر بدون تسجيل")
print("   • إضافة المنتجات للسلة للزوار")
print("   • إتمام الطلبات للزوار")
print("   • تسجيل حساب جديد في أي وقت")
print("   • التفريق بين الزوار والمستخدمين المسجلين")

# ====== Debug Command ======
@bot.message_handler(commands=['debug_db'])
def debug_db_status(message):
    try:
        db_url = os.environ.get('DATABASE_URL')
        status = "✅ Using PostgreSQL" if IS_POSTGRES else "⚠️ Using SQLite (Local)"
        
        info = f"**Database Status:**\n{status}\n\n"
        if db_url:
            masked_url = db_url[:15] + "..." + db_url[-5:]
            info += f"URL Found: `{masked_url}`\n"
        else:
            info += "URL Not Found in Enviroment\n"
            
        # Try a quick count
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Products")
            count = cursor.fetchone()[0]
            conn.close()
            info += f"\nProducts Count: {count}"
        except Exception as e:
            info += f"\nDB Error: {e}"

        bot.send_message(message.chat.id, info, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "Error checking status")

# تشغيل البوت
if __name__ == "__main__":
    init_db() 
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        traceback.print_exc()