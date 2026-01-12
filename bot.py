import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

import re
import sys
from datetime import datetime
from utils.receipt_generator import generate_order_card
import base64
# Reverting to direct DB functions defined in bot.py
# from db_manager import get_seller_by_telegram, get_products, get_categories, get_product_by_id, get_category_by_id
# from integration_models import Product, Category, Seller

# ----------------- إعداد البوت وملفات -----------------
import os

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import IntegrityError
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    IntegrityError = None



TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if TOKEN:
    TOKEN = TOKEN.strip()

if not TOKEN:
    print("❌ FATAL ERROR: TELEGRAM_BOT_TOKEN environment variable is NOT set!")
    sys.exit(1) # Fail fast
else:
    print(f"[OK] DEBUG: TELEGRAM_BOT_TOKEN found. Starts with: {TOKEN[:10]}... Ends with: ...{TOKEN[-5:]}")
    print(f"[OK] DEBUG: Token Length: {len(TOKEN)}")

# --- DEBUGGING BLOCK: PRINT ALL ENV VARS ---
# print("\n🔍 DEBUGGING ENVIRONMENT VARIABLES:")
# for key, value in os.environ.items():
#    if "TOKEN" in key or "TELEGRAM" in key:
#        print(f"   🔑 Found Key: '{key}' -> Value starts with: '{value[:5]}...'")
# print("---------------------------------------\n")
bot = telebot.TeleBot(TOKEN)
IS_POSTGRES = (os.environ.get('DATABASE_URL') is not None) and (psycopg2 is not None)

# إضافة معرف صاحب البوت (أدمن) - للتحكم التقني فقط
BOT_ADMIN_ID = 1041977029  # ضع هنا معرف التليجرام الخاص بأدمن البوت

@bot.message_handler(commands=['sys_info'])
def sys_info(message):
    try:
        import sys
        info = f"🤖 **System Diagnostics**\n\n"
        info += f"🐍 Python: {sys.version.split()[0]}\n"
        info += f"📦 IS_POSTGRES: `{IS_POSTGRES}`\n"
        info += f"🔑 DATABASE_URL: {'✅ Found' if os.environ.get('DATABASE_URL') else '❌ Missing'}\n"
        info += f"🐘 psycopg2: {'✅ Imported' if psycopg2 else '❌ Missing'}\n"
        
        # Check explicit import
        try:
            import psycopg2 as pg2_test
            info += "🐘 Import Test: OK\n"
        except ImportError as e:
            info += f"🐘 Import Test: ❌ {e}\n"
            
        bot.reply_to(message, info, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['force_migration'])
def force_migration_command(message):
    """أمر لتطبيق Migration بشكل إجباري - للمشرفين فقط"""
    if not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    if not IS_POSTGRES:
        bot.reply_to(message, "⚠️ هذا الأمر يعمل فقط مع PostgreSQL (Cloud)")
        return
    
    try:
        bot.reply_to(message, "🔄 بدء تطبيق Migration...")
        
        # Use direct psycopg2 connection
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            bot.reply_to(message, "❌ DATABASE_URL not found")
            return
        
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
        cursor = conn.cursor()
        
        migrations = [
            ("Users", "TelegramID"),
            ("Sellers", "TelegramID"),
            ("CreditCustomers", "TelegramID"),
            ("Orders", "BuyerID"),
            ("Carts", "UserID"),
        ]
        
        results = []
        for table_name, column_name in migrations:
            try:
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s
                """, (table_name.lower(), column_name.lower()))
                result = cursor.fetchone()
                
                if result:
                    current_type = result[0].upper()
                    if current_type not in ('BIGINT', 'INT8'):
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                        conn.commit()
                        results.append(f"✅ {table_name}.{column_name}: {current_type} → BIGINT")
                    else:
                        results.append(f"✅ {table_name}.{column_name}: Already BIGINT")
                else:
                    results.append(f"⚠️ {table_name}.{column_name}: Column not found")
            except Exception as e:
                results.append(f"❌ {table_name}.{column_name}: {str(e)}")
                try:
                    conn.rollback()
                except:
                    pass
        
        cursor.close()
        conn.close()
        
        result_text = "🔄 **نتائج Migration:**\n\n" + "\n".join(results)
        bot.reply_to(message, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في تطبيق Migration: {str(e)}")
        import traceback
        traceback.print_exc()

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed_data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# ----------------- استعادة البيانات عند إضافة Volume جديد -----------------
import shutil
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

    @property
    def rowcount(self):
        return self.cursor.rowcount

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
            print("\n" + "="*50)
            print(f"✅ BOT CONNECTED TO POSTGRES (Cloud)")
            print(f"   Host: {hostname}")
            print("="*50 + "\n")
            return DBWrapper(conn, is_postgres=True)
        except Exception as e:
            print(f"❌ CRITICAL ERROR connecting to Postgres: {e}")
            raise e
    else:
        # Local development mode (no DATABASE_URL)
        print("\n" + "="*50)
        print(f"⚠️ BOT CONNECTED TO LOCAL SQLITE (No DATABASE_URL)")
        print(f"   File: {DB_FILE}")
        print("="*50 + "\n")
        return DBWrapper(sqlite3.connect(DB_FILE), is_postgres=False)

# Remove the restore logic entirely or guard it carefully
if not os.path.exists(DB_FILE) and os.path.exists(os.path.join(SEED_DIR, "store.db")) and not os.environ.get('DATABASE_URL'):
    print("🔄 استعادة قاعدة البيانات من النسخة الاحتياطية (Seed)...")
    shutil.copy(os.path.join(SEED_DIR, "store.db"), DB_FILE)
    if os.path.exists(os.path.join(SEED_DIR, "Images")):
         if os.path.exists(IMAGES_FOLDER):
             shutil.rmtree(IMAGES_FOLDER)
         shutil.copytree(os.path.join(SEED_DIR, "Images"), IMAGES_FOLDER)
    print("[OK] Data restored successfully!")

# ===================== قاعدة البيانات =====================
# ===================== قاعدة البيانات =====================
def init_db():
    print("=" * 60)
    print("🛠️ INITIALIZING DATABASE...")
    print("=" * 60)
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    cursor = cursor_wrapper.cursor  # Get the underlying cursor for direct access if needed

    # 1. Users (Main table, no dependencies)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Users(
                UserID SERIAL PRIMARY KEY,
                TelegramID BIGINT UNIQUE,
                UserName TEXT,
                UserType TEXT,
                PhoneNumber TEXT,
                FullName TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor_wrapper.execute("""
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
    
    # Migration: Change TelegramID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Users.TelegramID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Users.TelegramID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Users.TelegramID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Users ALTER COLUMN TelegramID TYPE BIGINT")
                    conn.commit()
                    print("✅ Users.TelegramID migrated to BIGINT successfully")
                else:
                    print(f"✅ Users.TelegramID is already BIGINT")
            else:
                print("⚠️ Users.TelegramID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Users.TelegramID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 2. Sellers (Depends on Users for SuspendedBy)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Sellers(
                SellerID SERIAL PRIMARY KEY,
                TelegramID BIGINT UNIQUE,
                UserName TEXT,
                StoreName TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                Status TEXT DEFAULT 'active',
                SuspensionReason TEXT,
                SuspendedBy BIGINT,
                SuspendedAt TIMESTAMP,
                RequireCustomerRegistration INTEGER DEFAULT 0,
                FOREIGN KEY (SuspendedBy) REFERENCES Users(TelegramID)
            )
        """)
    else:
        cursor_wrapper.execute("""
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
                RequireCustomerRegistration INTEGER DEFAULT 0,
                FOREIGN KEY (SuspendedBy) REFERENCES Users(TelegramID)
            )
        """)
    
    # Migration: Change TelegramID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Sellers.TelegramID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='sellers' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Sellers.TelegramID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Sellers.TelegramID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Sellers ALTER COLUMN TelegramID TYPE BIGINT")
                    conn.commit()
                    print("✅ Sellers.TelegramID migrated to BIGINT successfully")
                else:
                    print(f"✅ Sellers.TelegramID is already BIGINT")
            else:
                print("⚠️ Sellers.TelegramID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Sellers.TelegramID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass
    
    # Migration: Add RequireCustomerRegistration column if it doesn't exist
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sellers' AND column_name='requirecustomerregistration'
            """)
            if not cursor_wrapper.fetchone():
                print("🔄 Adding RequireCustomerRegistration column to Sellers table...")
                cursor_wrapper.execute("ALTER TABLE Sellers ADD COLUMN RequireCustomerRegistration INTEGER DEFAULT 0")
                conn.commit()
                print("✅ RequireCustomerRegistration column added successfully")
            # تأكد من أن جميع المتاجر لديها القيمة 0 (مفتوحة) افتراضياً
            cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
            conn.commit()
        else:
            try:
                cursor_wrapper.execute("SELECT RequireCustomerRegistration FROM Sellers LIMIT 1")
                # تأكد من أن جميع المتاجر لديها القيمة 0 (مفتوحة) افتراضياً
                cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
                conn.commit()
            except:
                print("🔄 Adding RequireCustomerRegistration column to Sellers table (SQLite)...")
                cursor_wrapper.execute("ALTER TABLE Sellers ADD COLUMN RequireCustomerRegistration INTEGER DEFAULT 0")
                cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
                conn.commit()
                print("✅ RequireCustomerRegistration column added successfully (SQLite)")
    except Exception as e:
        print(f"⚠️ Migration warning (non-critical): {e}")
        try:
            conn.rollback()
        except:
            pass

    # 3. CreditCustomers (Depends on Sellers)
    # Create table with nullable PhoneNumber first (for compatibility with existing data)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS CreditCustomers(
                CustomerID SERIAL PRIMARY KEY,
                SellerID INTEGER,
                FullName TEXT NOT NULL,
                PhoneNumber TEXT,
                TelegramID BIGINT,
                CustomerType TEXT DEFAULT 'CreditCustomer',
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(SellerID, PhoneNumber),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS CreditCustomers(
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                SellerID INTEGER,
                FullName TEXT NOT NULL,
                PhoneNumber TEXT,
                TelegramID INTEGER,
                CustomerType TEXT DEFAULT 'CreditCustomer',
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(SellerID, PhoneNumber),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    
    # Migration: Ensure both CustomerType and TelegramID exist and have correct types
    try:
        if IS_POSTGRES:
            # 1) Ensure CustomerType exists
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='creditcustomers' AND column_name='customertype'
            """)
            result = cursor_wrapper.fetchone()
            if not result:
                print("🔄 Adding CustomerType column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN CustomerType TEXT DEFAULT 'CreditCustomer'")
                cursor_wrapper.execute("UPDATE CreditCustomers SET CustomerType = 'CreditCustomer' WHERE CustomerType IS NULL")
                conn.commit()
                print("✅ CustomerType column added successfully")

            # 2) Ensure TelegramID exists and is BIGINT
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='creditcustomers' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if not result:
                print("🔄 Adding TelegramID column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN TelegramID BIGINT")
                conn.commit()
                print("✅ TelegramID column added successfully")
            else:
                cursor_wrapper.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name='creditcustomers' AND column_name='telegramid'
                """)
                type_result = cursor_wrapper.fetchone()
                if type_result:
                    current_type = type_result[0].upper()
                    print(f"📊 CreditCustomers.TelegramID current type: {current_type}")
                    if current_type not in ('BIGINT', 'INT8'):
                        print(f"🔄 FORCE Migrating CreditCustomers.TelegramID from {current_type} to BIGINT...")
                        cursor_wrapper.execute("ALTER TABLE CreditCustomers ALTER COLUMN TelegramID TYPE BIGINT")
                        conn.commit()
                        print("✅ CreditCustomers.TelegramID migrated to BIGINT successfully")
                    else:
                        print("✅ CreditCustomers.TelegramID is already BIGINT")
        else:
            # SQLite: check table columns and add missing ones
            cursor_wrapper.execute("PRAGMA table_info(CreditCustomers)")
            columns = [row[1] for row in cursor_wrapper.fetchall()]

            if 'TelegramID' not in columns:
                print("🔄 Adding TelegramID column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN TelegramID INTEGER")
                conn.commit()
                print("✅ TelegramID column added successfully")

            if 'CustomerType' not in columns:
                print("🔄 Adding CustomerType column to CreditCustomers table (SQLite)...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN CustomerType TEXT DEFAULT 'CreditCustomer'")
                cursor_wrapper.execute("UPDATE CreditCustomers SET CustomerType = 'CreditCustomer' WHERE CustomerType IS NULL")
                conn.commit()
                print("✅ CustomerType column added successfully (SQLite)")
    except Exception as e:
        print(f"⚠️ Migration warning (non-critical): {e}")
        try:
            conn.rollback()
        except:
            pass
        # Don't fail the entire init if migration fails

    # 4. CreditLimits (Depends on CreditCustomers, Sellers)
    # Using DEFAULT TRUE for Postgres compatibility
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS CreditLimits (
            LimitID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            MaxCreditAmount REAL DEFAULT 1000000,
            WarningThreshold REAL DEFAULT 0.8,
            CurrentUsedAmount REAL DEFAULT 0,
            IsActive BOOLEAN DEFAULT TRUE,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID),
            UNIQUE(CustomerID, SellerID)
        )
    """)

    # 5. Categories (Depends on Sellers)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Categories(
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            Name TEXT,
            OrderIndex INTEGER DEFAULT 0,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 6. Products (Depends on Sellers, Categories)
    cursor_wrapper.execute("""
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
    
    # 6.1. ProductImages (Depends on Products) - صور متعددة لكل منتج
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS ProductImages(
            ImageID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductID INTEGER,
            ImagePath TEXT NOT NULL,
            ImageOrder INTEGER DEFAULT 0,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE CASCADE
        )
    """)

    # 7. Carts (Depends on Users, Products)
    if IS_POSTGRES:
        # PostgreSQL: Use BIGINT for UserID to support large Telegram IDs
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Carts(
                CartID SERIAL PRIMARY KEY,
                UserID BIGINT,
                ProductID INTEGER,
                Quantity INTEGER,
                Price REAL,
                AddedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(UserID, ProductID),
                FOREIGN KEY (UserID) REFERENCES Users(TelegramID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
        """)
    else:
        # SQLite: INTEGER supports 64-bit values
        cursor_wrapper.execute("""
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
    
    # Migration: Change UserID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Carts.UserID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='carts' AND column_name='userid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Carts.UserID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Carts.UserID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Carts ALTER COLUMN UserID TYPE BIGINT")
                    conn.commit()
                    print("✅ Carts.UserID migrated to BIGINT successfully")
                else:
                    print(f"✅ Carts.UserID is already BIGINT")
            else:
                print("⚠️ Carts.UserID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Carts.UserID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 8. Orders (Depends on Users, Sellers)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Orders(
                OrderID SERIAL PRIMARY KEY,
                BuyerID BIGINT,
                SellerID INTEGER,
                Total REAL,
                Status TEXT DEFAULT 'Pending',
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                DeliveryAddress TEXT,
                Notes TEXT,
                PaymentMethod TEXT DEFAULT 'cash',
                FullyPaid BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    else:
        cursor_wrapper.execute("""
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
                FullyPaid BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    
    # Migration: Change BuyerID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Orders.BuyerID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='orders' AND column_name='buyerid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Orders.BuyerID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Orders.BuyerID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Orders ALTER COLUMN BuyerID TYPE BIGINT")
                    conn.commit()
                    print("✅ Orders.BuyerID migrated to BIGINT successfully")
                else:
                    print(f"✅ Orders.BuyerID is already BIGINT")
            else:
                print("⚠️ Orders.BuyerID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Orders.BuyerID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 9. OrderItems (Depends on Orders, Products)
    cursor_wrapper.execute("""
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

    # 10. Returns (Depends on Orders, Products, Users)
    cursor_wrapper.execute("""
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

    # 11. Messages (Depends on Orders, Sellers)
    # Using DEFAULT FALSE for Postgres compatibility
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Messages(
            MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            SellerID INTEGER,
            MessageType TEXT,
            MessageText TEXT,
            IsRead BOOLEAN DEFAULT FALSE,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 12. CustomerCredit (Transaction History) - Depends on CreditCustomers, Sellers
    cursor_wrapper.execute("""
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

    # 13. CustomerCredit (Depends on CreditCustomers, Sellers)
    # Using DEFAULT FALSE for Postgres compatibility (though boolean not used here heavily)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS CustomerCredit (
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

    # 14. Image Storage (For Syncing Images from Desktop App)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BYTEA,
                UploadedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BLOB,
                UploadedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    # ----------------- MIGRATIONS -----------------
    def ensure_column(table, column, definition):
        try:
            cursor_wrapper.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
            print(f"[OK] Migrated: Added {column} to {table}")
        except Exception as e:
            # Most likely column already exists
            pass
            
    # Explicitly ensure ImagePath exists for Sync
    ensure_column('Sellers', 'ImagePath', 'TEXT')
    ensure_column('Categories', 'ImagePath', 'TEXT')
    ensure_column('Products', 'ImagePath', 'TEXT')
    
    # Ensure Suspension columns exist
    ensure_column('Sellers', 'SuspensionReason', 'TEXT')
    ensure_column('Sellers', 'SuspendedBy', 'INTEGER')
    ensure_column('Sellers', 'SuspendedAt', 'DATETIME')
    
    conn.commit()
    cursor_wrapper.close()
    conn.close()
    
    # Force apply BIGINT migrations after all tables are created
    if IS_POSTGRES:
        print("\n" + "=" * 60)
        print("🔄 APPLYING BIGINT MIGRATIONS (FORCE)...")
        print("=" * 60)
        try:
            force_apply_bigint_migrations()
        except Exception as e:
            print(f"❌ Error in force_apply_bigint_migrations: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("=" * 60)

# Note: init_db() is called in if __name__ == "__main__" block, not here

def force_apply_bigint_migrations():
    """تطبيق Migration بشكل إجباري لجميع الأعمدة"""
    if not IS_POSTGRES:
        print("⚠️ Not PostgreSQL, skipping BIGINT migration")
        return
    
    # Get the actual connection (not DBWrapper) for direct SQL execution
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        result = urllib.parse.urlparse(database_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        # Connect directly using psycopg2
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = conn.cursor()
        
        migrations = [
            ("Users", "TelegramID"),
            ("Sellers", "TelegramID"),
            ("CreditCustomers", "TelegramID"),
            ("Orders", "BuyerID"),
            ("Carts", "UserID"),
        ]
        
        for table_name, column_name in migrations:
            try:
                # Check current type
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s
                """, (table_name.lower(), column_name.lower()))
                result = cursor.fetchone()
                
                if result:
                    current_type = result[0].upper()
                    print(f"📊 {table_name}.{column_name}: {current_type}")
                    
                    if current_type not in ('BIGINT', 'INT8'):
                        print(f"   🔄 FORCE Migrating {table_name}.{column_name} from {current_type} to BIGINT...")
                        # Use direct SQL execution for ALTER TABLE
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                        conn.commit()
                        print(f"   ✅ Successfully migrated to BIGINT")
                    else:
                        print(f"   ✅ Already BIGINT")
                else:
                    print(f"⚠️ {table_name}.{column_name}: Column not found!")
            except Exception as e:
                print(f"❌ Error migrating {table_name}.{column_name}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    conn.rollback()
                except:
                    pass
        
        cursor.close()
        conn.close()
        print("✅ Migration completed successfully")
    except Exception as e:
        print(f"❌ Error connecting to database for migration: {e}")
        import traceback
        traceback.print_exc()

def check_and_fix_db():
    # ... logic skipped ...
    pass

# check_and_fix_db()

def download_image_from_cloud(filename):
    """
    Attempts to download an image from the Postgres ImageStorage table
    if it exists there. Returns True if successful, False otherwise.
    """
    if not IS_POSTGRES:
        return False
        
    try:
        # Prevent SQL injection or path traversal (basic check)
        filename = os.path.basename(filename)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT FileData FROM ImageStorage WHERE FileName = %s", (filename,))
        result = cursor.fetchone()
        
        if result and result[0]:
            file_data = result[0]
            # Ensure Images folder exists
            if not os.path.exists(IMAGES_FOLDER):
                os.makedirs(IMAGES_FOLDER)
                
            file_path = os.path.join(IMAGES_FOLDER, filename)
            
            # Write bytes
            with open(file_path, 'wb') as f:
                f.write(file_data)
                
            conn.close()
            return True
            
        conn.close()
        return False
        
    except Exception as e:
        print(f"Error downloading image {filename}: {e}")
        return False

# ===================== نظام حدود الائتمان =====================

def check_credit_limit(customer_id, seller_id, new_amount):
    """التحقق إذا كان يمكن للزبون تحمل مبلغ جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الحد الحالي
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount 
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
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
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
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
            WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
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
            VALUES (?, ?, 1000000, ?, TRUE)
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
    
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO CreditLimits (CustomerID, SellerID, MaxCreditAmount, WarningThreshold, CurrentUsedAmount, IsActive)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (CustomerID, SellerID) DO UPDATE SET
                MaxCreditAmount = EXCLUDED.MaxCreditAmount,
                WarningThreshold = EXCLUDED.WarningThreshold,
                IsActive = TRUE
        """, (customer_id, seller_id, max_amount, warning_percentage, current_used))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO CreditLimits 
            (CustomerID, SellerID, MaxCreditAmount, WarningThreshold, CurrentUsedAmount, IsActive)
            VALUES (?, ?, ?, ?, ?, TRUE)
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
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
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

def download_image_from_cloud(filename):
    """
    Downloads an image from the Cloud 'ImageStorage' table if it exists
    and saves it to the local IMAGES_FOLDER.
    Returns True if successful, False otherwise.
    """
    if not IS_POSTGRES:
        return False
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if file exists in ImageStorage
        # Note: cursor wrapper executes standard SQL. 
        # We need raw fetch for BYTEA data.
        
        # We need to access the underlying cursor for raw byte handling if Wrapper acts up, 
        # but let's try standard fetchone first.
        cursor.execute("SELECT FileData FROM ImageStorage WHERE FileName = %s", (filename,))
        result = cursor.fetchone()
        
        if result and result[0]:
            file_data = result[0]
            # If it's memoryview (psycopg2 binary), convert to bytes
            if isinstance(file_data, memoryview):
                file_data = file_data.tobytes()
                
            local_path = os.path.join(IMAGES_FOLDER, filename)
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            conn.close()
            return True
            
        conn.close()
        return False
        
    except Exception as e:
        print(f"❌ Error downloading image {filename}: {e}")
        traceback.print_exc()
        return False

def add_credit_customer(seller_id, full_name, phone_number, customer_type='CreditCustomer', telegram_id=None):
    """إضافة زبون آجل أو نقطة بيع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        if not phone_number or phone_number.strip() == '':
            conn.close()
            return None
        
        if IS_POSTGRES:
            cursor_wrapper.execute("""
                INSERT INTO CreditCustomers (SellerID, FullName, PhoneNumber, CustomerType, TelegramID)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                RETURNING CustomerID
            """, (seller_id, full_name, phone_number, customer_type, telegram_id))
            result = cursor_wrapper.fetchone()
            customer_id = result[0] if result else None
        else:
            cursor_wrapper.execute("""
                INSERT OR IGNORE INTO CreditCustomers (SellerID, FullName, PhoneNumber, CustomerType, TelegramID)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, full_name, phone_number, customer_type, telegram_id))
            customer_id = cursor_wrapper.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        return customer_id
    except Exception as e:
        print(f"Error adding credit customer: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        cursor.close()
        conn.close()
        return None

def update_credit_customer(customer_id, seller_id, full_name=None, phone_number=None):
    """تحديث بيانات زبون آجل"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if full_name:
            updates.append("FullName = ?" if not IS_POSTGRES else "FullName = %s")
            params.append(full_name)
        
        if phone_number is not None:
            updates.append("PhoneNumber = ?" if not IS_POSTGRES else "PhoneNumber = %s")
            params.append(phone_number)
        
        if not updates:
            conn.close()
            return False
        
        params.append(customer_id)
        params.append(seller_id)
        
        if IS_POSTGRES:
            query = f"UPDATE CreditCustomers SET {', '.join(updates)} WHERE CustomerID = %s AND SellerID = %s"
        else:
            query = f"UPDATE CreditCustomers SET {', '.join(updates)} WHERE CustomerID = ? AND SellerID = ?"
        
        cursor.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        print(f"Error updating credit customer: {e}")
        conn.close()
        return False

def get_credit_customer(seller_id, phone_number=None, full_name=None):
    """الحصول على زبون آجل بالهاتف أو الاسم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if phone_number:
        if IS_POSTGRES:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=%s AND PhoneNumber=%s
            """, (seller_id, phone_number))
        else:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=? AND PhoneNumber=?
            """, (seller_id, phone_number))
    elif full_name:
        if IS_POSTGRES:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=%s AND FullName LIKE %s
            """, (seller_id, f"%{full_name}%"))
        else:
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

def is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id):
    """التحقق من أن Telegram ID مسجل في CreditCustomers لهذا المتجر"""
    try:
        if not telegram_id:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
        
        cursor_wrapper.execute("""
            SELECT CustomerID FROM CreditCustomers 
            WHERE SellerID=? AND TelegramID=?
        """, (seller_id, telegram_id))
        
        result = cursor_wrapper.fetchone()
        cursor.close()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من تسجيل الزبون بـ Telegram ID: {e}")
        import traceback
        traceback.print_exc()
        return False

def is_customer_registered_for_store_by_phone(phone_number, seller_id):
    """التحقق من أن رقم الهاتف مسجل في CreditCustomers لهذا المتجر (deprecated - use Telegram ID)"""
    try:
        if not phone_number or not phone_number.strip():
            return False
        
        # تنظيف رقم الهاتف (إزالة المسافات والرموز)
        phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("+", "")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT CustomerID FROM CreditCustomers 
                WHERE SellerID=%s AND PhoneNumber=%s
            """, (seller_id, phone_number))
        else:
            cursor.execute("""
                SELECT CustomerID FROM CreditCustomers 
                WHERE SellerID=? AND PhoneNumber=?
            """, (seller_id, phone_number))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من تسجيل الزبون بالهاتف: {e}")
        return False

def get_all_credit_customers(seller_id):
    """الحصول على جميع الزبائن الآجلين ونقاط البيع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT cc.CustomerID, cc.SellerID, cc.FullName, cc.PhoneNumber, cc.TelegramID,
                   COALESCE(cc.CustomerType, 'CreditCustomer') as CustomerType, cc.CreatedAt,
                   COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
                   COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
                   COALESCE(cl.IsActive, TRUE) as LimitActive
            FROM CreditCustomers cc
            LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
            WHERE cc.SellerID=%s 
            ORDER BY cc.FullName
        """, (seller_id,))
    else:
        cursor.execute("""
            SELECT cc.CustomerID, cc.SellerID, cc.FullName, cc.PhoneNumber, cc.TelegramID,
                   COALESCE(cc.CustomerType, 'CreditCustomer') as CustomerType, cc.CreatedAt,
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
            COALESCE(cl.IsActive, TRUE) as LimitActive
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
    """إضافة مستخدم جديد أو تحديث المستخدم الموجود"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        if IS_POSTGRES:
            # PostgreSQL syntax
            cursor_wrapper.execute("""
                INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (TelegramID) 
                DO UPDATE SET 
                    UserName = EXCLUDED.UserName, 
                    UserType = EXCLUDED.UserType, 
                    PhoneNumber = COALESCE(EXCLUDED.PhoneNumber, Users.PhoneNumber), 
                    FullName = COALESCE(EXCLUDED.FullName, Users.FullName)
            """, (telegram_id, username, usertype, phone_number, full_name))
        else:
            # SQLite syntax
            cursor_wrapper.execute("""
                INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, username, usertype, phone_number, full_name))
        conn.commit()
        print(f"[SUCCESS] User {telegram_id} added/updated successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error in add_user for {telegram_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def get_user(telegram_id):
    """الحصول على معلومات المستخدم من TelegramID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("SELECT * FROM Users WHERE TelegramID=?", (telegram_id,))
        user = cursor_wrapper.fetchone()
        return user
    except Exception as e:
        print(f"[ERROR] Error in get_user for {telegram_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor.close()
        conn.close()

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
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute("""
                INSERT INTO Sellers (TelegramID, UserName, StoreName)
                VALUES (?, ?, ?)
                ON CONFLICT (TelegramID) DO NOTHING
            """, (telegram_id, username, store_name))
        else:
            cursor_wrapper.execute("""
                INSERT OR IGNORE INTO Sellers (TelegramID, UserName, StoreName)
                VALUES (?, ?, ?)
            """, (telegram_id, username, store_name))
        
        cursor_wrapper.execute("""
            UPDATE Sellers SET StoreName=?, UserName=?
            WHERE TelegramID=?
        """, (store_name, username, telegram_id))
        conn.commit()
    except Exception as e:
        print(f"Error in add_seller: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
    finally:
        cursor.close()
        conn.close()

def get_seller_by_telegram(telegram_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
        seller = cursor_wrapper.fetchone()
        
        # إذا لم يتم العثور على البائع، حاول البحث في جدول Users
        if not seller:
            user = get_user(telegram_id)
            if user and user[3] == 'seller':
                # إذا كان المستخدم مسجلاً كبائع ولكن ليس في جدول البائعين
                # أضفه إلى جدول البائعين باسم افتراضي
                username = user[2] or user[5] or "بائع"
                store_name = f"متجر {username}"
                add_seller(telegram_id, username, store_name)
                conn2 = get_db_connection()
                cursor_wrapper2 = conn2.cursor()  # This returns CursorWrapper
                cursor_wrapper2.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
                seller = cursor_wrapper2.fetchone()
                cursor_wrapper2.close()
                conn2.close()
        
        return seller
    except Exception as e:
        print(f"Error in get_seller_by_telegram: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

def get_seller_by_id(seller_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("SELECT * FROM Sellers WHERE SellerID=?", (seller_id,))
        seller = cursor_wrapper.fetchone()
        return seller
    except Exception as e:
        print(f"Error in get_seller_by_id: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

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
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("SELECT CategoryID, Name FROM Categories WHERE SellerID=? ORDER BY OrderIndex", (seller_id,))
        categories = cursor_wrapper.fetchall()
        return categories
    except Exception as e:
        print(f"Error in get_categories: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

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
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        # Debug: Check database type
        is_postgres = conn.is_postgres if hasattr(conn, 'is_postgres') else IS_POSTGRES
        print(f"🔍 get_products: IS_POSTGRES={is_postgres}, seller_id={seller_id}, category_id={category_id}")
        
        if seller_id and category_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND CategoryID=? AND Status='active'", 
                          (seller_id, category_id))
        elif seller_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND Status='active'", (seller_id,))
        elif category_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND CategoryID=? AND Status='active'", (category_id,))
        else:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND Status='active'")
        products = cursor_wrapper.fetchall()
        
        print(f"📊 get_products: Found {len(products)} products")
        if len(products) == 0:
            # Debug: Check if there are any products at all (even with Quantity = 0)
            cursor_wrapper.execute("SELECT COUNT(*) FROM Products WHERE Status='active'")
            count_result = cursor_wrapper.fetchone()
            total_count = count_result[0] if count_result else 0
            print(f"⚠️ No products found with Quantity > 0. Total active products: {total_count}")
        
        return products
    except Exception as e:
        print(f"Error in get_products: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

def get_product_images(product_id):
    """الحصول على جميع صور المنتج"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            SELECT ImageID, ImagePath, ImageOrder 
            FROM ProductImages 
            WHERE ProductID=%s 
            ORDER BY ImageOrder, ImageID
        """, (product_id,))
    else:
        cursor.execute("""
            SELECT ImageID, ImagePath, ImageOrder 
            FROM ProductImages 
            WHERE ProductID=? 
            ORDER BY ImageOrder, ImageID
        """, (product_id,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_customer_by_phone_for_seller(phone_number, seller_id):
    """الحصول على معلومات الزبون من رقم الهاتف والبائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تنظيف رقم الهاتف
    phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, PhoneNumber 
            FROM CreditCustomers 
            WHERE SellerID=%s AND PhoneNumber=%s
        """, (seller_id, phone_number))
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, PhoneNumber 
            FROM CreditCustomers 
            WHERE SellerID=? AND PhoneNumber=?
        """, (seller_id, phone_number))
    
    customer = cursor.fetchone()
    conn.close()
    return customer

def add_credit_transaction(customer_id, seller_id, amount, description):
    """إضافة معاملة ائتمانية للزبون"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على الرصيد الحالي
        current_balance = get_customer_balance(customer_id, seller_id)
        new_balance = current_balance + amount
        
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO CustomerCredit (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, seller_id, 'Purchase', amount, description, current_balance, new_balance))
        else:
            cursor.execute("""
                INSERT INTO CustomerCredit (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, seller_id, 'Purchase', amount, description, current_balance, new_balance))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding credit transaction: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def get_product_by_id(pid):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("SELECT ProductID, SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE ProductID=?", (pid,))
        product = cursor_wrapper.fetchone()
        return product
    except Exception as e:
        print(f"Error in get_product_by_id: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

def get_product_price_for_customer(product_id, seller_id, phone_number=None, full_name=None):
    """الحصول على سعر المنتج للزبون
    - زبون آجل (CreditCustomer): سعر المفرد
    - نقطة بيع (PointOfSale): سعر الجملة
    """
    product = get_product_by_id(product_id)
    if not product:
        return None
    
    # التحقق إذا كان الزبون مسجلاً
    if phone_number or full_name:
        customer = get_credit_customer(seller_id, phone_number, full_name)
        if customer:
            customer_type = customer[4] if len(customer) > 4 else 'CreditCustomer'
            # نقطة بيع: سعر الجملة
            if customer_type == 'PointOfSale':
                return product[6] if product[6] is not None and product[6] > 0 else product[5]
            # زبون آجل: سعر المفرد
            else:
                return product[5]
    
    # إرجاع سعر البيع العادي
    return product[5]

def get_customer_type(seller_id, phone_number=None, full_name=None):
    """الحصول على نوع الزبون"""
    customer = get_credit_customer(seller_id, phone_number, full_name)
    if customer:
        return customer[4] if len(customer) > 4 else 'CreditCustomer'
    return None

def add_to_cart_db(user_id, product_id, quantity=1, price=None):
    """إضافة منتج إلى السلة مع التحقق من وجود المستخدم والمنتج"""
    print(f"[DEBUG] add_to_cart_db called: user_id={user_id}, product_id={product_id}, quantity={quantity}, price={price}")
    
    # Validate inputs
    if not user_id or user_id == 0:
        print(f"[ERROR] Invalid user_id: {user_id}")
        return False
    
    if not product_id or product_id == 0:
        print(f"[ERROR] Invalid product_id: {product_id}")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        # Ensure user exists in Users table before adding to cart (Foreign Key constraint)
        print(f"[DEBUG] Checking if user {user_id} exists...")
        user = get_user(user_id)
        if not user:
            # User doesn't exist, create a basic user entry
            print(f"[INFO] User {user_id} not found in Users table. Creating user entry...")
            user_created = add_user(user_id, None, 'buyer', None, None)
            if not user_created:
                print(f"[ERROR] Failed to create user {user_id}. Cannot add to cart.")
                cursor.close()
                conn.close()
                return False
            
            # Close current connection and reopen to ensure fresh state
            cursor.close()
            conn.close()
            
            # Small delay to ensure database commit is complete
            import time
            time.sleep(0.2)  # Increased delay
            
            # Reopen connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
            
            # Verify user was created
            user = get_user(user_id)
            if not user:
                print(f"[ERROR] User {user_id} still not found after creation attempt.")
                cursor.close()
                conn.close()
                return False
            print(f"[SUCCESS] User {user_id} created and verified")
        else:
            print(f"[OK] User {user_id} exists: TelegramID={user[1]}, UserType={user[3]}")
        
        # Verify product exists
        print(f"[DEBUG] Checking if product {product_id} exists...")
        if price is None:
            product = get_product_by_id(product_id)
            if not product:
                print(f"[ERROR] Product {product_id} not found")
                cursor.close()
                conn.close()
                return False
            price = product[5]
            print(f"[OK] Product {product_id} exists: Name={product[3]}, Price={price}")
        else:
            # Still verify product exists even if price is provided
            product = get_product_by_id(product_id)
            if not product:
                print(f"[ERROR] Product {product_id} not found")
                cursor.close()
                conn.close()
                return False
            print(f"[OK] Product {product_id} exists: Name={product[3]}")
        
        # Ensure referenced user exists (upsert) — prevents FK violations
        print(f"[DEBUG] Ensuring user row exists for TelegramID={user_id}...")
        try:
            if IS_POSTGRES:
                cursor_wrapper.execute(
                    """
                    INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (TelegramID) DO NOTHING
                    """,
                    (user_id, None, 'buyer', None, None)
                )
            else:
                cursor_wrapper.execute(
                    "INSERT OR IGNORE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) VALUES (?, ?, ?, ?, ?)",
                    (user_id, None, 'buyer', None, None)
                )
        except Exception as e:
            print(f"[WARN] Failed to ensure user existence before cart insert: {e}")

        # Use CursorWrapper to handle PostgreSQL parameter conversion
        print(f"[DEBUG] Checking existing cart entry...")
        cursor_wrapper.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
        existing = cursor_wrapper.fetchone()
        
        if existing:
            new_quantity = existing[0] + quantity
            print(f"[DEBUG] Updating cart: UserID={user_id}, ProductID={product_id}, OldQuantity={existing[0]}, NewQuantity={new_quantity}")
            cursor_wrapper.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", 
                          (new_quantity, price, user_id, product_id))
            print(f"[SUCCESS] Updated cart: UserID={user_id}, ProductID={product_id}, Quantity={new_quantity}")
        else:
            print(f"[DEBUG] Inserting new cart entry: UserID={user_id}, ProductID={product_id}, Quantity={quantity}, Price={price}")
            cursor_wrapper.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                          (user_id, product_id, quantity, price))
            print(f"[SUCCESS] Added to cart: UserID={user_id}, ProductID={product_id}, Quantity={quantity}")
        
        conn.commit()
        print(f"[SUCCESS] Cart operation completed successfully for UserID={user_id}, ProductID={product_id}")
        return True
    except Exception as e:
        # Check if it's an IntegrityError (Foreign Key constraint violation)
        error_str = str(e).lower()
        if 'foreign key' in error_str or 'violates' in error_str or (psycopg2 and isinstance(e, psycopg2.IntegrityError)):
            print(f"[ERROR] Foreign Key Constraint Violation in add_to_cart_db:")
            print(f"  UserID: {user_id}")
            print(f"  ProductID: {product_id}")
            print(f"  Error: {e}")
            # Additional debugging
            try:
                # Check if user exists
                user_check = get_user(user_id)
                print(f"  User exists: {user_check is not None}")
                if user_check:
                    print(f"  User TelegramID: {user_check[1]}")
                # Check if product exists
                product_check = get_product_by_id(product_id)
                print(f"  Product exists: {product_check is not None}")
                if product_check:
                    print(f"  Product ProductID: {product_check[0]}")
            except Exception as debug_error:
                print(f"  Debug error: {debug_error}")
                import traceback
                traceback.print_exc()
            # Try to collect more DB state and attempt a safe repair: ensure Users row exists and retry once
            try:
                repair_conn = get_db_connection()
                repair_cur = repair_conn.cursor()
                repair_w = CursorWrapper(repair_cur, is_postgres=IS_POSTGRES)

                try:
                    # Show matching Users row(s)
                    repair_w.execute("SELECT UserID, TelegramID, UserName, UserType, CreatedAt FROM Users WHERE TelegramID=?", (user_id,))
                    rows = repair_w.fetchall()
                    print(f"  Users rows for TelegramID={user_id}: {rows}")

                    # If no user row, create one
                    if not rows:
                        print(f"  Attempting to insert missing Users row for TelegramID={user_id}")
                        if IS_POSTGRES:
                            repair_w.execute(
                                """
                                INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT (TelegramID) DO NOTHING
                                """,
                                (user_id, None, 'buyer', None, None)
                            )
                        else:
                            repair_w.execute(
                                "INSERT OR IGNORE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) VALUES (?, ?, ?, ?, ?)",
                                (user_id, None, 'buyer', None, None)
                            )
                        try:
                            repair_conn.commit()
                        except:
                            pass

                    # Show recent Carts rows for visibility
                    repair_w.execute("SELECT CartID, UserID, ProductID, Quantity, AddedAt FROM Carts ORDER BY CartID DESC LIMIT 10")
                    carts = repair_w.fetchall()
                    print(f"  Recent Carts: {carts}")

                    # For SQLite, show PRAGMA foreign_keys state
                    if not IS_POSTGRES:
                        try:
                            repair_w.execute("PRAGMA foreign_keys")
                            fk_state = repair_w.fetchall()
                            print(f"  PRAGMA foreign_keys: {fk_state}")
                        except Exception:
                            pass

                    # Attempt one safe retry of the insert into Carts
                    try:
                        print(f"  Retrying cart insert once for UserID={user_id}, ProductID={product_id}")
                        # Use a fresh cursor wrapper for the insert
                        repair_w.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
                        ex = repair_w.fetchone()
                        if ex:
                            new_q = ex[0] + quantity
                            repair_w.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", (new_q, price, user_id, product_id))
                        else:
                            repair_w.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)", (user_id, product_id, quantity, price))
                        repair_conn.commit()
                        print("  Retry succeeded: cart insert/update completed")
                        try:
                            repair_cur.close()
                        except:
                            pass
                        try:
                            repair_conn.close()
                        except:
                            pass
                        return True
                    except Exception as retry_e:
                        print(f"  Retry failed: {retry_e}")

                except Exception as rr:
                    print(f"  Repair debug failed: {rr}")
                finally:
                    try:
                        repair_cur.close()
                    except:
                        pass
                    try:
                        repair_conn.close()
                    except:
                        pass
            except Exception as outer_repair_err:
                print(f"  Outer repair error: {outer_repair_err}")

            try:
                conn.rollback()
            except:
                pass
            return False

        # Other exceptions
        print(f"[ERROR] Error in add_to_cart_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def update_cart_quantity_db(user_id, product_id, new_quantity):
    """Update the quantity of a product in the cart (Set, not Add)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("UPDATE Carts SET Quantity=? WHERE UserID=? AND ProductID=?", 
                      (new_quantity, user_id, product_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_cart_quantity_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def get_cart_items_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("""
            SELECT C.ProductID, C.Quantity, C.Price, P.Name, P.Description, P.ImagePath, 
                   P.Quantity as AvailableQty, P.SellerID, S.StoreName
            FROM Carts C
            JOIN Products P ON C.ProductID = P.ProductID
            JOIN Sellers S ON P.SellerID = S.SellerID
            WHERE C.UserID = ?
            ORDER BY C.AddedAt DESC
        """, (user_id,))
        
        items = cursor_wrapper.fetchall()
        return items
    except Exception as e:
        print(f"Error in get_cart_items_db: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor.close()
        conn.close()

def create_order(buyer_id, seller_id, cart_items, delivery_address=None, notes=None, payment_method='cash', fully_paid=False):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    total = 0
    
    try:
        for pid, qty, price in cart_items:
            total += price * qty

        query = """
            INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        if IS_POSTGRES:
            query += " RETURNING OrderID"
        
        cursor_wrapper.execute(query, (buyer_id, seller_id, total, delivery_address, notes, payment_method, fully_paid))
        order_id = cursor_wrapper.lastrowid
        
        # 🛡️ Safe Fallback for Postgres: If CursorWrapper didn't capture ID, try manually
        if IS_POSTGRES and not order_id:
            try:
                res = cursor_wrapper.fetchone()
                if res:
                    order_id = res[0]
                    print(f"DEBUG: Retrieved OrderID via fallback fetchone for User {buyer_id}")
            except Exception as e:
                print(f"DEBUG: Error in fallback fetchone: {e}")

        # Optimize: Fetch product data using valid transaction cursor to avoid locking/visibility issues
        # Pre-fetch check or inline check
        for pid, qty, price in cart_items:
            # Inline lookup using SAME cursor_wrapper
            cursor_wrapper.execute("SELECT Quantity FROM Products WHERE ProductID = ?", (pid,))
            res = cursor_wrapper.fetchone()
            
            if not res:
                print(f"⚠️ Warning: Product {pid} not found during Order {order_id} creation. Skipping Item.")
                continue
                
            current_qty_in_db = res[0]
            
            cursor_wrapper.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                           (order_id, pid, qty, price))
                           
            new_qty = current_qty_in_db - qty
            if new_qty < 0:
                new_qty = 0
            cursor_wrapper.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
    
        # تسجيل المعاملة في كشف الحساب حسب نوع الزبون وطريقة الدفع
        buyer_info = get_user(buyer_id)
        if buyer_info:
            phone = buyer_info[4]
            full_name = buyer_info[5]
            customer = get_credit_customer(seller_id, phone, full_name)
            if customer:
                customer_type = customer[4] if len(customer) > 4 else 'CreditCustomer'
                
                # تحديد متى نسجل المعاملة:
                # - زبون آجل: دائماً نسجل إذا كان الدفع آجل
                # - نقطة بيع: نسجل فقط إذا كان الدفع آجل (لا نسجل إذا كان نقدي)
                should_record = False
                if customer_type == 'CreditCustomer':
                    # زبون آجل: نسجل إذا كان الدفع آجل
                    should_record = (payment_method == 'credit' and not fully_paid)
                elif customer_type == 'PointOfSale':
                    # نقطة بيع: نسجل فقط إذا كان الدفع آجل
                    should_record = (payment_method == 'credit' and not fully_paid)
                
                if should_record:
                    # التحقق من الحد الائتماني قبل إتمام الشراء
                    can_purchase, message, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, total)
                    if not can_purchase:
                        # إرجاع الطلب
                        conn.rollback()
                        cursor_wrapper.close()
                        conn.close()
                        return None, message
                    
                    add_credit_transaction(customer[0], seller_id, 'purchase', total, f"شراء طلب #{order_id}")

        conn.commit()
        notify_seller_of_order(order_id, buyer_id, seller_id)
        return order_id, total
    except Exception as e:
        print(f"Error in create_order: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return None, f"حدث خطأ أثناء إنشاء الطلب: {str(e)}"
    finally:
        cursor_wrapper.close()
        conn.close()

# This function is a duplicate - removed, using the one above

def get_orders_by_seller(seller_id, status=None):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
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
        
        cursor_wrapper.execute(query, params)
        orders = cursor_wrapper.fetchall()
        return orders
    except Exception as e:
        print(f"Error in get_orders_by_seller: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

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
        LEFT JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = ?
    """, (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    return order, items

def clear_cart_db(user_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("DELETE FROM Carts WHERE UserID=?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in clear_cart_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor_wrapper.close()
        conn.close()

def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Products WHERE ProductID = ?", (product_id,))
    conn.commit()
    conn.close()
    return True

def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Categories WHERE CategoryID = ?", (category_id,))
    conn.commit()
    conn.close()
    return True

def get_product_count_in_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Products WHERE CategoryID = ?", (category_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

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
        WHERE m.SellerID = ? AND m.IsRead IS FALSE
        ORDER BY m.CreatedAt DESC
    """, (seller_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def mark_message_as_read(message_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    conn.commit()
    conn.close()

def mark_messages_read_by_order(order_id):
    """Marks all messages related to a specific order as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET IsRead = TRUE WHERE OrderID = ?", (order_id,))
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
    # بناء النص التفصيلي (للرسايل الداخلية والاحتياط)
    full_notification = f"🛎️ **طلب جديد!**\n\n"
    full_notification += f"🏪 المتجر: {store_name}\n"
    full_notification += f"🆔 رقم الطلب: {order_id}\n"
    full_notification += f"👤 المشتري: {buyer_name}\n"
    full_notification += f"📞 رقم الهاتف: {buyer_phone}\n"
    full_notification += f"💰 الإجمالي: {order_details[3]} IQD\n"
    full_notification += f"💳 طريقة الدفع: {'نقداً' if order_details[8] == 'cash' else 'على الحساب'}\n"
    full_notification += f"💵 حالة الدفع: {'مدفوع بالكامل' if order_details[9] == 1 else 'غير مدفوع بالكامل'}\n"
    # تنسيق التاريخ (بدون وقت)
    order_date = str(order_details[5]).split()[0]
    full_notification += f"📅 تاريخ الطلب: {order_date}\n"
    
    if order_details[6]:
        full_notification += f"📍 العنوان: {order_details[6]}\n"
    
    full_notification += f"\n📦 **المنتجات:**\n"
    
    # تفاصيل المنتجات للنص الاحتياطي
    for item in items:
        item_id, order_id_val, product_id, quantity, price, returned_qty, return_reason, return_date = item[:8]
        product_name = item[8] if len(item) > 8 else "منتج"
        full_notification += f"• {product_name} × {quantity} = {quantity * price} IQD\n"

    # Minimal caption for the image
    short_caption = f"🛎️ **طلب جديد #{order_id}**\n💰 الإجمالي: {order_details[3]} IQD"


    # Buttons for Order Management
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("تفاصيل 📄", callback_data=f"order_details_{order_id}"),
               types.InlineKeyboardButton("تأكيد ✅", callback_data=f"confirm_order_{order_id}")) # Matches user request
    markup.add(types.InlineKeyboardButton("شحن 🚚", callback_data=f"ship_order_{order_id}"),
               types.InlineKeyboardButton("حذف 🗑️", callback_data=f"delete_order_{order_id}"))
    markup.add(types.InlineKeyboardButton("الرئيسية 🏠", callback_data="seller_main_menu"))
    
    # Save full details to Messages table (for history)
    create_message(order_id, seller_id, 'new_order', full_notification)
    
    try:
        # 🎨 Try to generate Receipt Image
        try:
            # Force Reload to ensure latest changes (Development Mode)
            import importlib
            import utils.receipt_generator
            importlib.reload(utils.receipt_generator)
            from utils.receipt_generator import generate_order_card
            
            receipt_img = generate_order_card(order_details, items, buyer_name, buyer_phone, store_name)
            
            if receipt_img:
                receipt_img.name = f"receipt_{order_id}.png"
                # Use Short Caption with Image AND Buttons
                bot.send_photo(seller_telegram_id, receipt_img, caption=short_caption, reply_markup=markup, parse_mode='Markdown')
                print(f"✅ Sent Visual Receipt for Order #{order_id}")
                return # Stop here if image sent successfully
        except ImportError:
            pass # Pillow not installed
        except Exception as img_err:
            print(f"⚠️ Failed to generate/send receipt image: {img_err}")
            
        # Fallback to Full Text if image fails
        bot.send_message(seller_telegram_id, full_notification, reply_markup=markup, parse_mode='Markdown')
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
        # Save to Disk
        with open(path, "wb") as f:
            f.write(downloaded)
            
        # 🟢 SYNC SUPPORT: Save to Postgres Blob Storage
        if IS_POSTGRES:
            try:
                # bot.send_message(message.chat.id, "🔍 Debug: Attempting Cloud Upload...")
                import psycopg2 
                conn_pg = get_db_connection()
                # Unwrap DBWrapper
                raw_conn = conn_pg.conn 
                cur_pg = raw_conn.cursor()
                
                # Verify table exists
                cur_pg.execute("CREATE TABLE IF NOT EXISTS ImageStorage (FileName TEXT PRIMARY KEY, FileData BYTEA, UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                
                cur_pg.execute(
                    "INSERT INTO ImageStorage (FileName, FileData) VALUES (%s, %s) ON CONFLICT (FileName) DO NOTHING",
                    (filename, psycopg2.Binary(downloaded))
                )
                raw_conn.commit()
                raw_conn.close()
                print(f"✅ [Sync] Saved image {filename} to Cloud DB")
                # bot.send_message(message.chat.id, "✅ Debug: Cloud Upload Success!")
            except Exception as pg_e:
                error_msg = f"⚠️ [Sync] Cloud Upload Failed: {pg_e}"
                print(error_msg)
                try:
                    bot.send_message(message.chat.id, error_msg)
                except: pass
        else:
             print("⚠️ [Sync] IS_POSTGRES is False. Skipping Cloud Upload.")
             # try:
             #    bot.send_message(message.chat.id, "⚠️ Debug: IS_POSTGRES is False. Database URL ignored?")
             # except: pass
        
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

def escape_markdown_v1(text):
    """Escape special characters for legacy Markdown."""
    if not text:
        return ""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

def format_seller_mention(username, seller_telegram_id):
    """Return a safe display for seller username. Do not prefix @ for admin store."""
    try:
        if not username:
            return ''
        if seller_telegram_id == BOT_ADMIN_ID:
            return escape_markdown_v1(username)
        return f"@{escape_markdown_v1(username)}"
    except:
        return escape_markdown_v1(username) or ''

def generate_store_link(telegram_id):
    """توليد رابط المتجر"""
    bot_info = get_bot_info()
    if bot_info['username']:
        return f"https://t.me/{bot_info['username']}?start=store_{telegram_id}"
    return None

# ====== دالة لعرض المنتجات مع صورها ======
def send_product_with_image(chat_id, product, markup=None, seller_name=""):
    """إرسال منتج مع صورته (Generate Card v1)"""
    try:
        pid, name, desc, price, wholesale_price, qty, img_path = product
        
        # 1. Try to Generate Product Card
        try:
            from utils.receipt_generator import generate_product_card
            card_img = generate_product_card(product, seller_name)
            
            if card_img:
                card_img.name = f"product_{pid}.png"
                # Keep caption minimal as details are on the card
                # We still show Quantity as it might not be on card, and maybe a brief text copy
                caption = f"📦 **{name}**\n📦 المتوفر: {qty}"
                
                bot.send_photo(chat_id, card_img, caption=caption, reply_markup=markup, parse_mode='Markdown')
                return
        except Exception as e:
            print(f"⚠️ Product Card Generation Failed: {e}")
            # Fallthrough to legacy raw image logic
            
        # 2. Legacy Logic (Raw Image/Text)
        print(f"DEBUG: sending raw product {pid} ({name}) [Fallback]")
        
        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD"
        if wholesale_price and wholesale_price > 0:
            caption += f"\n💰 سعر الجملة: {wholesale_price} IQD"
        caption += f"\n📦 متاح: {qty}"
        if seller_name:
            caption += f"\n🏪 {seller_name}"
        if desc:
            caption += f"\n📝 {desc[:100]}{'...' if len(desc) > 100 else ''}"
        
        if img_path:
            # 1. Check direct path
            if os.path.exists(img_path):
                try:
                    with open(img_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    return
                except Exception as e:
                    print(f"⚠️ Error sending image from direct path {img_path}: {e}")
            
            # 2. Check in IMAGES_FOLDER by basename
            base_name = os.path.basename(img_path)
            alt_path = os.path.join(IMAGES_FOLDER, base_name)
            
            if not os.path.exists(alt_path) and IS_POSTGRES:
                # 3. Try download from Cloud
                download_image_from_cloud(base_name)
            
            if os.path.exists(alt_path):
                try:
                    with open(alt_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    return
                except Exception as e:
                    print(f"⚠️ Error sending image from alt path {alt_path}: {e}")

        # Fallback: Send message without image
        if markup:
            bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, caption, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ خطأ في send_product_with_image: {e}")
        traceback.print_exc()

# ====== دالة مساعدة لإنشاء أزرار الكمية ======
def create_product_markup_with_qty(product_id, current_qty=1, is_admin_store=False):
    markup = types.InlineKeyboardMarkup()
    # Removed check: if not is_admin_store:
    # Always allow buying
    
    # Quantity Control Row
    markup.row(
        types.InlineKeyboardButton("➖", callback_data=f"qty_dec_{product_id}_{current_qty}"),
        types.InlineKeyboardButton(f"{current_qty}", callback_data="noop"),
        types.InlineKeyboardButton("➕", callback_data=f"qty_inc_{product_id}_{current_qty}")
    )
    # Add to Cart Button with Quantity
    markup.add(types.InlineKeyboardButton(f"🛒 أضف {current_qty} للسلة", callback_data=f"addtocart_{product_id}_{current_qty}"))
    print(f"DEBUG: Created Markup for PID {product_id}, Qty {current_qty}. Encoded: {markup.to_json()}")
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("qty_"))
def handle_qty_update(call):
    try:
        parts = call.data.split("_")
        action = parts[1] # inc or dec
        product_id = int(parts[2])
        current_qty = int(parts[3])
        
        new_qty = current_qty
        if action == "inc":
            new_qty += 1
        elif action == "dec":
            if current_qty > 1:
                new_qty -= 1
        
        if new_qty != current_qty:
            # Re-generate markup with new quantity
            # We need to check if it's admin store, but usually this button only appears if not admin.
            # However, for safety we can assume False or check product owner.
            # For UI speed, we assume False here as these buttons are only added if !is_admin_store
            markup = create_product_markup_with_qty(product_id, new_qty, is_admin_store=False)
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_qty_update: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ")

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
            send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
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
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "👤 تسجيل حساب جديد")
    markup.row("🏠 الرئيسية")
    
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
    # Row 1
    markup.row("👑 لوحة التحكم الإدارية", "🏪 منتجاتي", "📁 الأقسام")
    # Row 2
    markup.row("📦 الطلبات", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    # Row 3
    markup.row(f"📩 الرسائل{messages_badge}", "🔗 رابط المتجر", "📊 إحصائيات النظام")
    # Row 4
    markup.row("🗑️ حذف متجر", "➕ إضافة متجر", "📋 قائمة المتاجر")
    # Row 5
    markup.row("👑 إدارة الحسابات", "🛍️ وضع المشتري", "🏠 الرئيسية")
    
    welcome_msg = f"👑🏪 **مرحباً بأدمن البوت وصاحب المتجر!**\n\n"
    welcome_msg += f"🏪 متجرك: {store_name}\n"
    welcome_msg += f"👑 صلاحياتك: إدارة النظام الكاملة"
    
    if unread_count > 0:
        welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

def show_admin_dashboard(message):
    """لوحة التحكم الإدارية فقط"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    markup.row("👑 إدارة الحسابات", "📊 إحصائيات النظام", "🗑️ حذف متجر")
    markup.row("➕ إضافة متجر", "📋 قائمة المتاجر", "🛍️ وضع المشتري")
    markup.row("🏠 الرئيسية")
    
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

# ====== عرض قائمة البائع ======
def show_seller_menu(message):
    telegram_id = message.from_user.id
    
    # التحقق أولاً إذا كان المستخدم مسجل كبائع
    seller = get_seller_by_telegram(telegram_id)
    # print(f"DEBUG: show_seller_menu - User: {telegram_id}, Seller: {seller}")
    
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
    
    # تحديث الشارة لتظهر عدد الطلبات المعلقة
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ? AND Status IN ('Pending', 'Confirmed', 'Shipped')", (seller[0],))
    pending_count = cursor.fetchone()[0]
    
    # Self-Cleaning: Mark messages as read for processed orders (Shipped/Delivered/Rejected)
    # This fixes "stuck" counters for orders processed before the previous fix or outside the flow.
    cursor.execute("""
        UPDATE Messages 
        SET IsRead = 1 
        WHERE SellerID = ? 
          AND IsRead = 0 
          AND OrderID IN (SELECT OrderID FROM Orders WHERE Status IN ('Shipped', 'Delivered', 'Rejected'))
    """, (seller[0],))
    if cursor.rowcount > 0:
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM Messages WHERE SellerID = ? AND IsRead = 0", (seller[0],))
    unread_messages = cursor.fetchone()[0]
    conn.close()
    
    # Red Circle Badges 🔴
    messages_badge = f" 🔴 {unread_messages}" if unread_messages > 0 else ""
    orders_badge = f" 🔴 {pending_count}" if pending_count > 0 else ""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    # Row 1
    markup.row("🏪 منتجاتي", "📁 الأقسام", f"📦 الطلبات{orders_badge}")
    # Row 2
    markup.row(f"📩 الرسائل{messages_badge}", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    # Row 3
    markup.row("🔗 رابط المتجر", "🛍️ وضع المشتري", "🏠 الرئيسية")
    
    welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
    welcome_msg += f"🏪 متجرك: {store_name}"
    
    if pending_count > 0:
        welcome_msg += f"\n\nلديك {pending_count} طلبات جديدة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

# ... (Existing code) ...



# ====== عرض الطلبات للبائع ======
@bot.message_handler(func=lambda message: "📦 الطلبات" in message.text and is_seller(message.from_user.id))
def handle_seller_orders_menu(message):
    try:
        print("DEBUG: handle_seller_orders_menu triggered") # DEBUG
        telegram_id = message.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        print(f"DEBUG: Seller info: {seller}") # DEBUG
        
        if not seller:
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب آخر 10 طلبات مع التفاصيل الكاملة (مشابه لـ seller_messages)
        query = """
            SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
                   COALESCE(u.FullName, 'زائر') as BuyerName,
                   COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
                   o.PaymentMethod, o.DeliveryAddress, o.Notes
            FROM Orders o
            LEFT JOIN Users u ON o.BuyerID = u.TelegramID
            WHERE o.SellerID = ?
            ORDER BY 
                CASE WHEN o.Status = 'Pending' THEN 0 ELSE 1 END,
                o.CreatedAt DESC
            LIMIT 10
        """
        
        cursor.execute(query, (seller[0],))
        orders = cursor.fetchall()
        print(f"DEBUG: Retrieved {len(orders)} orders: {orders}") # DEBUG
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد طلبات حالياً.")
            conn.close()
            return
            
        bot.send_message(message.chat.id, f"📦 **قائمة الطلبات**\n🏪 {seller[3]}\nيتم عرض آخر 10 طلبات:", parse_mode='Markdown')
        
        for order in orders:
            oid, total, status, date, buyer, phone, pay_method, address, notes = order
            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            # Check cloud images (Previous Logic)
            if items:
                 for i in items:
                    p_name = i[0] if i[0] else "منتج"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img: 
                        first_image_path = img
                        
                    # 🟢 SYNC SUPPORT: Download image if missing locally (Check EVERY item)
                    if img and IS_POSTGRES:
                        if not os.path.exists(img):
                            try:
                                filename = os.path.basename(img)
                                alt_path = os.path.join(IMAGES_FOLDER, filename)
                                if not os.path.exists(alt_path):
                                     if download_image_from_cloud(filename):
                                         print(f"DEBUG: Downloaded {filename} from Cloud ImageStorage for Order {oid}")
                            except Exception as e:
                                print(f"DEBUG: Failed to download cloud image {img}: {e}")
                    
                    row_total = qty * price
                    items_text += f"\n🛍️ *{p_name}*\n"
                    items_text += f"   {qty} x {price:,.0f} = {row_total:,.0f}\n" 

            if not items_text:
                items_text = ""

            # ... Button Logic ... (Omitted to keep it simple, I target the mock tuple creation specifically if possible. No, need surrounding for context if replacing huge chunk)
            # Actually, I can allow replace to match the 'query' part and the 'mock_order' part separately if I use multi?
            # No, 'replace_file_content' is single block.
            # I will Replace the query block first (Fix Indent).
            
            # Wait, I can target just the mock_order_details line if the query block is fixed? 
            # The query block WAS replaced in the LAST step and broke indentation. I MUST fix it.
            # So I will replace the query block again with correct indentation.
            
            # AND I need to update 'mock_order_details'. That is further down.
            # If I select the whole block from 2277 to 2458 it's too big.
            # I will use multi_replace_file_content this time.

            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            # ... (Image handling loop code remains same, skipping for brevity in search replacement if possible? No, need to be contiguous)
            # Actually I can't skip lines easily with replace_file_content if I'm replacing a huge block unless I include them.
            # I will just replace the top part and the packing part.
            
            # Wait, replace_file_content checks for exact match.
            # I'll just Replace the Query block and the Unpacking line.
            
            # But there is code in between?
            # No.
            # Query is lines 2277-2289.
            # Execute 2291.
            # Loop start 2302.
            # Unpack 2303.
            
            # I will target lines 2277 to 2303.


            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            if not items:
                items_text = "" # User requested to remove the warning line
            else:
                for i in items:
                    p_name = i[0] if i[0] else "منتج محذوف"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img:
                        first_image_path = img
                        
                    items_text += f"• {qty}x {p_name} ({price:,.0f})\n"
                    
            # تنسيق الحالة والتاريخ
            status_map = {
                'Pending': '⏳ قيد الانتظار',
                'Confirmed': '✅ تم التأكيد',
                'Shipped': '🚚 تم الشحن',
                'Delivered': '🎉 تم التسليم',
                'Rejected': '❌ مرفوض'
            }
            status_text = status_map.get(status, status)
            
            # تحويل التاريخ
            try:
                date_obj = datetime.strptime(str(date).split('.')[0], '%Y-%m-%d %H:%M:%S')
                date_fmt = date_obj.strftime('%Y-%m-%d')
            except:
                date_fmt = str(date)
                
            # تنسيق المنتجات
            items_text = ""
            if items:
                 for i in items:
                    p_name = i[0] if i[0] else "منتج"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img: 
                        first_image_path = img
                        
                    # 🟢 SYNC SUPPORT: Download image if missing locally (Check EVERY item)
                    if img and IS_POSTGRES:
                        if not os.path.exists(img):
                            try:
                                filename = os.path.basename(img)
                                # Check if it exists in IMAGES_FOLDER first (alt path) before downloading
                                alt_path = os.path.join(IMAGES_FOLDER, filename)
                                if not os.path.exists(alt_path):
                                     if download_image_from_cloud(filename):
                                         print(f"DEBUG: Downloaded {filename} from Cloud ImageStorage for Order {oid}")
                            except Exception as e:
                                print(f"DEBUG: Failed to download cloud image {img}: {e}")
                    
                    row_total = qty * price
                    # تنسيق المنتج: اسم المنتج (غامق) وتحته التفاصيل
                    items_text += f"\n🛍️ *{p_name}*\n"
                    items_text += f"   {qty} x {price:,.0f} = {row_total:,.0f}\n" 

            if not items_text:
                items_text = ""

            # ================= تصميم البطاقة =================
            # بدلاً من النص العادي، سنقوم بتوليد صورة البطاقة
            
            # استعادة الأزرار
            markup = types.InlineKeyboardMarkup()
            
            # الصف الأول: أزرار الإجراءات الرئيسية (تأكيد / شحن)
            actions_row = []
            if status == 'Pending':
                 actions_row.append(types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_order_{oid}"))
            elif status == 'Confirmed':
                 actions_row.append(types.InlineKeyboardButton("🚚 شحن", callback_data=f"ship_order_{oid}"))
            
            # الصف الثاني: زر الحذف (أيقونة سلة المهملات)
            btns = []
            btns.append(types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_order_{oid}"))
            
            if actions_row:
                btns.insert(0, actions_row[0]) 
                
            markup.row(*btns)
            
            # 🎨 Generate Visual Card using the new REV 11 logic
            try:
                # Force Reload for Dev
                import importlib
                import utils.receipt_generator
                importlib.reload(utils.receipt_generator)
                from utils.receipt_generator import generate_order_card

                # Generator expects: (order_details, items, buyer_name, buyer_phone, store_name)
                # handle_seller_orders_menu has: oid, total, status, date, buyer, phone, pay_method, address
                # store_name comes from 'seller' tuple index 3
                
                # Construct Mock Order Details Tuple to match expectations:
                # [0] OrderID
                # [1] BuyerID (Not used in visual, pass 0)
                # [2] SellerID (Not used in visual, pass 0)
                # [3] TotalAmount (Used)
                # [4] Status (Used)
                # [5] CreatedAt (Used)
                # [6] DeliveryAddress (Used)
                # [6] DeliveryAddress (Used)
                mock_order_details = (oid, 0, 0, total, status, date, address, notes)
                
                # RESTRUCTURE ITEMS to match Generator Expectations
                # Generator expects: item[3]=Qty, item[4]=Price, item[8]=Name, item[10]=Image, item[13]=Image
                # Current 'items' from DB query (line 2307): (Name, Qty, Price, ImagePath)
                
                gen_items = []
                for db_item in items:
                    # db_item: (Name, Qty, Price, ImagePath)
                    d_name = db_item[0]
                    d_qty = db_item[1]
                    d_price = db_item[2]
                    d_img = db_item[3]
                    
                    # Create Mock Tuple (Length 15)
                    # Indices: 0,1,2, QTY(3), PRICE(4), 5,6,7, NAME(8), 9, IMG(10), 11,12, IMG(13), 14
                    mock_item = [None]*15
                    mock_item[3] = d_qty
                    mock_item[4] = d_price
                    mock_item[8] = d_name
                    mock_item[10] = d_img
                    mock_item[13] = d_img
                    gen_items.append(tuple(mock_item))
                
                # Generate
                card_img = generate_order_card(mock_order_details, gen_items, buyer, phone, seller[3])
                
                if card_img:
                    card_img.name = f"card_{oid}.png"
                    # Send Image Card
                    bot.send_photo(message.chat.id, card_img, reply_markup=markup)
                else:
                    # Fallback to text if generation fails
                    raise Exception("Image generation returned None")

            except Exception as e:
                print(f"Card generation error for Order list: {e}")
                # Fallback to Text
                card_text = f"{status_text} | طلب #{oid}\n"
                card_text += f"📅 {date_fmt}\n"
                card_text += f"👤 {buyer}\n"
                card_text += f"💰 **الإجمالي: {total:,.0f} د.ع**"
                
                if first_image_path and os.path.exists(first_image_path):
                    with open(first_image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=card_text, reply_markup=markup, parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, card_text, reply_markup=markup, parse_mode='Markdown')
                
        conn.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض الطلبات:\n{str(e)}")

def show_buyer_main_menu(message=None, chat_id=None, user_id=None):
    """عرض قائمة المشتري - يمكن استدعاؤها مع message أو chat_id و user_id"""
    if message:
        telegram_id = message.from_user.id
        chat_id = message.chat.id
    elif chat_id and user_id:
        telegram_id = user_id
    else:
        return
    
    user = get_user(telegram_id)
    
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    if telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest'):
        # For guest buyers show only the Cart button
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("سلة المشتريات 🛒")

        bot.send_message(chat_id,
                        "👀 **مرحباً بك كزائر!**\n\n"
                        "يمكنك تصفح المتاجر وإضافة المنتجات للسلة.\n"
                        "عند إنهاء الطلب، سيُطلب منك إدخال معلوماتك.",
                        reply_markup=markup)
        return
    
    # For registered buyers show only the Cart button
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("سلة المشتريات 🛒")

    welcome_msg = "👋 **مرحباً بك كـ مشتري!**"
    
    if user and (user[4] or user[5]):
        welcome_msg += f"\n\n👤 الاسم: {user[5] if user[5] else 'غير محدد'}"
        welcome_msg += f"\n📞 الهاتف: {user[4] if user[4] else 'غير محدد'}"
    
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

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

# ====== معالجة إنشاء متجر للمستخدمين ======
@bot.message_handler(func=lambda message: message.text == "🏪 إنشاء متجر جديد")
def handle_create_user_store(message):
    telegram_id = message.from_user.id
    
    # التحقق من أن المستخدم ليس بائعاً بالفعل
    seller = get_seller_by_telegram(telegram_id)
    if seller:
        bot.send_message(message.chat.id, "⛔ لديك متجر بالفعل!")
        return

    user_states[telegram_id] = {
        "step": "create_user_store_name"
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏠 الرئيسية")
    
    bot.send_message(message.chat.id,
                    "🏪 **إنشاء متجر جديد**\n\n"
                    "يرجى إدخال اسم المتجر الذي ترغب بإنشائه:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "create_user_store_name")
def process_user_store_name(message):
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[user_id]
        if message.text == "🔙 رجوع":
            # Check user type to decide where to go, or just main menu
            handle_main_menu(message)
        else:
            handle_main_menu(message)
        return
        
    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المتجر كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    user_id = message.from_user.id
    store_name = message.text.strip()
    
    if not store_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمتجر.")
        return
    
    # إنشاء متجر للمستخدم
    username = message.from_user.username or message.from_user.first_name
    add_seller(user_id, username, store_name)
    
    # تحديث نوع المستخدم إلى بائع
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("UPDATE Users SET UserType = 'seller' WHERE TelegramID = %s", (user_id,))
    else:
        cursor.execute("UPDATE Users SET UserType = 'seller' WHERE TelegramID = ?", (user_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id,
                    f"✅ **تم إنشاء متجرك بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, user_id)}\n\n"
                    f"يمكنك الآن البدء بإضافة المنتجات وإدارة متجرك.")
    
    # --- Notify Admin ---
    try:
        # Generate link if possible
        store_link = generate_store_link(user_id)
        links_text = f"\n🔗 **رابط المتجر:**\n`{store_link}`" if store_link else ""
        
        bot.send_message(BOT_ADMIN_ID, 
                f"🆕 **تم تسجيل متجر جديد!**\n\n"
                f"🏪 المتجر: {store_name}\n"
                f"👤 المالك: {format_seller_mention(username, user_id)}\n"
                f"🆔 المعرف: {user_id}\n"
                f"{links_text}\n\n"
                f"يرجى مراجعة المتجر وتفعيله (إذا كان التفعيل اليدوي مطلوباً).",
                parse_mode='Markdown')
    except Exception as e:
        print(f"Failed to notify admin about new store: {e}")
    # --------------------
    
    del user_states[user_id]
    show_seller_menu(message)

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
    cursor.execute("SELECT COUNT(*) FROM CreditLimits WHERE IsActive IS TRUE")
    active_credit_limits = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(MaxCreditAmount), SUM(CurrentUsedAmount) FROM CreditLimits WHERE IsActive IS TRUE")
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
        
        # تحديث الشارة لتظهر عدد الطلبات المعلقة
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()  # This returns CursorWrapper
        try:
            cursor_wrapper.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ? AND Status IN ('Pending', 'Confirmed')", (seller[0],))
            result = cursor_wrapper.fetchone()
            pending_count = result[0] if result else 0
        except Exception as e:
            print(f"Error getting pending orders count: {e}")
            pending_count = 0
        finally:
            cursor_wrapper.close()
            conn.close()
        
        messages_badge = f" 📩({pending_count})" if pending_count > 0 else ""
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        # Row 1
        markup.row("🏪 منتجاتي", "📁 الأقسام", "📊 كشف حساب الزبائن")
        # Row 2
        markup.row("🏪 إدارة الزبائن الآجلين", f"📩 الرسائل{messages_badge}", "🔗 رابط المتجر")
        # Row 3
        markup.row("🛍️ وضع المشتري", "🏠 الرئيسية")
        
        welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
        welcome_msg += f"🏪 متجرك: {store_name}"
        if pending_count > 0:
            welcome_msg += f"\n\nلديك {pending_count} طلبات جديدة!"
        
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
                # إذا كان زائراً للمتجر، نعرض له المنتجات (مع التحقق من التسجيل)
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Explicitly select columns to avoid index errors if schema changes
        if IS_POSTGRES:
            cursor.execute("""
                SELECT SellerID, TelegramID, UserName, StoreName, CreatedAt, Status, 
                       COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers
                ORDER BY CreatedAt DESC
            """)
        else:
            cursor.execute("""
                SELECT SellerID, TelegramID, UserName, StoreName, CreatedAt, Status, 
                       COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers
                ORDER BY CreatedAt DESC
            """)
        stores = cursor.fetchall()
        conn.close()
        
        if not stores:
            bot.send_message(message.chat.id, "لا توجد متاجر مسجلة بعد.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        text = "📋 **قائمة جميع المتاجر:**\n\n"
        
        for store in stores:
            seller_id, telegram_id, username, store_name, created_at, status = store[:6]
            require_reg = store[6] if len(store) > 6 else 0
            status_icon = "✅" if status == 'active' else "⏸️"
            reg_icon = "🔒" if require_reg == 1 else "🔓"
            
            # Escape store name to prevent markdown errors
            safe_store_name = escape_markdown_v1(store_name)
            
            text += f"{status_icon} {reg_icon} **المتجر:** {safe_store_name}\n"
            text += f"👤 المالك: {format_seller_mention(username, telegram_id)}\n"
            text += f"🆔 المعرف: {telegram_id}\n"
            text += f"📅 تاريخ الإنشاء: {created_at}\n"
            text += f"📊 الحالة: {'نشط' if status == 'active' else 'معلق'}\n"
            text += f"🔐 قيد الدخول: {'مفعل (يتطلب تسجيل)' if require_reg == 1 else 'معطل (مفتوح للجميع)'}\n"
            text += "────\n\n"
            
            # إضافة زر لإدارة إعدادات المتجر
            label = f"{safe_store_name[:30]} - {'🔒' if require_reg == 1 else '🔓'}"
            markup.add(types.InlineKeyboardButton(
                label,
                callback_data=f"manage_store_reg_{seller_id}"
            ))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض القائمة:\n{e}")

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
    
    # safeguard: IF NOT MOCK (Real user click on old button), Redirect to new menu
    if not getattr(message, 'is_mock', False):
        bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
        show_seller_menu(message)
        return

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        # Debugging "Not a seller" issue
        bot.send_message(message.chat.id, f"⛔ أنت لست بائعاً مسجلاً! (Debug ID: {telegram_id})")
        return
    
    user_states[telegram_id] = {
        "step": "add_category",
        "seller_id": seller[0]
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏠 الرئيسية")
    
    bot.send_message(message.chat.id, "📁 **إضافة قسم جديد**\n\nيرجى إدخال اسم القسم:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_category")
def add_category_step2(message):
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم القسم كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية' أو '🔙 رجوع'.")
        return
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
    
    # safeguard: IF NOT MOCK (Real user click on old button), Redirect to new menu
    if not getattr(message, 'is_mock', False):
        bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
        show_seller_menu(message)
        return

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام لتعديلها.\n\nيمكنك إضافة قسم جديد أولاً.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
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
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🏠 الرئيسية")
        
        bot.send_message(call.message.chat.id,
                        f"📁 **تعديل قسم**\n\n"
                        f"القسم الحالي: {category[2]}\n\n"
                        f"يرجى إدخال الاسم الجديد للقسم:", reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

# دالة جديدة لعرض قائمة الأقسام للتعديل (بدلاً من تعديل قسم محدد مباشرة)
def view_edit_category_menu(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return

    categories = get_categories(seller[0])
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام لتعديلها.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        # Revert to Tuple Access
        cid, name = cat[0], cat[1]
        markup.add(types.InlineKeyboardButton(f"📁 {name}", callback_data=f"view_cat_{cid}"))
    
    markup.add(types.InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="dashboard_add_cat"))
    markup.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, "📁 **أقسام متجرك**\n\nاضغط على القسم للتحكم به.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_cat_"))
def handle_view_category_detail(call):
    try:
        category_id = int(call.data.split("_")[2])
        category = get_category_by_id(category_id)
        
        if not category:
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
            
        cid = category[0]
        name = category[2]
        
        text = f"📁 **{name}**\n\n"
        text += "يمكنك التحكم في هذا القسم من هنا."
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة", callback_data="dashboard_add_cat"),
            types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_cat_{cid}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_cat_{cid}") # Need to ensure delete_cat handler exists
        )
        markup.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="back_to_cat_list"))
        
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        bot.answer_callback_query(call.id)
    except Exception as e:
         bot.answer_callback_query(call.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_cat_list")
def back_to_cat_list(call):
    call.message.from_user.id = call.from_user.id
    view_categories(call.message)
    bot.answer_callback_query(call.id)
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    markup_hidden = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_hidden.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=markup_hidden)
    
    bot.send_message(message.chat.id, "📁 **تعديل قسم**\n\nاختر القسم الذي تريد تعديله:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_category_name")
def edit_category_step2(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_name = message.text.strip()

    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم القسم كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    
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
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    text = "📁 **إدارة الأقسام**\n\n"
    text += "هنا يمكنك إدارة أقسام متجرك (إضافة، تعديل، حذف، وعرض).\n\n"
    text += "**الأقسام الحالية:**\n"
    
    if categories:
        for i, category in enumerate(categories, 1):
            category_id, category_name = category
            text += f"{i}. **{category_name}**\n"
            text += f"   🆔 معرف القسم: {category_id}\n"
            text += "────\n"
    else:
        text += "📭 لا توجد أقسام حالياً.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قسم", callback_data="dashboard_add_cat"),
        types.InlineKeyboardButton("✏️ تعديل قسم", callback_data="dashboard_edit_cat"),
        types.InlineKeyboardButton("🗑️ حذف قسم", callback_data="delete_category_menu"),
        types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "add_new_category")
def handle_add_new_category(call):
    add_category_step1(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "go_to_edit_category")
def handle_go_to_edit_category(call):
    edit_category_step1(call.message)
    bot.answer_callback_query(call.id)

# ====== معالجة أزرار الحذف النصية (القائمة الرئيسية) ======
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف منتج" and is_seller(message.from_user.id))
def handle_delete_product_text(message):
    bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.text == "🗑️ حذف قسم" and is_seller(message.from_user.id))
def handle_delete_category_text(message):
    bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
    show_seller_menu(message)

# ====== حذف متجر (للأدمن) ======
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف متجر" and is_bot_admin(message.from_user.id))
def handle_delete_store_text(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SellerID, StoreName, Status FROM Sellers ORDER BY CreatedAt DESC")
    stores = cursor.fetchall()
    conn.close()
    
    if not stores:
        bot.send_message(message.chat.id, "📭 لا توجد متاجر لحذفها.")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for store in stores:
        sid, name, status = store
        status_icon = "✅" if status == 'active' else "⏸️"
        markup.add(types.InlineKeyboardButton(f"🗑️ {name} {status_icon}", callback_data=f"confirm_delete_store_{sid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🗑️ **حذف متجر**\n\nاضغط على المتجر لحذفه نهائياً:",
                    reply_markup=markup,
                    parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_store_"))
def handle_confirm_delete_store(call):
    store_id = int(call.data.split("_")[3])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف نهائياً", callback_data=f"do_delete_store_{store_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        f"⚠️ **تحذير: حذف المتجر**\n\nهل أنت متأكد من حذف المتجر رقم {store_id}؟\nسيؤدي هذا إلى حذف جميع المنتجات والأقسام والطلبات المرتبطة به.\n\n⚠️ **لا يمكن التراجع عن هذا الإجراء!**",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_store_"))
def handle_do_delete_store(call):
    store_id = int(call.data.split("_")[3])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete related data first (cascade manually if needed, or rely on FK cascade if configured)
    # Since we didn't specify ON DELETE CASCADE in init_db, we should delete manually or update schema.
    # For safety, let's delete manually.
    try:
        cursor.execute("DELETE FROM OrderItems WHERE OrderID IN (SELECT OrderID FROM Orders WHERE SellerID = ?)", (store_id,))
        cursor.execute("DELETE FROM Orders WHERE SellerID = ?", (store_id,))
        cursor.execute("DELETE FROM Carts WHERE ProductID IN (SELECT ProductID FROM Products WHERE SellerID = ?)", (store_id,))
        cursor.execute("DELETE FROM Products WHERE SellerID = ?", (store_id,))
        cursor.execute("DELETE FROM Categories WHERE SellerID = ?", (store_id,))
        cursor.execute("DELETE FROM CreditLimits WHERE SellerID = ?", (store_id,))
        cursor.execute("DELETE FROM CreditCustomers WHERE SellerID = ?", (store_id,))
        cursor.execute("DELETE FROM Sellers WHERE SellerID = ?", (store_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ تم حذف المتجر بنجاح")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **تم حذف المتجر وجميع بياناته بنجاح.**")
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ أثناء الحذف")
        print(f"Delete Store Error: {e}")
    finally:
        conn.close()

# ====== لوحة التحكم والحذف ======
@bot.message_handler(func=lambda message: message.text == "📊 لوحة التحكم" and is_seller(message.from_user.id))
def handle_seller_control_panel(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🗑️ حذف منتج", callback_data="delete_product_menu"))
    markup.add(types.InlineKeyboardButton("🗑️ حذف قسم", callback_data="delete_category_menu"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "📊 **لوحة التحكم**\n\n"
                    "اختر الإجراء المطلوب:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delete_product_menu")
def handle_delete_product_menu(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
        return
        
    products = get_products(seller_id=seller[0])
    
    if not products:
        bot.answer_callback_query(call.id, "لا توجد منتجات لحذفها", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for product in products: # Show allow products
        pid, name = product[0], product[1]
        markup.add(types.InlineKeyboardButton(f"🗑️ {name}", callback_data=f"confirm_delete_prod_{pid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "🗑️ **حذف منتج**\n\nاضغط على المنتج لحذفه:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_prod_"))
def handle_confirm_delete_product(call):
    product_id = int(call.data.split("_")[3])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف", callback_data=f"do_delete_prod_{product_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="delete_product_menu"))
    
    product = get_product_by_id(product_id)
    if product:
        name = product[3]
        bot.edit_message_text(
            f"⚠️ **هل أنت متأكد من حذف المنتج؟**\n\n🛒 المنتج: {name}\n\n⚠️ لا يمكن التراجع عن هذا الإجراء.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "المنتج غير موجود")

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_prod_"))
def handle_do_delete_product(call):
    product_id = int(call.data.split("_")[3])
    
    # 1. Fetch product to get image path BEFORE deletion
    product = get_product_by_id(product_id)
    image_path = None
    if product:
        # Structure: ProductID(0), ..., ImagePath(8)
        image_path = product[8]

    # 2. Delete from Database
    delete_product(product_id)
    
    # 3. Delete Image File if exists
    if image_path:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"🗑️ Deleted image file: {image_path}")
        except Exception as e:
            print(f"⚠️ Failed to delete image file {image_path}: {e}")

    bot.answer_callback_query(call.id, "✅ تم حذف المنتج والصورة")
    handle_delete_product_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "delete_category_menu")
def handle_delete_category_menu(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
        return
        
    categories = get_categories(seller[0])
    
    if not categories:
        bot.answer_callback_query(call.id, "لا توجد أقسام لحذفها", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        cid, name = cat[0], cat[1]
        markup.add(types.InlineKeyboardButton(f"🗑️ {name}", callback_data=f"try_delete_cat_{cid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "🗑️ **حذف قسم**\n\nاضغط على القسم لحذفه:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("try_delete_cat_"))
def handle_try_delete_category(call):
    category_id = int(call.data.split("_")[3])
    
    # Check if category has products
    count = get_product_count_in_category(category_id)
    if count > 0:
        bot.answer_callback_query(call.id, f"⛔ لا يمكن حذف القسم!\nيحتوي على {count} منتج.", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف", callback_data=f"do_delete_cat_{category_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="delete_category_menu"))
    
    category = get_category_by_id(category_id)
    if category:
        name = category[2]
        bot.edit_message_text(
            f"⚠️ **هل أنت متأكد من حذف القسم؟**\n\n📁 القسم: {name}\n\n⚠️ لا يمكن التراجع عن هذا الإجراء.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "القسم غير موجود")

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_cat_"))
def handle_do_delete_category(call):
    category_id = int(call.data.split("_")[3])
    delete_category(category_id)
    bot.answer_callback_query(call.id, "✅ تم حذف القسم")
    handle_delete_category_menu(call)

# ====== وظائف إضافة وتعديل المنتج ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة منتج" and is_seller(message.from_user.id))
def add_product_step1(message):
    telegram_id = message.from_user.id
    
    # safeguard: IF NOT MOCK (Real user click on old button), Redirect to new menu
    if not getattr(message, 'is_mock', False):
        bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
        show_seller_menu(message)
        return

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام بعد.\n\nيرجى إضافة قسم أولاً قبل إضافة المنتجات.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
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
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🏠 الرئيسية")
        
        bot.send_message(call.message.chat.id, 
                        "🛒 **إضافة منتج جديد**\n\n"
                        "الآن، يرجى إدخال اسم المنتج:", reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_name")
def add_product_step2(message):
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المنتج كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية' أو '🔙 رجوع'.")
        return
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    seller_id = state["seller_id"]
    
    # التحقق من حالة المتجر
    seller = get_seller_by_id(seller_id)
    require_registration = False
    if seller and len(seller) > 9:
        require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
    
    # إذا كان المتجر مقفول، تخطي طلب الكمية (ستكون تلقائية من عدد الصور)
    if require_registration:
        user_states[telegram_id]["quantity"] = 1  # افتراضياً 1، سيتم تحديثها تلقائياً من عدد الصور
        user_states[telegram_id]["step"] = "add_product_image"
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("📸 إرسال صور متعددة", "⏭️ تخطي بدون صور")
        
        bot.send_message(message.chat.id, 
                        "📸 **صور المنتج**\n\n"
                        "⚠️ **ملاحظة:** الكمية ستكون تلقائياً بعدد الصور التي ستضيفها.\n\n"
                        "الآن، يمكنك إرسال صور متعددة للمنتج:\n\n"
                        "• اضغط '📸 إرسال صور متعددة' لإرسال صور (يمكن إرسال عدة صور)\n"
                        "• أو اضغط '⏭️ تخطي بدون صور' للمتابعة بدون صور",
                        reply_markup=markup)
    else:
        # المتجر مفتوح - طلب الكمية يدوياً
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    if message.text == "📸 إرسال صورة":
        user_states[telegram_id]["step"] = "waiting_for_product_image"
        bot.send_message(message.chat.id, "📤 الرجاء إرسال صورة المنتج الآن:")
        return
    elif message.text == "📸 إرسال صور متعددة":
        user_states[telegram_id]["step"] = "waiting_for_product_images"
        user_states[telegram_id]["product_images"] = []
        
        # إضافة زر "تم" في لوحة المفاتيح
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("✅ تم - حفظ المنتج")
        
        bot.send_message(message.chat.id, 
                        "📤 **إرسال صور متعددة**\n\n"
                        "الآن، يمكنك إرسال عدة صور للمنتج.\n"
                        "بعد الانتهاء من إرسال جميع الصور، اضغط '✅ تم - حفظ المنتج' لحفظ المنتج.",
                        reply_markup=markup)
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
                     user_states[message.from_user.id].get("step") in ["waiting_for_product_image", "waiting_for_product_images"])
def handle_product_image_photo(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    step = state.get("step")
    
    try:
        image_path = save_photo_from_message(message)
        if not image_path:
            bot.send_message(message.chat.id, "⚠️ حدث خطأ في حفظ الصورة.")
            return
        
        if step == "waiting_for_product_images":
            # للمتاجر المقفولة: حفظ الصور في قائمة مؤقتة
            if "product_images" not in state:
                state["product_images"] = []
            state["product_images"].append(image_path)
            
            # إضافة زر "تم" في لوحة المفاتيح
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.row("✅ تم - حفظ المنتج", "➕ إضافة المزيد من الصور")
            
            bot.send_message(message.chat.id, 
                           f"✅ تم حفظ الصورة ({len(state['product_images'])} صورة حتى الآن)\n\n"
                           "📤 أرسل المزيد من الصور أو اضغط '✅ تم - حفظ المنتج' لحفظ المنتج.",
                           reply_markup=markup)
        else:
            # للمتاجر المفتوحة: صورة واحدة فقط
            finish_adding_product(message, image_path)
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الصورة: {e}")
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في معالجة الصورة.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_product_image" and 
                     message.content_type == 'text')
def handle_product_image_text(message):
    telegram_id = message.from_user.id
    if message.text.lower() in ['تخطي', 'تخطي بدون صورة', 'skip', 'الغاء']:
        finish_adding_product(message, "")
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'تخطي' للمتابعة بدون صورة.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "waiting_for_product_images" and 
                     message.content_type == 'text')
def handle_product_images_text(message):
    """معالج النص عند إضافة صور متعددة"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text in ['✅ تم - حفظ المنتج', 'تم', 'انتهيت', 'انتهى', 'done', 'finish']:
        # حفظ المنتج مع الصور
        finish_adding_product(message, "")
    elif message.text == "➕ إضافة المزيد من الصور":
        # الاستمرار في إضافة الصور
        bot.send_message(message.chat.id, 
                        "📤 الرجاء إرسال الصور التالية.\n"
                        "بعد الانتهاء، اضغط '✅ تم - حفظ المنتج' لحفظ المنتج.")
    else:
        # إضافة زر "تم" في لوحة المفاتيح
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("✅ تم - حفظ المنتج", "➕ إضافة المزيد من الصور")
        
        bot.send_message(message.chat.id, 
                        "⚠️ الرجاء إرسال صورة أو اضغط '✅ تم - حفظ المنتج' لحفظ المنتج.",
                        reply_markup=markup)

def finish_adding_product(message, image_path=""):
    telegram_id = message.from_user.id
    if telegram_id not in user_states:
        bot.send_message(message.chat.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    state = user_states[telegram_id]
    
    # التحقق من وجود جميع البيانات المطلوبة
    required_fields = ["seller_id", "category_id", "product_name", "price"]
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
    
    # التحقق من حالة المتجر
    seller = get_seller_by_id(seller_id)
    require_registration = False
    if seller and len(seller) > 9:
        require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
    
    # تحديد الكمية
    if require_registration:
        # للمتاجر المقفولة: الكمية الافتراضية = 1، ثم سيتم تحديثها بعد إضافة الصور
        quantity = 1  # افتراضياً، سيتم تحديثها بعد إضافة الصور
    else:
        # للمتاجر المفتوحة: الكمية يدوية
        quantity = state.get("quantity", 1)  # افتراضياً 1
    
    try:
        # إضافة المنتج
        add_product_db(seller_id, category_id, product_name, description, price, wholesale_price, quantity, image_path)
        
        # الحصول على ProductID للمنتج المضاف حديثاً
        conn = get_db_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT ProductID FROM Products WHERE SellerID=%s AND CategoryID=%s AND Name=%s ORDER BY ProductID DESC LIMIT 1", 
                         (seller_id, category_id, product_name))
        else:
            cursor.execute("SELECT ProductID FROM Products WHERE SellerID=? AND CategoryID=? AND Name=? ORDER BY ProductID DESC LIMIT 1", 
                         (seller_id, category_id, product_name))
        result = cursor.fetchone()
        product_id = None
        if result:
            product_id = result[0]
        
        # إذا كان المتجر مقفول، حفظ الصور المتعددة في ProductImages
        if require_registration and product_id:
            product_images = state.get("product_images", [])
            
            # حفظ الصور في ProductImages
            for idx, img_path in enumerate(product_images):
                try:
                    add_product_image_db(product_id, img_path, idx)
                    print(f"✅ تم حفظ الصورة {idx+1}: {img_path}")
                except Exception as e:
                    print(f"⚠️ خطأ في حفظ الصورة {idx+1}: {e}")
            
            # حساب عدد الصور وتحديث الكمية
            if IS_POSTGRES:
                cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=%s", (product_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=?", (product_id,))
            result = cursor.fetchone()
            image_count = result[0] if result else 0
            
            print(f"📊 عدد الصور المحفوظة: {image_count}")
            
            # تحديث الكمية
            if IS_POSTGRES:
                cursor.execute("UPDATE Products SET Quantity=%s WHERE ProductID=%s", (image_count, product_id))
            else:
                cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (image_count, product_id))
            conn.commit()
            quantity = image_count
            print(f"✅ تم تحديث الكمية إلى: {quantity}")
        
        conn.close()
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
    if require_registration:
        success_msg += f"📦 **الكمية:** {quantity} صورة (تلقائية)\n"
    else:
        success_msg += f"📦 **الكمية:** {quantity}\n"
    
    if description:
        success_msg += f"📝 **الوصف:** {description}\n"
    
    # عرض معلومات الصور
    if require_registration:
        product_images = state.get("product_images", [])
        if product_images:
            success_msg += f"📸 **تم رفع {len(product_images)} صورة للمنتج**"
        else:
            success_msg += "📷 **لم يتم رفع صور للمنتج**"
    elif image_path and os.path.exists(image_path):
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
    
    # safeguard: IF NOT MOCK (Real user click on old button), Redirect to new menu
    if not getattr(message, 'is_mock', False):
        bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
        show_seller_menu(message)
        return

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    products = get_products(seller_id=seller[0])
    
    if not products:
        bot.send_message(message.chat.id, "📭 لا توجد منتجات لتعديلها.\n\nيمكنك إضافة منتجات أولاً.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for product in products[:10]:
        pid = product[0]
        name = product[1]
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
        
        # التحقق من حالة المتجر
        seller_id = product[1]
        seller = get_seller_by_id(seller_id)
        require_registration = False
        if seller and len(seller) > 9:
            require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data="edit_prod_name"),
            types.InlineKeyboardButton("📝 تعديل الوصف", callback_data="edit_prod_desc"),
            types.InlineKeyboardButton("💰 تعديل السعر", callback_data="edit_prod_price"),
            types.InlineKeyboardButton("💰 تعديل سعر الجملة", callback_data="edit_prod_wholesale"),
        )
        # إخفاء تعديل الكمية للمتاجر المقفولة (الكمية تلقائية من عدد الصور)
        if not require_registration:
            markup.add(types.InlineKeyboardButton("📦 تعديل الكمية", callback_data="edit_prod_qty"))
        markup.add(
            types.InlineKeyboardButton("📁 تغيير القسم", callback_data="edit_prod_cat"),
            types.InlineKeyboardButton("📸 تغيير الصورة", callback_data="edit_prod_img"),
            types.InlineKeyboardButton("🖼️ إدارة الصور المتعددة", callback_data=f"manage_product_images_{product_id}"),
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
        user_states[telegram_id]["step"] = "waiting_for_new_product_image"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("إلغاء")
        
        bot.send_message(call.message.chat.id,
                        f"📸 **تغيير صورة المنتج**\n\n"
                        f"يرجى إرسال الصورة الجديدة الآن:",
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
    
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المنتج كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    product_id = state["product_id"]
    product = state["product_data"]
    
    # التحقق من حالة المتجر
    seller_id = product[1]
    seller = get_seller_by_id(seller_id)
    require_registration = False
    if seller and len(seller) > 9:
        require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
    
    # إذا كان المتجر مقفول، لا يمكن تعديل الكمية يدوياً
    if require_registration:
        bot.send_message(message.chat.id,
            "⚠️ **لا يمكن تعديل الكمية يدوياً**\n\n"
            "في المتاجر المقفولة، الكمية تحسب تلقائياً من عدد الصور.\n"
            "لتعديل الكمية، أضف أو احذف الصور من قائمة '🖼️ إدارة الصور المتعددة'.")
        del user_states[telegram_id]
        show_seller_menu(message)
        return
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    telegram_id = message.from_user.id
    if message.text == "🏠 الرئيسية":
        if telegram_id in user_states:
            del user_states[telegram_id]
        handle_main_menu(message)
        return

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
        bot.send_message(message.chat.id, 
                        "📭 **لا توجد أقسام بعد**\n\nيجب إنشاء قسم واحد على الأقل قبل إضافة المنتجات.",
                        reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton("➕ إضافة قسم", callback_data="dashboard_add_cat"),
                            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")
                        ))
        return
    
    all_products = []
    
    for category_id, category_name in categories:
        products = get_products(seller_id=seller[0], category_id=category_id)
        if products:
            all_products.append((category_name, products))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_products:
        text = "📭 **لا توجد منتجات حالياً**\n\nيمكنك إضافة منتجات جديدة باستخدام الأزرار أدناه."
    else:
        text = "🏪 **قائمة منتجاتك**\n\nاضغط على المنتج لعرض التفاصيل والتحكم به:\n"
        for category_name, products in all_products:
            # Optional: Add category header
            # markup.add(types.InlineKeyboardButton(f"--- {category_name} ---", callback_data="ignore"))
            
            for product in products:
                # Product tuple: (ProductID, Name, Description, Price, ...)
                pid = product[0]
                name = product[1]
                price = product[3]
                markup.add(types.InlineKeyboardButton(f"📦 {name} - {price}", callback_data=f"view_prod_{pid}"))
    
    # Add Control Buttons (Always Visible)
    markup.row(
        types.InlineKeyboardButton("➕ إضافة منتج", callback_data="dashboard_add_prod"),
        types.InlineKeyboardButton("✏️ تعديل", callback_data="dashboard_edit_prod"),
        types.InlineKeyboardButton("🗑️ حذف", callback_data="delete_product_menu")
    )
    markup.add(types.InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="back_to_menu"))
    
    # Hide menu first (ensure we are in a clean state)
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري الحصول على المنتجات...**", reply_markup=menu_markup)
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_prod_"))
def handle_view_product_detail(call):
    try:
        product_id = int(call.data.split("_")[2])
        # Direct DB Call (Tuple)
        product = get_product_by_id(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return
            
        print(f"DEBUG PRODUCT DATA: {product}") # Debugging

            
        # Structure: ProductID(0), SellerID(1), CategoryID(2), Name(3), Description(4), Price(5), WholesalePrice(6), Quantity(7), ImagePath(8)
        
        pid = product[0]
        name = product[3]
        desc = product[4]
        price = product[5]
        wholesale_price = product[6]
        qty = product[7]
        img_path = product[8]
        
        text = f"📦 **{name}**\n\n"
        text += f"💰 السعر: {price} IQD\n"
        if wholesale_price:
            text += f"💰 سعر الجملة: {wholesale_price} IQD\n"
        text += f"📦 الكمية: {qty}\n"
        if desc: text += f"📝 الوصف: {desc}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        # Check if viewer is the seller/admin (Owner)
        # We need seller_id of the product.
        seller = get_seller_by_id(product[1]) # product[1] is SellerID
        is_owner = False
        
        if seller and seller[1] == call.from_user.id:
             is_owner = True
        elif str(call.from_user.id) == str(BOT_ADMIN_ID): # Global Admin can edit everything? Maybe.
             # For now, stick to seller ownership
             if seller and seller[1] == call.from_user.id:
                 is_owner = True

        if is_owner:
            # Owner View: Edit/Delete
            markup.add(
                types.InlineKeyboardButton("➕ إضافة جديد", callback_data="dashboard_add_prod"),
                types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_product_{pid}"),
                types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_product_{pid}")
            )
        else:
            # Buyer View: Add to Cart
            # Always allow buying, even from Admin store
            # Reuse logic from create_product_markup_with_qty
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"qty_dec_{pid}_1"),
                types.InlineKeyboardButton("1", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"qty_inc_{pid}_1")
            )
            markup.add(types.InlineKeyboardButton(f"🛒 أضف 1 للسلة", callback_data=f"addtocart_{pid}_1"))

        markup.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_prod_list"))

        # Try to resolve valid image path
        final_img_path = None
        if img_path:
            # 1. Check exact path from DB
            if os.path.exists(img_path):
                final_img_path = img_path
            else:
                # 2. Check local Images folder (Fix for OS path mismatch)
                filename = os.path.basename(img_path)
                local_path = os.path.join(IMAGES_FOLDER, filename)
                if os.path.exists(local_path):
                    final_img_path = local_path
                else:
                    # Lazy Download from Cloud if missing
                    print(f"⚠️ Image found in DB but missing locally: {filename}. Attempting download...")
                    if download_image_from_cloud(filename):
                        if os.path.exists(local_path):
                             final_img_path = local_path
                             print(f"✅ Successfully downloaded {filename}")
                        else:
                             print(f"❌ Download reported success but file still missing: {local_path}")
                    else:
                        print(f"❌ Failed to download {filename} from cloud.")

        if final_img_path:
            try:
                with open(final_img_path, 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo, caption=text, parse_mode='Markdown', reply_markup=markup)
            except Exception as img_error:
                print(f"⚠️ Error sending photo for product {pid}: {img_error}")
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
            
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in view_prod: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ أثناء عرض المنتج")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_prod_list")
def back_to_product_list(call):
    # Call view_my_products but passing the message correctly
    call.message.from_user.id = call.from_user.id
    view_my_products(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_product_"))
def handle_delete_product_direct(call):
    try:
        product_id = int(call.data.split("_")[2])
        # Confirm deletion
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete_prod_{product_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"view_prod_{product_id}")
        )
        # Handle different message types (Photo vs Text)
        if call.message.content_type == 'photo':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "⚠️ **هل أنت متأكد من حذف هذا المنتج؟**\nسيتم حذفه من القائمة نهائياً.",
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ **هل أنت متأكد من حذف هذا المنتج؟**\nسيتم حذفه من القائمة نهائياً.",
                parse_mode='Markdown',
                reply_markup=markup
            )
            
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in delete product direct: {e}")
        # Show actual error to user for debugging
        bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)[:50]}", show_alert=True)

# ====== ربط أزرار لوحة التحكم بالوظائف الموجودة ======
class MockMessage:
    def __init__(self, chat, from_user, text):
        self.chat = chat
        self.from_user = from_user
        self.text = text
        self.content_type = 'text'
        self.is_mock = True

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_add_prod")
def bridge_add_product(call):
    # استخدام MockMessage لضمان تمرير كائن المستخدم الصحيح (الذي ضغط الزر)
    # بدلاً من كائن البوت الموجود في call.message original
    mock_msg = MockMessage(call.message.chat, call.from_user, "➕ إضافة منتج")
    add_product_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_edit_prod")
def bridge_edit_product(call):
    mock_msg = MockMessage(call.message.chat, call.from_user, "✏️ تعديل منتج")
    edit_product_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_del_prod")
def bridge_delete_product(call):
    # دالة الحذف تستخدم call مباشرة، لذا يجب أن تعمل إذا كان الـ id صحيحاً
    # سنتأكد من تمرير الـ call كما هو
    handle_delete_product_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_add_cat")
def bridge_add_category(call):
    # Debug: Print ID to verify
    # bot.send_message(call.message.chat.id, f"Debug ID: {call.from_user.id}")
    mock_msg = MockMessage(call.message.chat, call.from_user, "➕ إضافة قسم")
    add_category_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_edit_cat")
def bridge_edit_category(call):
    # Fix: Call the list menu, not the specific handler
    mock_msg = MockMessage(call.message.chat, call.from_user, "✏️ تعديل قسم")
    view_edit_category_menu(mock_msg)
    bot.answer_callback_query(call.id)


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
        if len(customer) >= 10:
            customer_id, seller_id, full_name, phone, telegram_id, customer_type, created_at, max_credit, current_used, limit_active = customer[:10]
        else:
            # Fallback for old format (without TelegramID)
            customer_id, seller_id, full_name, phone, customer_type, created_at, max_credit, current_used, limit_active = customer[:9]
            telegram_id = None
        
        customer_type_arabic = "👤 زبون آجل" if customer_type == 'CreditCustomer' else "🏪 نقطة بيع"
        text += f"{customer_type_arabic} **{full_name}**\n"
        text += f"📞 {phone}\n"
        
        if limit_active == 1:
            percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
            text += f"💳 الحد: {max_credit:,.0f} دينار ({percentage_used:.1f}%)\n"
        
        text += f"📅 تاريخ الإضافة: {created_at}\n"
        text += "────\n\n"
        
        markup.row(
            types.InlineKeyboardButton(f"👤 {full_name[:10]}", callback_data=f"view_credit_customer_{customer_id}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_credit_customer_{customer_id}")
        )
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return
    
    user_states[telegram_id]["full_name"] = full_name
    user_states[telegram_id]["step"] = "add_credit_customer_phone"
    
    bot.send_message(message.chat.id,
                    "📞 **رقم هاتف الزبون**\n\n"
                    "يرجى إدخال رقم هاتف الزبون (إجباري):")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_credit_customer_phone")
def process_credit_customer_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    phone = message.text.strip()
    
    if not phone or phone == '':
        bot.send_message(message.chat.id, "⚠️ **رقم الهاتف إجباري**\n\nيرجى إدخال رقم هاتف صحيح.")
        return
    
    user_states[telegram_id]["phone"] = phone
    user_states[telegram_id]["step"] = "add_credit_customer_type"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👤 زبون آجل (سعر المفرد)", callback_data="customer_type_CreditCustomer"))
    markup.add(types.InlineKeyboardButton("🏪 نقطة بيع (سعر الجملة)", callback_data="customer_type_PointOfSale"))
    
    bot.send_message(message.chat.id,
                    "📋 **نوع الزبون**\n\n"
                    "اختر نوع الزبون:\n\n"
                    "👤 **زبون آجل:** التعامل بسعر المفرد\n"
                    "🏪 **نقطة بيع:** التعامل بسعر الجملة\n"
                    "   - إذا الدفع آجل: يسجل في كشف الحساب\n"
                    "   - إذا الدفع نقدي: لا يسجل في كشف الحساب",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("customer_type_"))
def handle_customer_type(call):
    telegram_id = call.from_user.id
    state = user_states.get(telegram_id)
    
    if not state or state.get("step") != "add_credit_customer_type":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة")
        return
    
    customer_type = call.data.split("_")[2]  # CreditCustomer or PointOfSale
    
    seller_id = state["seller_id"]
    full_name = state["full_name"]
    phone = state["phone"]
    
    # الحصول على Telegram ID من المستخدم (إذا كان متاحاً)
    # في حالة إضافة زبون من البوت، يمكن إضافة حقل Telegram ID اختياري
    telegram_id = state.get("telegram_id")  # يمكن إضافته لاحقاً عند الحاجة
    
    customer_id = add_credit_customer(seller_id, full_name, phone, customer_type, telegram_id)
    
    if customer_id:
        customer_type_arabic = "زبون آجل" if customer_type == "CreditCustomer" else "نقطة بيع"
        bot.send_message(call.message.chat.id,
                        f"✅ **تم إضافة الزبون بنجاح!**\n\n"
                        f"👤 الاسم: {full_name}\n"
                        f"📞 الهاتف: {phone}\n"
                        f"📋 النوع: {customer_type_arabic}\n"
                        f"🆔 معرف الزبون: {customer_id}\n\n"
                        f"💡 **تلميح:** يمكنك تعيين حد ائتماني للزبون من خلال قائمة '💳 إدارة الحدود'")
    else:
        bot.send_message(call.message.chat.id,
                        "⚠️ **حدث خطأ**\n\n"
                        "تعذر إضافة الزبون. قد يكون رقم الهاتف مسجلاً مسبقاً.")
    
    del user_states[telegram_id]
    manage_credit_customers(call.message)
    bot.answer_callback_query(call.id)
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    # Handle both old and new schema
    if len(customer) >= 6:
        customer_id, seller_id, full_name, phone, customer_type, created_at = customer[:6]
    else:
        customer_id, seller_id, full_name, phone, created_at = customer
        customer_type = 'CreditCustomer'
    
    customer_type_arabic = "👤 زبون آجل" if customer_type == 'CreditCustomer' else "🏪 نقطة بيع"
    text = f"{customer_type_arabic} **معلومات الزبون**\n\n"
    text += f"🆔 معرف الزبون: {customer_id}\n"
    text += f"👤 الاسم: {full_name}\n"
    text += f"📞 الهاتف: {phone}\n"
    text += f"📋 النوع: {'زبون آجل (سعر المفرد)' if customer_type == 'CreditCustomer' else 'نقطة بيع (سعر الجملة)'}\n"
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_credit_customer_"))
def handle_edit_credit_customer(call):
    try:
        print(f"DEBUG: edit_credit_customer called with data: {call.data}")
        customer_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        customer = cursor.fetchone()
        conn.close()
        
        if not customer:
            bot.answer_callback_query(call.id, "الزبون غير موجود")
            return
        
        customer_id, seller_id, full_name, phone, created_at = customer
        
        text = f"✏️ **تعديل بيانات الزبون الآجل**\n\n"
        text += f"👤 **الاسم الحالي:** {full_name}\n"
        text += f"📞 **الهاتف الحالي:** {phone if phone else 'غير محدد'}\n\n"
        text += "اختر ما تريد تعديله:"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"edit_customer_name_{customer_id}"))
        markup.add(types.InlineKeyboardButton("📞 تعديل الهاتف", callback_data=f"edit_customer_phone_{customer_id}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"view_credit_customer_{customer_id}"))
        
        chat_id = call.message.chat.id if call.message else call.from_user.id
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_credit_customer: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء المعالجة")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_customer_name_"))
def handle_edit_customer_name(call):
    try:
        customer_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        user_states[telegram_id] = {
            "step": "edit_customer_name",
            "customer_id": customer_id,
            "seller_id": seller[0]
        }
        
        chat_id = call.message.chat.id if call.message else call.from_user.id
        bot.send_message(chat_id, "✏️ **تعديل اسم الزبون**\n\nيرجى إدخال الاسم الجديد:")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_customer_name: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_customer_phone_"))
def handle_edit_customer_phone(call):
    try:
        customer_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        user_states[telegram_id] = {
            "step": "edit_customer_phone",
            "customer_id": customer_id,
            "seller_id": seller[0]
        }
        
        chat_id = call.message.chat.id if call.message else call.from_user.id
        bot.send_message(chat_id, "📞 **تعديل رقم الهاتف**\n\nيرجى إدخال رقم الهاتف الجديد:\n(أو اكتب 'حذف' لحذف رقم الهاتف)")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_customer_phone: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_customer_name")
def process_edit_customer_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    new_name = message.text.strip()
    
    if not new_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return
    
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    success = update_credit_customer(customer_id, seller_id, full_name=new_name)
    
    if success:
        bot.send_message(message.chat.id, f"✅ **تم تحديث اسم الزبون بنجاح!**\n\n👤 الاسم الجديد: {new_name}")
    else:
        bot.send_message(message.chat.id, "⚠️ **حدث خطأ**\n\nتعذر تحديث اسم الزبون.")
    
    del user_states[telegram_id]
    
    # إعادة عرض تفاصيل الزبون
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    
    if customer:
        customer_id, seller_id, full_name, phone, created_at = customer
        text = f"👤 **معلومات الزبون الآجل**\n\n"
        text += f"🆔 معرف الزبون: {customer_id}\n"
        text += f"👤 الاسم: {full_name}\n"
        text += f"📞 الهاتف: {phone if phone else 'غير محدد'}\n"
        text += f"📅 تاريخ الإضافة: {created_at}\n\n"
        
        balance = get_customer_balance(customer_id, seller_id)
        text += f"💰 **الرصيد الحالي:** {balance} IQD\n"
        
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
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_customer_phone")
def process_edit_customer_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    new_phone = message.text.strip()
    
    if new_phone.lower() in ["حذف", "delete", "none", "null"]:
        new_phone = None
    elif not new_phone:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم هاتف صحيح أو اكتب 'حذف' لحذف رقم الهاتف.")
        return
    
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    success = update_credit_customer(customer_id, seller_id, phone_number=new_phone)
    
    if success:
        phone_display = new_phone if new_phone else "تم الحذف"
        bot.send_message(message.chat.id, f"✅ **تم تحديث رقم الهاتف بنجاح!**\n\n📞 رقم الهاتف الجديد: {phone_display}")
    else:
        bot.send_message(message.chat.id, "⚠️ **حدث خطأ**\n\nتعذر تحديث رقم الهاتف.")
    
    del user_states[telegram_id]
    
    # إعادة عرض تفاصيل الزبون
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    
    if customer:
        customer_id, seller_id, full_name, phone, created_at = customer
        text = f"👤 **معلومات الزبون الآجل**\n\n"
        text += f"🆔 معرف الزبون: {customer_id}\n"
        text += f"👤 الاسم: {full_name}\n"
        text += f"📞 الهاتف: {phone if phone else 'غير محدد'}\n"
        text += f"📅 تاريخ الإضافة: {created_at}\n\n"
        
        balance = get_customer_balance(customer_id, seller_id)
        text += f"💰 **الرصيد الحالي:** {balance} IQD\n"
        
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
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "delete_credit_customer_list")
def handle_delete_credit_customer_list(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_credit_customers(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن آجلين للحذف")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for customer in customers:
        customer_id, seller_id, full_name, phone, created_at, max_credit, current_used, limit_active = customer
        markup.add(types.InlineKeyboardButton(f"🗑️ {full_name}", callback_data=f"delete_credit_customer_{customer_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(call.message.chat.id, "🗑️ **اختر الزبون الذي تريد حذفه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_credit_customer_"))
def handle_delete_credit_customer(call):
    try:
        print(f"DEBUG: delete_credit_customer called with data: {call.data}")
        # استخراج customer_id من callback_data بشكل آمن
        parts = call.data.split("_")
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "❌ خطأ في البيانات")
            return
        
        customer_id = int(parts[-1])  # استخدام آخر جزء كـ customer_id
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        customer = cursor.fetchone()
        
        if not customer:
            bot.answer_callback_query(call.id, "الزبون غير موجود")
            conn.close()
            return
        
        customer_id, seller_id, full_name, phone, created_at = customer
        
        # التحقق من وجود رصيد
        balance = get_customer_balance(customer_id, seller_id)
        
        text = f"🗑️ **حذف زبون آجل**\n\n"
        text += f"👤 **الاسم:** {full_name}\n"
        text += f"📞 **الهاتف:** {phone if phone else 'غير محدد'}\n"
        text += f"💰 **الرصيد الحالي:** {balance} IQD\n\n"
        
        if balance != 0:
            text += f"⚠️ **تحذير:** هذا الزبون لديه رصيد بقيمة {balance} IQD.\n"
            text += f"سيتم حذف جميع المعاملات والحدود الائتمانية المرتبطة به.\n\n"
        
        text += "هل أنت متأكد من حذف هذا الزبون؟"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete_credit_customer_{customer_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"view_credit_customer_{customer_id}")
        )
        
        chat_id = call.message.chat.id if call.message else call.from_user.id
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        conn.close()
    except Exception as e:
        print(f"Error in handle_delete_credit_customer: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء المعالجة")
        if 'conn' in locals():
            conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_credit_customer_"))
def handle_confirm_delete_credit_customer(call):
    customer_id = int(call.data.split("_")[-1])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # الحصول على معلومات الزبون قبل الحذف
        cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        customer_info = cursor.fetchone()
        customer_name = customer_info[0] if customer_info else "الزبون"
        
        # حذف البيانات المرتبطة بالزبون
        cursor.execute("DELETE FROM CustomerCredit WHERE CustomerID=?", (customer_id,))
        cursor.execute("DELETE FROM CreditLimits WHERE CustomerID=?", (customer_id,))
        cursor.execute("DELETE FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        conn.commit()
        
        bot.answer_callback_query(call.id, "✅ تم حذف الزبون بنجاح")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"✅ **تم حذف الزبون الآجل بنجاح!**\n\n👤 الزبون: {customer_name}")
        
        # إعادة عرض قائمة الزبائن
        manage_credit_customers(call.message)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ أثناء الحذف")
        print(f"Delete Credit Customer Error: {e}")
    finally:
        conn.close()

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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
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

# ====== حذف الطلب وتحديث الكميات ======
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_order_"))
def handle_delete_order(call):
    try:
        order_id = int(call.data.split("_")[2])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get Order Items to restore quantity (subtract already returned items)
        if IS_POSTGRES:
            cursor.execute("SELECT ProductID, (Quantity - COALESCE(ReturnedQuantity, 0)) FROM OrderItems WHERE OrderID = %s", (order_id,))
        else:
            cursor.execute("SELECT ProductID, (Quantity - COALESCE(ReturnedQuantity, 0)) FROM OrderItems WHERE OrderID = ?", (order_id,))
            
        items = cursor.fetchall()
        
        # 2. Restore Quantities
        for item in items:
            pid, qty = item
            if IS_POSTGRES:
                cursor.execute("UPDATE Products SET Quantity = Quantity + %s WHERE ProductID = %s", (qty, pid))
            else:
                cursor.execute("UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?", (qty, pid))
                
        # 3. Delete Order (Cascades to OrderItems usually, but safe to delete items first if no cascade)
        # Assuming CASCADE or manual deletion. Let's delete items first to be safe.
        # 3. Delete Order (Delete children first to avoid FK constraints)
        if IS_POSTGRES:
            cursor.execute("DELETE FROM Messages WHERE OrderID = %s", (order_id,))
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = %s", (order_id,))
            # Check for Returns if any
            cursor.execute("DELETE FROM Returns WHERE OrderID = %s", (order_id,))
            cursor.execute("DELETE FROM Orders WHERE OrderID = %s", (order_id,))
            
        else:
            cursor.execute("DELETE FROM Messages WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Returns WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Orders WHERE OrderID = ?", (order_id,))
            
        # Capture rowcount before closing connection
        deleted_count = cursor.rowcount
            
        conn.commit()
        conn.close()
        
        # 4. Update View
        if deleted_count > 0:
            bot.answer_callback_query(call.id, "✅ تم حذف الطلب واعادة الكميات")
            bot.edit_message_text(
                f"🗑️ **تم حذف الطلب #{order_id}**\n\nتم إعادة الكميات للمخزن.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=None
            )
        else:
            bot.answer_callback_query(call.id, f"⚠️ لم يتم العثور على الطلب #{order_id}", show_alert=True)
            bot.edit_message_text(
                f"⚠️ **الطلب #{order_id} غير موجود**\n\nربما تم حذفه مسبقاً.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=None
            )
        
    except Exception as e:
        print(f"Error deleting order: {e}")
        bot.answer_callback_query(call.id, f"خطأ: {str(e)[:50]}", show_alert=True)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        # تخطي معالجات الزبائن الآجلين لأنها موجودة كمعالجات منفصلة
        if (call.data.startswith("edit_credit_customer_") or 
            call.data.startswith("edit_customer_name_") or 
            call.data.startswith("edit_customer_phone_") or
            call.data.startswith("delete_credit_customer_") or
            call.data.startswith("confirm_delete_credit_customer_") or
            call.data == "delete_credit_customer_list"):
            # هذه المعالجات موجودة كمعالجات منفصلة قبل هذا المعالج
            return
        
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
        elif call.data.startswith("manage_store_reg_"):
            handle_manage_store_registration(call)
        elif call.data.startswith("toggle_store_reg_"):
            handle_toggle_store_registration(call)
        elif call.data.startswith("viewcat_"):
            handle_view_category(call)
        elif call.data.startswith("select_images_"):
            handle_select_images(call)
        elif call.data.startswith("buy_images_"):
            handle_buy_images(call)
        elif call.data == "cancel_image_selection":
            handle_cancel_image_selection(call)
        elif call.data.startswith("manage_product_images_"):
            handle_manage_product_images(call)
        elif call.data.startswith("add_product_image_"):
            handle_add_product_image(call)
        elif call.data.startswith("delete_product_image_"):
            handle_delete_product_image(call)
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
        elif call.data.startswith("skip_seller_"):
             handle_skip_seller(call)
        elif call.data.startswith("payment_cash_"):
             handle_payment_cash(call)
        elif call.data in ["edit_name", "edit_phone"]:
            handle_edit_user_info(call)
        elif call.data.startswith("customer_type_"):
            handle_customer_type(call)
        # ملاحظة: معالجات delete_credit_customer_ و edit_credit_customer_ موجودة كمعالجات منفصلة قبل هذا المعالج
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
        
        safe_store_name = escape_markdown_v1(store_name)
        
        text += f"{status_icon} **المتجر:** {safe_store_name}\n"
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
        
        safe_store_name = escape_markdown_v1(store_name)
        safe_reason = escape_markdown_v1(reason)
        
        text += f"⏸️ **المتجر:** {safe_store_name}\n"
        text += f"👤 {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📋 السبب: {safe_reason}\n"
        text += f"👮 معلق بواسطة: {escape_markdown_v1(suspender_name)}\n"
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
def send_store_catalog_by_telegram_id(chat_id, seller_telegram_id, customer_telegram_id=None):
    """إرسال كتالوج المتجر - يتطلب تسجيل الزبون في CreditCustomers إذا كان الإعداد مفعلاً"""
    try:
        print(f"🔍 send_store_catalog_by_telegram_id: seller_telegram_id={seller_telegram_id}, customer_telegram_id={customer_telegram_id}")
        
        # Ensure customer exists in Users table (required for Foreign Key constraint in Carts)
        if customer_telegram_id:
            print(f"[DEBUG] send_store_catalog: Checking customer {customer_telegram_id}...")
            user = get_user(customer_telegram_id)
            if not user:
                print(f"[INFO] Customer {customer_telegram_id} not found in Users table. Creating user entry...")
                try:
                    user_created = add_user(customer_telegram_id, None, 'buyer', None, None)
                    if not user_created:
                        print(f"[ERROR] Failed to create user entry for customer {customer_telegram_id}")
                    else:
                        # Small delay to ensure database commit is complete
                        import time
                        time.sleep(0.2)
                        
                        # Verify user was created
                        user = get_user(customer_telegram_id)
                        if user:
                            print(f"[SUCCESS] Created and verified user entry for customer {customer_telegram_id}")
                        else:
                            print(f"[WARNING] User {customer_telegram_id} still not found after creation")
                except Exception as user_error:
                    print(f"[ERROR] Failed to create user entry: {user_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[OK] Customer {customer_telegram_id} exists in Users table")
        
        seller = get_seller_by_telegram(seller_telegram_id)
        print(f"✅ get_seller_by_telegram returned: {seller is not None}")
    except Exception as e:
        print(f"❌ Error in send_store_catalog_by_telegram_id: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, f"⚠️ حدث خطأ في فتح المتجر: {str(e)}")
        return
    
    if not seller or seller[5] != 'active':
        bot.send_message(chat_id, "⚠️ المتجر غير موجود أو معطل حالياً.")
        return
    
    seller_id = seller[0]
    store_name = seller[3]
    username = seller[2] or "بائع"
    is_admin_store = (seller[1] == BOT_ADMIN_ID)
    
    # التحقق من إعداد RequireCustomerRegistration (العمود 9 في جدول Sellers)
    # إذا كان الإعداد مفعلاً (1)، يجب التحقق من تسجيل الزبون
    require_registration = False
    if len(seller) > 9:
        require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
    
    # التحقق من أن المستخدم مسجل في CreditCustomers لهذا المتجر (فقط إذا كان الإعداد مفعلاً)
    # استثناء: صاحب المتجر نفسه يمكنه الدخول دائماً
    if require_registration and customer_telegram_id and customer_telegram_id != seller_telegram_id:
        # التحقق من Telegram ID مباشرة
        if not is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 التواصل مع البائع", url=f"https://t.me/{username}" if username else None))
            
            bot.send_message(chat_id,
                f"🔒 **الدخول مقيد**\n\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"⚠️ حسابك (Telegram ID: {customer_telegram_id}) غير مسجل في قائمة الزبائن الآجلين.\n\n"
                f"📝 **للحصول على الوصول:**\n"
                f"• تواصل مع البائع لإضافتك كزبون آجل\n"
                f"• أو اطلب من البائع إضافتك من خلال قائمة '🏪 إدارة الزبائن الآجلين'\n\n"
                f"بعد التسجيل، يمكنك الوصول إلى جميع منتجات المتجر.",
                reply_markup=markup if username else None,
                parse_mode='Markdown')
            return
    
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
                # للمتاجر المقفولة: عرض بدون صور مع زر خاص لاختيار الصور
                if require_registration:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📸 اختر الصور", callback_data=f"select_images_{pid}"))
                    
                    text = f"📦 **{name}**\n"
                    if desc:
                        text += f"📝 {desc[:100]}{'...' if len(desc) > 100 else ''}\n"
                    text += f"💰 السعر: {price:,.0f} د.ع للصورة الواحدة\n"
                    text += f"📊 الكمية المتاحة: {qty} صورة"
                    
                    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
                else:
                    # للمتاجر المفتوحة: العرض العادي مع الصور
                    markup = types.InlineKeyboardMarkup()
                    markup = create_product_markup_with_qty(pid, 1)
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
    
    # إضافة قائمة الأزرار للمشتري بعد عرض المتجر
    if customer_telegram_id and customer_telegram_id != seller_telegram_id:
        try:
            print(f"🔍 Showing buyer menu for customer: {customer_telegram_id}, chat_id: {chat_id}")
            # إرسال الأزرار مباشرة باستخدام chat_id و user_id
            show_buyer_main_menu(chat_id=chat_id, user_id=customer_telegram_id)
            print(f"✅ Buyer menu sent successfully")
        except Exception as e:
            print(f"❌ Error showing buyer menu: {e}")
            import traceback
            traceback.print_exc()

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
            try:
                telegram_id, username, store_name = seller
                
                # Sanitize store name
                if not store_name or not store_name.strip():
                    store_name = "متجر بدون اسم"
                
                # Replace replacement character if present
                store_name = store_name.replace('\ufffd', '?')
                
                label = f"🏪 {store_name} - {format_seller_mention(username, telegram_id)}"
                markup.add(types.InlineKeyboardButton(
                    label, 
                    callback_data=f"viewstore_{telegram_id}"
                ))
            except Exception as e:
                print(f"Skipping bad store: {e}")
                continue
        
        try:
            bot.send_message(message.chat.id, "🛍️ **المتاجر المتاحة:**", reply_markup=markup)
        except Exception as e:
            print(f"Error sending stores list: {e}")
            bot.send_message(message.chat.id, "حدث خطأ في عرض قائمة المتاجر.")
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
        customer_telegram_id = call.from_user.id
        send_store_catalog_by_telegram_id(call.message.chat.id, telegram_id, customer_telegram_id)
        bot.answer_callback_query(call.id)
    except:
        bot.answer_callback_query(call.id, "خطأ في عرض المتجر")

def handle_manage_store_registration(call):
    """إدارة إعداد قيد الدخول للمتجر"""
    try:
        seller_id = int(call.data.split("_")[3])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers WHERE SellerID=%s
            """, (seller_id,))
        else:
            cursor.execute("""
                SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers WHERE SellerID=?
            """, (seller_id,))
        
        store = cursor.fetchone()
        conn.close()
        
        if not store:
            bot.answer_callback_query(call.id, "⚠️ المتجر غير موجود")
            return
        
        store_name = store[1]
        current_setting = store[2] if len(store) > 2 else 0
        
        text = f"🔐 **إدارة قيد الدخول للمتجر**\n\n"
        text += f"🏪 **المتجر:** {store_name}\n\n"
        text += f"**الحالة الحالية:**\n"
        if current_setting == 1:
            text += f"🔒 **مفعل** - المتجر مفتوح فقط للزبائن المسجلين في CreditCustomers\n\n"
            text += f"⚠️ **ملاحظة:** الزبائن غير المسجلين لن يتمكنوا من الوصول للمتجر."
        else:
            text += f"🔓 **معطل** - المتجر مفتوح للجميع\n\n"
            text += f"✅ **ملاحظة:** أي شخص يمكنه الوصول للمتجر بدون تسجيل."
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        if current_setting == 1:
            markup.add(types.InlineKeyboardButton("🔓 إلغاء قيد الدخول (فتح للجميع)", callback_data=f"toggle_store_reg_{seller_id}_0"))
        else:
            markup.add(types.InlineKeyboardButton("🔒 تفعيل قيد الدخول (الزبائن المسجلين فقط)", callback_data=f"toggle_store_reg_{seller_id}_1"))
        markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_stores_list"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_manage_store_registration: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

def handle_toggle_store_registration(call):
    """تفعيل/إلغاء قيد الدخول للمتجر"""
    try:
        parts = call.data.split("_")
        seller_id = int(parts[3])
        new_value = int(parts[4])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                UPDATE Sellers 
                SET RequireCustomerRegistration = %s 
                WHERE SellerID = %s
            """, (new_value, seller_id))
        else:
            cursor.execute("""
                UPDATE Sellers 
                SET RequireCustomerRegistration = ? 
                WHERE SellerID = ?
            """, (new_value, seller_id))
        
        conn.commit()
        
        # الحصول على اسم المتجر
        if IS_POSTGRES:
            cursor.execute("SELECT StoreName FROM Sellers WHERE SellerID=%s", (seller_id,))
        else:
            cursor.execute("SELECT StoreName FROM Sellers WHERE SellerID=?", (seller_id,))
        
        store_result = cursor.fetchone()
        store_name = store_result[0] if store_result else "المتجر"
        conn.close()
        
        status_text = "تم تفعيل قيد الدخول" if new_value == 1 else "تم إلغاء قيد الدخول"
        icon = "🔒" if new_value == 1 else "🔓"
        
        bot.answer_callback_query(call.id, f"✅ {status_text}")
        bot.send_message(call.message.chat.id, 
            f"{icon} **{status_text}**\n\n"
            f"🏪 المتجر: {store_name}\n\n"
            f"{'المتجر الآن مفتوح فقط للزبائن المسجلين في CreditCustomers' if new_value == 1 else 'المتجر الآن مفتوح للجميع'}",
            parse_mode='Markdown')
        
        # تحديث الرسالة السابقة
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
    except Exception as e:
        print(f"Error in handle_toggle_store_registration: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_stores_list")
def handle_back_to_stores_list(call):
    """العودة لقائمة المتاجر"""
    if is_bot_admin(call.from_user.id):
        # إعادة عرض قائمة المتاجر
        message = call.message
        message.text = "📋 قائمة المتاجر"
        list_stores(message)
        bot.answer_callback_query(call.id)

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
        
        # التحقق من إعداد RequireCustomerRegistration
        require_registration = False
        if len(seller) > 9:
            require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
        
        text = f"📁 **قسم: {category[2]}**\n🏪 {seller_name}\n\n🛍️ المنتجات المتاحة:\n\n"
        
        for product in products:
            pid, name, desc, price, wholesale_price, qty, img_path = product
            if qty > 0:
                # للمتاجر المقفولة: عرض بدون صور مع زر خاص لاختيار الصور
                if require_registration:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📸 اختر الصور", callback_data=f"select_images_{pid}"))
                    
                    product_text = f"📦 **{name}**\n"
                    if desc:
                        product_text += f"📝 {desc[:100]}{'...' if len(desc) > 100 else ''}\n"
                    product_text += f"💰 السعر: {price:,.0f} د.ع للصورة الواحدة\n"
                    product_text += f"📊 الكمية المتاحة: {qty} صورة"
                    
                    bot.send_message(call.message.chat.id, product_text, reply_markup=markup, parse_mode='Markdown')
                else:
                    # للمتاجر المفتوحة: العرض العادي مع الصور
                    markup = types.InlineKeyboardMarkup()
                    markup = create_product_markup_with_qty(pid, 1)
                    send_product_with_image(call.message.chat.id, product, markup, seller_name)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_view_category: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ")

def handle_select_images(call):
    """معالج اختيار عدد الصور للمنتج"""
    try:
        product_id = int(call.data.split("_")[2])
        product = get_product_by_id(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        seller_id = product[1]
        product_name = product[3]
        price = product[5]
        available_qty = product[7]
        
        # الحصول على صور المنتج
        images = get_product_images(product_id)
        
        if not images:
            bot.answer_callback_query(call.id, "⚠️ لا توجد صور متاحة لهذا المنتج")
            return
        
        # التحقق من رقم الهاتف المسجل
        telegram_id = call.from_user.id
        user_phone = None
        if telegram_id in user_states:
            state = user_states[telegram_id]
            if 'verified_phone' in state and 'verified_seller_id' in state:
                if state['verified_seller_id'] == seller_id:
                    user_phone = state['verified_phone']
        
        if not user_phone:
            bot.answer_callback_query(call.id, "⚠️ يجب التحقق من رقم الهاتف أولاً")
            return
        
        # الحصول على معلومات الزبون
        customer = get_customer_by_phone_for_seller(user_phone, seller_id)
        if not customer:
            bot.answer_callback_query(call.id, "⚠️ أنت غير مسجل كزبون آجل")
            return
        
        customer_id, customer_name, customer_phone = customer
        
        # عرض عدد الصور المتاحة واختيار العدد
        text = f"📸 **اختر عدد الصور**\n\n"
        text += f"📦 المنتج: {product_name}\n"
        text += f"💰 السعر: {price:,.0f} د.ع للصورة الواحدة\n"
        text += f"📊 الصور المتاحة: {len(images)} صورة\n"
        text += f"📦 الكمية المتاحة: {available_qty} صورة\n\n"
        text += f"👤 الزبون: {customer_name}\n"
        text += f"📱 الهاتف: {customer_phone}\n\n"
        text += f"اختر عدد الصور التي تريد شراءها:"
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        # أزرار الكمية (1-10)
        qty_buttons = []
        max_qty = min(available_qty, len(images), 10)
        for i in range(1, max_qty + 1):
            qty_buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"buy_images_{product_id}_{i}"))
            if len(qty_buttons) == 3:
                markup.row(*qty_buttons)
                qty_buttons = []
        
        if qty_buttons:
            markup.row(*qty_buttons)
        
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_image_selection"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_select_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

def handle_buy_images(call):
    """معالج شراء الصور وإرسالها للمستخدم"""
    try:
        parts = call.data.split("_")
        product_id = int(parts[2])
        quantity = int(parts[3])
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        seller_id = product[1]
        product_name = product[3]
        price = product[5]
        available_qty = product[7]
        
        if quantity > available_qty:
            bot.answer_callback_query(call.id, f"⚠️ الكمية المتاحة فقط {available_qty} صورة")
            return
        
        # الحصول على صور المنتج
        images = get_product_images(product_id)
        if not images or len(images) < quantity:
            bot.answer_callback_query(call.id, "⚠️ لا توجد صور كافية")
            return
        
        # التحقق من رقم الهاتف المسجل
        telegram_id = call.from_user.id
        user_phone = None
        if telegram_id in user_states:
            state = user_states[telegram_id]
            if 'verified_phone' in state and 'verified_seller_id' in state:
                if state['verified_seller_id'] == seller_id:
                    user_phone = state['verified_phone']
        
        if not user_phone:
            bot.answer_callback_query(call.id, "⚠️ يجب التحقق من رقم الهاتف أولاً")
            return
        
        # الحصول على معلومات الزبون
        customer = get_customer_by_phone_for_seller(user_phone, seller_id)
        if not customer:
            bot.answer_callback_query(call.id, "⚠️ أنت غير مسجل كزبون آجل")
            return
        
        customer_id, customer_name, customer_phone = customer
        
        # حساب المبلغ الإجمالي
        total_amount = price * quantity
        
        # إرسال الصور للمستخدم
        sent_images = []
        for i in range(quantity):
            image_path = images[i][1]  # ImagePath
            
            # محاولة إرسال الصورة
            try:
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(telegram_id, photo)
                        sent_images.append(image_path)
                elif IS_POSTGRES:
                    # محاولة تحميل من السحابة
                    base_name = os.path.basename(image_path)
                    if download_image_from_cloud(base_name):
                        alt_path = os.path.join(IMAGES_FOLDER, base_name)
                        if os.path.exists(alt_path):
                            with open(alt_path, 'rb') as photo:
                                bot.send_photo(telegram_id, photo)
                                sent_images.append(base_name)
            except Exception as e:
                print(f"Error sending image {i+1}: {e}")
        
        if not sent_images:
            bot.answer_callback_query(call.id, "❌ فشل إرسال الصور")
            return
        
        # إضافة المبلغ لحساب الزبون
        description = f"شراء {quantity} صورة من منتج: {product_name}"
        if add_credit_transaction(customer_id, seller_id, total_amount, description):
            # تحديث كمية المنتج (تأكد من عدم السالب)
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("UPDATE Products SET Quantity = GREATEST(0, Quantity - %s) WHERE ProductID = %s", (quantity, product_id))
            else:
                cursor.execute("UPDATE Products SET Quantity = MAX(0, Quantity - ?) WHERE ProductID = ?", (quantity, product_id))
            conn.commit()
            conn.close()
            
            # إرسال رسالة للمستخدم
            bot.send_message(telegram_id,
                f"✅ **تم الشراء بنجاح!**\n\n"
                f"📦 المنتج: {product_name}\n"
                f"📸 عدد الصور: {quantity}\n"
                f"💰 المبلغ: {total_amount:,.0f} د.ع\n\n"
                f"تم إضافة المبلغ إلى حسابك الآجل.",
                parse_mode='Markdown')
            
            # إرسال إشعار للبائع
            seller = get_seller_by_id(seller_id)
            if seller:
                seller_telegram_id = seller[1]
                images_list = "\n".join([f"• {os.path.basename(img)}" for img in sent_images])
                
                bot.send_message(seller_telegram_id,
                    f"🛒 **طلب شراء صور**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"📱 الهاتف: {customer_phone}\n\n"
                    f"📦 المنتج: {product_name}\n"
                    f"📸 عدد الصور: {quantity}\n"
                    f"💰 المبلغ: {total_amount:,.0f} د.ع\n\n"
                    f"📸 الصور المشتراة:\n{images_list}\n\n"
                    f"✅ تم إضافة المبلغ {total_amount:,.0f} د.ع إلى حساب الزبون.",
                    parse_mode='Markdown')
            
            bot.answer_callback_query(call.id, f"✅ تم إرسال {len(sent_images)} صورة")
        else:
            bot.answer_callback_query(call.id, "❌ فشل إضافة المبلغ للحساب")
    except Exception as e:
        print(f"Error in handle_buy_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_image_selection")
def handle_cancel_image_selection(call):
    """إلغاء اختيار الصور"""
    bot.answer_callback_query(call.id, "تم الإلغاء")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def add_product_image_db(product_id, image_path, image_order=0):
    """إضافة صورة للمنتج في قاعدة البيانات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
                VALUES (%s, %s, %s)
                RETURNING ImageID
            """, (product_id, image_path, image_order))
            result = cursor.fetchone()
            image_id = result[0] if result else None
        else:
            cursor.execute("""
                INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
                VALUES (?, ?, ?)
            """, (product_id, image_path, image_order))
            image_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return image_id
    except Exception as e:
        print(f"Error adding product image: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return None

def delete_product_image_db(image_id):
    """حذف صورة من المنتج"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("DELETE FROM ProductImages WHERE ImageID=%s", (image_id,))
        else:
            cursor.execute("DELETE FROM ProductImages WHERE ImageID=?", (image_id,))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    except Exception as e:
        print(f"Error deleting product image: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def handle_manage_product_images(call):
    """إدارة صور المنتج"""
    try:
        product_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        # التحقق من أن البائع يملك المنتج
        seller = get_seller_by_telegram(telegram_id)
        if not seller or product[1] != seller[0]:
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لتعديل هذا المنتج")
            return
        
        product_name = product[3]
        images = get_product_images(product_id)
        
        text = f"🖼️ **إدارة صور المنتج**\n\n"
        text += f"📦 المنتج: {product_name}\n"
        text += f"📸 عدد الصور الحالية: {len(images)}\n\n"
        
        if images:
            text += "**الصور الحالية:**\n"
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            for img_id, img_path, img_order in images:
                img_name = os.path.basename(img_path)
                text += f"• {img_name}\n"
                markup.add(types.InlineKeyboardButton(f"🗑️ {img_name[:15]}", callback_data=f"delete_product_image_{img_id}"))
            
            markup.add(types.InlineKeyboardButton("➕ إضافة صورة جديدة", callback_data=f"add_product_image_{product_id}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"edit_product_{product_id}"))
        else:
            text += "لا توجد صور حالياً.\n"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("➕ إضافة صورة جديدة", callback_data=f"add_product_image_{product_id}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"edit_product_{product_id}"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_manage_product_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

def handle_add_product_image(call):
    """بدء عملية إضافة صورة جديدة للمنتج"""
    try:
        product_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        # التحقق من أن البائع يملك المنتج
        seller = get_seller_by_telegram(telegram_id)
        if not seller or product[1] != seller[0]:
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لتعديل هذا المنتج")
            return
        
        # حفظ الحالة
        user_states[telegram_id] = {
            'step': 'add_product_image_to_db',
            'product_id': product_id
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("📸 إرسال صورة", "❌ إلغاء")
        
        bot.send_message(call.message.chat.id,
            f"📸 **إضافة صورة جديدة**\n\n"
            f"📦 المنتج: {product[3]}\n\n"
            f"يرجى إرسال الصورة التي تريد إضافتها للمنتج:",
            reply_markup=markup,
            parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_add_product_image: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "add_product_image_to_db")
def handle_save_product_image(message):
    """حفظ الصورة الجديدة للمنتج"""
    try:
        telegram_id = message.from_user.id
        state = user_states[telegram_id]
        product_id = state['product_id']
        
        # حفظ الصورة
        image_path = save_photo_from_message(message)
        if not image_path:
            bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الصورة")
            del user_states[telegram_id]
            return
        
        # إضافة الصورة لقاعدة البيانات
        images = get_product_images(product_id)
        image_order = len(images)  # ترتيب الصورة الجديدة
        
        image_id = add_product_image_db(product_id, image_path, image_order)
        
        if image_id:
            # تحديث كمية المنتج تلقائياً إذا كان المتجر مقفول
            product = get_product_by_id(product_id)
            if product:
                seller_id = product[1]
                seller = get_seller_by_id(seller_id)
                require_registration = False
                if seller and len(seller) > 9:
                    require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
                
                if require_registration:
                    # حساب عدد الصور بعد إضافة الصورة الجديدة وتحديث الكمية
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    if IS_POSTGRES:
                        cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=%s", (product_id,))
                    else:
                        cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=?", (product_id,))
                    result = cursor.fetchone()
                    image_count = result[0] if result else 0
                    
                    print(f"📊 تم إضافة صورة جديدة. عدد الصور الآن: {image_count}")
                    
                    # تحديث الكمية
                    if IS_POSTGRES:
                        cursor.execute("UPDATE Products SET Quantity=%s WHERE ProductID=%s", (image_count, product_id))
                    else:
                        cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (image_count, product_id))
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ تم تحديث الكمية إلى: {image_count}")
            
            bot.send_message(message.chat.id,
                f"✅ **تم إضافة الصورة بنجاح!**\n\n"
                f"📸 تم حفظ الصورة: {os.path.basename(image_path)}\n\n"
                f"يمكنك إضافة المزيد من الصور أو العودة لإدارة المنتج.",
                parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ في إضافة الصورة لقاعدة البيانات")
        
        # إزالة الحالة
        del user_states[telegram_id]
        
        # إعادة عرض قائمة إدارة الصور
        call_data = f"manage_product_images_{product_id}"
        fake_call = type('obj', (object,), {
            'data': call_data,
            'from_user': message.from_user,
            'message': message
        })()
        handle_manage_product_images(fake_call)
    except Exception as e:
        print(f"Error in handle_save_product_image: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الصورة")
        if telegram_id in user_states:
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "add_product_image_to_db" and
                     message.text == "❌ إلغاء")
def handle_cancel_add_image(message):
    """إلغاء إضافة صورة"""
    telegram_id = message.from_user.id
    if telegram_id in user_states:
        state = user_states[telegram_id]
        product_id = state.get('product_id')
        del user_states[telegram_id]
        
        if product_id:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("🏠 الرئيسية")
            bot.send_message(message.chat.id, "❌ تم إلغاء العملية", reply_markup=markup)

def handle_delete_product_image(call):
    """حذف صورة من المنتج"""
    try:
        image_id = int(call.data.split("_")[3])
        
        # الحصول على معلومات الصورة
        conn = get_db_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                SELECT pi.ImageID, pi.ProductID, pi.ImagePath, p.SellerID, p.Name
                FROM ProductImages pi
                JOIN Products p ON pi.ProductID = p.ProductID
                WHERE pi.ImageID = %s
            """, (image_id,))
        else:
            cursor.execute("""
                SELECT pi.ImageID, pi.ProductID, pi.ImagePath, p.SellerID, p.Name
                FROM ProductImages pi
                JOIN Products p ON pi.ProductID = p.ProductID
                WHERE pi.ImageID = ?
            """, (image_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.answer_callback_query(call.id, "⚠️ الصورة غير موجودة")
            return
        
        img_id, product_id, img_path, seller_id, product_name = result
        
        # التحقق من أن البائع يملك المنتج
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        if not seller or seller[0] != seller_id:
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لحذف هذه الصورة")
            return
        
        # حذف الصورة
        if delete_product_image_db(image_id):
            # تحديث كمية المنتج تلقائياً إذا كان المتجر مقفول
            seller = get_seller_by_id(seller_id)
            require_registration = False
            if seller and len(seller) > 9:
                require_registration = seller[9] == 1 if not IS_POSTGRES else (seller[9] if seller[9] is not None else False)
            
            if require_registration:
                # حساب عدد الصور المتبقية وتحديث الكمية
                conn = get_db_connection()
                cursor = conn.cursor()
                if IS_POSTGRES:
                    cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=%s", (product_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM ProductImages WHERE ProductID=?", (product_id,))
                image_count = cursor.fetchone()[0] or 0
                
                # تحديث الكمية
                if IS_POSTGRES:
                    cursor.execute("UPDATE Products SET Quantity=%s WHERE ProductID=%s", (image_count, product_id))
                else:
                    cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (image_count, product_id))
                conn.commit()
                conn.close()
            
            bot.answer_callback_query(call.id, "✅ تم حذف الصورة")
            
            # إعادة عرض قائمة إدارة الصور
            call_data = f"manage_product_images_{product_id}"
            fake_call = type('obj', (object,), {
                'data': call_data,
                'from_user': call.from_user,
                'message': call.message
            })()
            handle_manage_product_images(fake_call)
        else:
            bot.answer_callback_query(call.id, "❌ فشل حذف الصورة")
    except Exception as e:
        print(f"Error in handle_delete_product_image: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("addtocart_"))
def handle_add_to_cart(call):
    try:
        parts = call.data.split("_")
        product_id = int(parts[1])
        
        # New: Parse quantity if present, default to 1
        quantity = 1
        if len(parts) > 2:
            try:
                quantity = int(parts[2])
            except:
                pass
        
        user_id = call.from_user.id
        
        # ====== التعديل: إزالة شرط التحقق من نوع المستخدم ======
        # يمكن لأي مستخدم (زائر، مشتري، بائع، أدمن) إضافة منتجات للسلة
        
        # Ensure user exists in Users table (required for Foreign Key constraint)
        print(f"[DEBUG] handle_add_to_cart: Checking user {user_id}...")
        user = get_user(user_id)
        if not user:
            # Create user entry if doesn't exist
            print(f"[INFO] User {user_id} not found. Creating user entry...")
            username = call.from_user.username or None
            full_name = None
            if call.from_user.first_name or call.from_user.last_name:
                full_name = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
            
            user_created = add_user(user_id, username, 'buyer', None, full_name)
            if not user_created:
                print(f"[ERROR] Failed to create user {user_id}")
                bot.answer_callback_query(call.id, "❌ حدث خطأ في إنشاء المستخدم")
                return
            
            # Small delay to ensure database commit is complete
            import time
            time.sleep(0.2)
            
            # Verify user was created
            user = get_user(user_id)
            if not user:
                print(f"[ERROR] User {user_id} still not found after creation")
                bot.answer_callback_query(call.id, "❌ حدث خطأ في التحقق من المستخدم")
                return
            print(f"[SUCCESS] User {user_id} created and verified")
        else:
            print(f"[OK] User {user_id} exists")
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return

        # منع الشراء من متجر الأدمن - REMOVED
        seller_id = product[1]
        # seller = get_seller_by_id(seller_id)
        # Check removed to allow buying from admin
        
        if product[7] <= 0:
            bot.answer_callback_query(call.id, "⛔ المنتج غير متوفر حالياً")
            return
        
        # الحصول على سعر المنتج المناسب للزبون
        seller_id = product[1]
        phone = None
        full_name = None
        
        # فقط للمستخدمين المسجلين، نحاول الحصول على معلوماتهم
        if user:
            phone = user[4] if len(user) > 4 else None
            full_name = user[5] if len(user) > 5 else None
        
        price = get_product_price_for_customer(product_id, seller_id, phone, full_name)
        
        success = add_to_cart_db(user_id, product_id, quantity, price)
        
        if success:
            product_name = product[3]
            bot.answer_callback_query(call.id, f"✅ تم إضافة {quantity}x {product_name} إلى السلة")
        else:
            bot.answer_callback_query(call.id, "❌ حدث خطأ في إضافة المنتج للسلة")
        
    except Exception as e:
        print(f"Error in handle_add_to_cart: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"خطأ: {str(e)[:50]}")

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
        
        # Build Consolidated Cart View
        markup = types.InlineKeyboardMarkup(row_width=4)
        cart_text = "🛒 **سلة المشتريات**\n\n"
        
        total = 0
        idx = 1
        
        # Group by seller for display structure (optional, but good for organization)
        # For the consolidated list, we can just list them sequentially but maybe group headers if needed.
        # Let's simple list them as requested: Image(No) Name Price Qty Total Controls
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            item_total = price * quantity
            total += item_total
            
            # Text Line
            # 1. Product Name (xQty) - Total
            cart_text += f"{idx}. **{name}**\n"
            cart_text += f"   💰 {price:,.0f} x {quantity} = {item_total:,.0f} IQD\n"
            cart_text += f"   🏪 {seller_name}\n"
            cart_text += "   ------------------------\n"
            
            # Control Row for this item
            # [ ➖ ] [ Qty ] [ ➕ ] [ 🗑️ ]
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton(f"{quantity}", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"remove_cart_{product_id}")
            )
            idx += 1
            
        cart_text += f"\n📊 **الإجمالي الكلي: {total:,.0f} IQD**\n"
        
        # Footer Actions
        markup.row(
            types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"),
            types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data="checkout_cart")
        )
        markup.row(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
        
        bot.send_message(message.chat.id, cart_text, reply_markup=markup, parse_mode='Markdown')     

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض السلة:\n{str(e)}")
        traceback.print_exc()

def update_cart_view(chat_id, message_id, user_id):
    """Updates the existing cart message with new state"""
    try:
        cart_items = get_cart_items_db(user_id)
        
        if not cart_items:
            # Cart is empty, edit message to say empty
            bot.edit_message_text("🛒 **سلة المشتريات**\n\nالسلة فارغة حالياً.", chat_id, message_id, parse_mode='Markdown', reply_markup=None)
            return

        markup = types.InlineKeyboardMarkup(row_width=4)
        cart_text = "🛒 **سلة المشتريات**\n\n"
        
        total = 0
        idx = 1
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            item_total = price * quantity
            total += item_total
            
            cart_text += f"{idx}. **{name}**\n"
            cart_text += f"   💰 {price:,.0f} x {quantity} = {item_total:,.0f} IQD\n"
            cart_text += f"   🏪 {seller_name}\n"
            cart_text += "   ------------------------\n"
            
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton(f"{quantity}", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"remove_cart_{product_id}")
            )
            idx += 1
            
        cart_text += f"\n📊 **الإجمالي الكلي: {total:,.0f} IQD**\n"
        
        markup.row(
            types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"),
            types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data="checkout_cart")
        )
        markup.row(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
        
        bot.edit_message_text(cart_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error updating cart view: {e}")
        # If edit fails (e.g. same content), ignore


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

        # Admin store filtering removed to allow purchases
        cleaned_cart = cart_items
        # removed_any = False logic removed

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
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📤 إرسال الطلب", callback_data=f"payment_cash_{seller_id}"))
        markup.add(types.InlineKeyboardButton("❌ إلغاء الطلب من هذا المتجر", callback_data=f"skip_seller_{seller_id}"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        return
    
    # للمستخدمين المسجلين
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
            # The 'status' line was removed as per the instruction's implied removal of check_credit_limit output
        
        if customer_balance > 0:
            text += f"💰 المبلغ المتبقي بعد خصم الرصيد: {max(0, subtotal - customer_balance)} IQD\n"
    
    
    # FORCED SINGLE BUTTON LAYOUT
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📤 إرسال الطلب", callback_data=f"payment_cash_{seller_id}"))
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
            # User requested one button flow. Let's redirect to "Full Cash" logic automatically or show choice?
            # Request was "There appear two buttons... make it one".
            # If I show choice here, it's 2 buttons again.
            # Let's skip this for now to ensure "One Button" feel, or maybe just proceed as Standard Order.
            # If we skip, we treat it as Cash/Standard.
            pass
            
            # markup = types.InlineKeyboardMarkup(row_width=2)
            # markup.add(
            #     types.InlineKeyboardButton("💵 دفع نقداً كاملاً", callback_data=f"payment_full_cash_{seller_id}"),
            #     types.InlineKeyboardButton("💳 دفع من الرصيد الآجل", callback_data=f"payment_from_balance_{seller_id}")
            # )
            
            # bot.send_message(call.message.chat.id,
            #                 f"💰 **لديك رصيد آجل**\n\n"
            #                 f"رصيدك الآجل: {customer_balance} IQD\n"
            #                 f"قيمة الطلب: {subtotal} IQD\n\n"
            #                 f"اختر طريقة الدفع:",
            #                 reply_markup=markup)
            # bot.answer_callback_query(call.id)
            # return
    
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
    query = """
        INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (temp_user_id, seller_id, total, delivery_address, f"زائر: {guest_name} - {guest_phone}", payment_method, fully_paid)
    
    if IS_POSTGRES:
        query += " RETURNING OrderID"
    
    cursor.execute(query, params)
    order_id = cursor.lastrowid
    
    # 🛡️ Safe Fallback for Postgres
    if IS_POSTGRES and not order_id:
        try:
            res = cursor.fetchone()
            if res:
                order_id = res[0]
                print(f"DEBUG: Retrieved Guest OrderID via fallback fetchone")
        except Exception as e:
            print(f"DEBUG: Error in guest fallback fetchone: {e}")

    # Optimize: Fetch product data using valid transaction cursor to avoid locking/visibility issues
    # Pre-fetch check or inline check
    for pid, qty, price in cart_items:
        # Inline lookup using SAME cursor
        cursor.execute("SELECT Quantity FROM Products WHERE ProductID = ?", (pid,))
        res = cursor.fetchone()
        
        if not res:
            print(f"⚠️ Warning: Product {pid} not found during Guest Order {order_id} creation. Skipping Item.")
            continue
            
        current_qty_in_db = res[0]
        
        cursor.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                       (order_id, pid, qty, price))
                       
        new_qty = current_qty_in_db - qty
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
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    cart_items = get_cart_items_db(telegram_id)
    current_qty = 0
    
    for item in cart_items:
        if item[0] == product_id:
            current_qty = item[1]
            break
    
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "المنتج غير موجود")
        return
    
    available_qty = product[7]
    
    if current_qty >= available_qty:
        bot.answer_callback_query(call.id, f"⚠️ الحد الأقصى للكمية المتاحة: {available_qty}")
        return
    
    update_cart_quantity_db(telegram_id, product_id, current_qty + 1)
    
    # Update View
    update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("decrease_cart_"))
def handle_decrease_cart(call):
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    cart_items = get_cart_items_db(telegram_id)
    current_qty = 0
    for item in cart_items:
        if item[0] == product_id:
            current_qty = item[1]
            break
            
    if current_qty > 1:
        update_cart_quantity_db(telegram_id, product_id, current_qty - 1)
        update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, "الحد الأدنى هو 1. للحذف استخدم زر الحذف.")

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
        
        update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
        bot.answer_callback_query(call.id, "تم حذف المنتج")
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
# ====== نظام الرسائل ======
@bot.message_handler(func=lambda message: "الرسائل" in message.text)
def seller_messages(message):
    print(f"📩 DEBUG: Message handler triggered for '{message.text}' by {message.from_user.id}")
    try:
        telegram_id = message.from_user.id
        from utils.receipt_generator import generate_order_card # Late import to avoid circular issues
        
        # Double check it is a seller
        if not is_seller(telegram_id):
            print(f"⛔ User {telegram_id} is NOT a seller.")
            return

        if not is_seller_active(telegram_id):
            bot.send_message(message.chat.id,
                            "⛔ **حسابك معطل**\n\n"
                            "لا يمكنك الوصول إلى الرسائل لأن حسابك معطل.")
            return

        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        # جلب الطلبات الحديثة (بدلاً من الرسائل)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب آخر 10 طلبات (المعلقة أولاً)
        query = """
            SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
                   COALESCE(u.FullName, 'زائر') as BuyerName,
                   COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
                   o.PaymentMethod, o.DeliveryAddress
            FROM Orders o
            LEFT JOIN Users u ON o.BuyerID = u.TelegramID
            WHERE o.SellerID = ? 
            ORDER BY 
                CASE WHEN o.Status = 'Pending' THEN 0 ELSE 1 END,
                o.CreatedAt DESC
            LIMIT 10
        """
        cursor.execute(query, (seller[0],))
        orders = cursor.fetchall()
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد طلبات أو رسائل.")
            conn.close()
            return

        bot.send_message(message.chat.id, "📩 **الطلبات والرسائل (Inbox)**")

        for order in orders:
            oid, total, status, date, buyer, phone, pay_method, address = order

            # --- NEW CARD LOGIC ---
            from utils.receipt_generator import generate_order_card
            try:
                # Use standard function (Safe with LEFT JOIN)
                order_details_full, items_full = get_order_details(oid)

                receipt_img = None
                try:
                    receipt_img = generate_order_card(order_details_full, items_full, buyer, phone, seller[3])
                    if receipt_img:
                        receipt_img.name = f"receipt_{oid}.png"
                except Exception as e:
                    print(f"Img Gen Error {oid}: {e}")

                clean_date = str(date).split('.')[0]
                caption = f"📦 طلب #{oid} | 💰 {total:,.0f} IQD\n📅 {clean_date}"

                if receipt_img:
                    try:
                        bot.send_photo(message.chat.id, receipt_img, caption=caption, parse_mode='Markdown')
                    except Exception as e:
                        bot.send_message(message.chat.id, caption + "\n⚠️ (Img Send Error)", parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, caption + "\n⚠️ (Img Gen Failed)", parse_mode='Markdown')

            except Exception as e:
                print(f"Error handling order {oid}: {e}")
                # Fallback
                clean_date = str(date).split('.')[0]
                bot.send_message(message.chat.id, f"📦 طلب #{oid}\n💰 {total:,.0f}\n📅 {clean_date}", parse_mode='Markdown')
            
            # Avoid hitting Telegram rate limits (approx 30 msgs/sec, but good to be safe with photos)
            time.sleep(0.3)
            continue # Skip legacy text logic below
            # --- END NEW LOGIC ---
            
            # جلب المنتجات للعرض (نستخدم LEFT JOIN لضمان ظهور العناصر حتى لو حذف المنتج الأصلي)
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق قائمة المنتجات
            items_text = ""
            first_image_path = None
            
            if not items:
                items_text = "" # User requested to remove warning
            else:
                for i in items:
                    p_name = i[0] if i[0] else "منتج محذوف"
                    p_qty = i[1]
                    p_price = i[2] if i[2] else 0
                    p_image = i[3]
                    
                    # Capture first image found to use as card cover
                    if not first_image_path and p_image and os.path.exists(p_image):
                         first_image_path = p_image
                    
                    row_total = p_qty * p_price
                    items_text += f"▫️ {p_name}\n   {p_qty}x | 💰 {p_price:,.0f} = {row_total:,.0f}\n"

            status_icon = "⏳" if status == 'Pending' else "✅" if status == 'Confirmed' else "🚚" if status == 'Shipped' else "❌" if status == 'Rejected' else ""
            status_text = "قيد الانتظار" if status == 'Pending' else "تم التأكيد" if status == 'Confirmed' else "تم الشحن" if status == 'Shipped' else "مرفوض" if status == 'Rejected' else status

            # تنسيق البطاقة
            card_text = f"{status_icon} طلب رقم #{oid}\n"
            card_text += f"📅 {date}\n\n"
            
            # المنتجات
            if items_text:
                card_text += f"{items_text}\n"
            
            # الإجمالي
            card_text += f"💰 **الإجمالي: {total:,.0f} IQD**\n"
            
            # معلومات العميل

            
            # معلومات العميل
            card_text += f"👤 {buyer}\n📞 {phone}\n"
            if address:
                card_text += f"📍 {address}\n"
            

            # Buttons: Removed as per user request (Details only)
            # markup = types.InlineKeyboardMarkup(row_width=3)
            # ... buttons removed ...
            
            # إرسال الرسالة (صورة أو نص)
            try:
                # ملاحظة: في تيليجرام لا يمكن وضع صور صغيرة بجانب كل سطر، لذا سنضع صورة المنتج الأول كغلاف للطلب إذا وجدت
                if first_image_path:
                    with open(first_image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=card_text, parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, card_text, parse_mode='Markdown')
            except Exception as e:
                print(f"Error sending order card {oid}: {e}")
                # Fallback to text if image fails
                bot.send_message(message.chat.id, card_text, parse_mode='Markdown')
            
        conn.close()
        
        # إعادة عرض القائمة لتحديث العداد
        show_seller_menu(message)
        
    except Exception as e:
        print(f"❌ Error in seller_messages: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض الرسائل: {e}")

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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
               COALESCE(u.FullName, 'زائر') as BuyerName,
               COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
               o.PaymentMethod, o.DeliveryAddress, o.Notes
        FROM Orders o
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE o.OrderID = ?
    """
    
    cursor.execute(query, (order_id,))
    order = cursor.fetchone()
    
    if not order:
        bot.answer_callback_query(call.id, "الطلب غير موجود")
        conn.close()
        return

    oid, total, status, date, buyer, phone, pay_method, address, notes = order

    # تنسيق المنتجات
    cursor.execute("""
        SELECT p.name, oi.quantity, oi.price, p.imagepath 
        FROM OrderItems oi 
        LEFT JOIN Products p ON oi.productid = p.productid 
        WHERE oi.orderid = ?
    """, (oid,))
    items = cursor.fetchall()
    
    conn.close()

    # تنسيق المنتجات
    items_text = ""
    first_image_path = None
    
    if not items:
        # Check if we really have no items, might be sync delay
        items_text = "⚠️ لا توجد منتجات (ربما تم حذفها أو لم تتم المزامنة بعد)"
    else:
        for i in items:
            p_name = i[0] if i[0] else "منتج محذوف"
            p_qty = i[1]
            p_price = i[2] if i[2] else 0
            p_image = i[3]
            
            if not first_image_path and p_image and os.path.exists(p_image):
                    first_image_path = p_image
            
            row_total = p_qty * p_price
            items_text += f"▫️ {p_name}\n   {p_qty}x | 💰 {p_price:,.0f} = {row_total:,.0f}\n"

    status_icon = {
        'Pending': '⏳',
        'Confirmed': '✅',
        'Shipped': '🚚',
        'Delivered': '🎉',
        'Rejected': '❌'
    }.get(status, '❓')
    
    status_text_ar = {
        'Pending': 'قيد الانتظار',
        'Confirmed': 'تم التأكيد',
        'Shipped': 'تم الشحن',
        'Delivered': 'تم التسليم',
        'Rejected': 'مرفوض'
    }.get(status, status)
    
    # تنسيق البطاقة
    try:
        # Try to parse if string, or format if datetime
        if isinstance(date, str):
             date_str = date.split(' ')[0]
        else:
             date_str = date.strftime('%Y-%m-%d')
    except:
        date_str = str(date)[:10]

    card_text = f"{status_icon} **تفاصيل الطلب #{oid}**\n"
    card_text += f"📅 {date_str}\n"
    card_text += f"📊 الحالة: {status_text_ar}\n\n"
    
    card_text += f"👤 العميل: {buyer}\n"
    card_text += f"📞 الهاتف: {phone}\n"
    if address:
        card_text += f"📍 العنوان: {address}\n"
    card_text += "─────────────────\n"
    
    card_text += f"{items_text}"
    card_text += "─────────────────\n"
    card_text += f"💰 **الإجمالي: {float(total):,.0f} IQD**\n"
    
    if pay_method:
        pm = "نقداً" if pay_method == 'cash' else "آجل"
        card_text += f"💳 الدفع: {pm}\n"
        
    # الأزرار (Confirm, Delete, Details, etc)
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    if status == 'Pending':
            buttons.append(types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_order_{oid}"))
    
    if status in ['Pending', 'Confirmed']:
            buttons.append(types.InlineKeyboardButton("🚚 شحن", callback_data=f"ship_order_{oid}"))
    
    buttons.append(types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_order_{oid}"))
    
    markup.add(*buttons)
    
    # Generate Image Receipt
    try:
        # Prepare data for generator
        # order_details: (oid, buyer_id, seller_id, total, status, date, address, phone...)
        # We need to construct a tuple similar to what the generator expects or update generator to handle dicts
        # Generator expects: (OrderID, BuyerID, SellerID, Total, Status, CreatedAt, Address)
        # We have: oid, total, status, date, buyer, phone, pay_method, address
        order_tuple = (oid, None, None, total, status, date, address) 
        
        print(f"DEBUG: Generating Receipt for Order #{oid}") # DEBUG
        
        # Items logic for generator check: generator seems to iterate items list of tuples
        # Generator expects: index 3->quantity, 4->price, 8->name, 10->imagepath
        # Our 'items' query returns: (name, qty, price, imagepath)
        # So we need to map our query result to what generator expects (which seems to be based on `get_order_items` full query)
        # Let's map it to a format the generator likes:
        # We can construct a list of mock tuples that match the indices used in generator.
        # Generator usage: item[3]=qty, item[4]=price, item[8]=name, item[10/13]=image
        
        # Construct mock items
        generator_items = []
        for i in items:
            # i = (name, qty, price, imagepath)
            # Create a tuple of size 14 with correct placements
            mock_item = [None]*14
            mock_item[3] = i[1] # Qty
            mock_item[4] = i[2] # Price
            mock_item[8] = i[0] # Name
            mock_item[10] = i[3] # ImagePath
            generator_items.append(mock_item)
            
        receipt_image = generate_order_card(order_tuple, generator_items, address, notes, None) 
        
        if receipt_image:
             # Minimal caption for image (Status + Total only, buttons below)
             minimal_caption = f"📊 {status_text_ar}\n💰 الإجمالي: {float(total):,.0f} IQD\n(v4)"
             bot.send_photo(call.message.chat.id, receipt_image, caption=minimal_caption, reply_markup=markup, parse_mode='Markdown')
        else:
             bot.send_message(call.message.chat.id, card_text, reply_markup=markup, parse_mode='Markdown')
             
    except Exception as e:
        print(f"Failed to generate receipt: {e}")
        # DEBUG: Show error to user to diagnose why image failed
        bot.send_message(call.message.chat.id, card_text + f"\n\n⚠️ Error: {str(e)}", reply_markup=markup, parse_mode='Markdown')
        
    bot.answer_callback_query(call.id)

def handle_confirm_order_seller(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Confirmed")
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
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
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_ship_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Shipped")
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
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
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_deliver_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Delivered")
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
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
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_reject_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Rejected")
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
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
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
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

@bot.message_handler(content_types=['contact'])
def handle_contact_message(message):
    """معالج رسائل جهة الاتصال (رقم الهاتف)"""
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states:
        return
    
    state = user_states[telegram_id]
    
    if state.get('step') == 'verify_store_access':
        # التحقق من رقم الهاتف للوصول للمتجر
        phone_number = message.contact.phone_number if message.contact else None
        
        if not phone_number:
            bot.send_message(message.chat.id, "⚠️ لم يتم الحصول على رقم الهاتف. يرجى المحاولة مرة أخرى.")
            return
        
        seller_id = state.get('seller_id')
        store_name = state.get('store_name', 'المتجر')
        username = state.get('username')
        
        # التحقق من رقم الهاتف
        if is_customer_registered_for_store_by_phone(phone_number, seller_id):
            # حفظ رقم الهاتف للجلسة
            user_states[telegram_id]['verified_phone'] = phone_number
            user_states[telegram_id]['verified_seller_id'] = seller_id
            user_states[telegram_id]['step'] = None
            
            # إزالة لوحة المفاتيح
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id,
                f"✅ **تم التحقق بنجاح!**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"يمكنك الآن الوصول إلى جميع منتجات المتجر.",
                reply_markup=markup,
                parse_mode='Markdown')
            
            # عرض المتجر
            seller_telegram_id = None
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=%s", (seller_id,))
            else:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=?", (seller_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                seller_telegram_id = result[0]
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 التواصل مع البائع", url=f"https://t.me/{username}" if username else None))
            
            bot.send_message(message.chat.id,
                f"❌ **رقم الهاتف غير مسجل**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"⚠️ هذا الرقم غير مسجل في قائمة الزبائن الآجلين.\n\n"
                f"📝 **للحصول على الوصول:**\n"
                f"• تواصل مع البائع لإضافتك كزبون آجل\n"
                f"• أو اطلب من البائع إضافتك من خلال قائمة '🏪 إدارة الزبائن الآجلين'",
                reply_markup=markup if username else None,
                parse_mode='Markdown')
            
            # إزالة الحالة
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "verify_store_access" and
                     message.text and message.text != "❌ إلغاء")
def handle_phone_number_text(message):
    """معالج إدخال رقم الهاتف يدوياً"""
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states:
        return
    
    state = user_states[telegram_id]
    
    if state.get('step') == 'verify_store_access':
        phone_number = message.text.strip()
        
        # التحقق من أن النص هو رقم هاتف
        if not phone_number or len(phone_number) < 7:
            bot.send_message(message.chat.id, "⚠️ يرجى إدخال رقم هاتف صحيح (مثال: 07701234567)")
            return
        
        seller_id = state.get('seller_id')
        store_name = state.get('store_name', 'المتجر')
        username = state.get('username')
        
        # التحقق من رقم الهاتف
        if is_customer_registered_for_store_by_phone(phone_number, seller_id):
            # حفظ رقم الهاتف للجلسة
            user_states[telegram_id]['verified_phone'] = phone_number
            user_states[telegram_id]['verified_seller_id'] = seller_id
            user_states[telegram_id]['step'] = None
            
            # إزالة لوحة المفاتيح
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id,
                f"✅ **تم التحقق بنجاح!**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"يمكنك الآن الوصول إلى جميع منتجات المتجر.",
                reply_markup=markup,
                parse_mode='Markdown')
            
            # عرض المتجر
            seller_telegram_id = None
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=%s", (seller_id,))
            else:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=?", (seller_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                seller_telegram_id = result[0]
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 التواصل مع البائع", url=f"https://t.me/{username}" if username else None))
            
            bot.send_message(message.chat.id,
                f"❌ **رقم الهاتف غير مسجل**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"⚠️ هذا الرقم غير مسجل في قائمة الزبائن الآجلين.\n\n"
                f"📝 **للحصول على الوصول:**\n"
                f"• تواصل مع البائع لإضافتك كزبون آجل\n"
                f"• أو اطلب من البائع إضافتك من خلال قائمة '🏪 إدارة الزبائن الآجلين'",
                reply_markup=markup if username else None,
                parse_mode='Markdown')
            
            # إزالة الحالة
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.text == "❌ إلغاء" and 
                     message.from_user.id in user_states and
                     user_states[message.from_user.id].get("step") == "verify_store_access")
def handle_cancel_phone_verification(message):
    """إلغاء عملية التحقق من رقم الهاتف"""
    telegram_id = message.from_user.id
    if telegram_id in user_states:
        del user_states[telegram_id]
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "❌ تم إلغاء عملية التحقق.", reply_markup=markup)

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
def handle_my_orders(message):
    telegram_id = message.from_user.id
    print(f"DEBUG: handle_my_orders processing for {telegram_id}") # Confirm handler is reached
    
    try:
        # التحقق إذا كان المستخدم مسجلاً
        user = get_user(telegram_id)
        if not user:
            bot.send_message(message.chat.id, "⚠️ يجب عليك تسجيل الدخول أولاً.")
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب الطلبات الخاصة بالمشتري (BuyerID)
        # استخدام BuyerID (TelegramID)
        query = """
            SELECT o.OrderID, s.StoreName, o.Total, o.Status, o.CreatedAt
            FROM Orders o
            JOIN Sellers s ON o.SellerID = s.SellerID
            WHERE o.BuyerID = ? OR o.BuyerID = ?
            ORDER BY o.CreatedAt DESC
            LIMIT 10
        """
        
        cursor.execute(query, (telegram_id, str(telegram_id)))
        orders = cursor.fetchall()
        conn.close()
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد لديك طلبات سابقة.")
            return
            
        text = "📋 **قائمة طلباتي**\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for order in orders:
            order_id, store_name, total, status, date = order
            
            status_icon = {
                'Pending': '⏳',
                'Confirmed': '✅',
                'Shipped': '🚚',
                'Delivered': '🎉',
                'Rejected': '❌'
            }.get(status, '❓')
            
            # Formating Total
            try:
                total_fmt = f"{float(total):,.0f}"
            except:
                total_fmt = str(total)

            button_text = f"{status_icon} طلب #{order_id} - {store_name} ({total_fmt} IQD)"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"my_order_{order_id}"))
            
        bot.send_message(message.chat.id, "اختر طلباً لعرض التفاصيل:", reply_markup=markup)
        
    except Exception as e:
        print(f"ERROR in handle_my_orders: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ تقني:\n{str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("my_order_"))
def handle_buyer_order_details(call):
    try:
        order_id = int(call.data.split("_")[2])
        
        order_details, items = get_order_details(order_id)
        
        if not order_details:
            bot.answer_callback_query(call.id, "الطلب غير موجود")
            return
            
        # order_details structure based on get_order_details return:
        # 0:OrderID, 1:BuyerID, 2:SellerID, 3:Total, 4:Status, 5:OrderDate, 6:Address, 7:Phone, 8:PaymentMethod, 9:FullyPaid
        
        store_name = "المتجر" 
        # نحتاج لجلب اسم المتجر، الدالة get_order_details لا ترجعه مباشرة بـ JOIN
        # سنحاول جلبه بشكل منفصل أو الاعتماد على seller_id
        seller_id = order_details[2]
        seller = get_seller_by_id(seller_id)
        if seller:
            store_name = seller[3]
            
        text = f"📋 **تفاصيل طلبي #{order_id}**\n\n"
        text += f"🏪 المتجر: {store_name}\n"
        text += f"📅 التاريخ: {order_details[5]}\n"
        text += f"📊 الحالة: {order_details[4]}\n"
        text += f"💰 الإجمالي: {order_details[3]} IQD\n"
        
        payment_method = 'نقداً' if order_details[8] == 'cash' else 'آجل'
        payment_status = 'مدفوع' if order_details[9] else 'غير مدفوع'
        text += f"💳 الدفع: {payment_method} ({payment_status})\n"
        
        if order_details[6]:
            text += f"📍 العنوان: {order_details[6]}\n"
            
        text += "\n📦 **المنتجات:**\n"
        
        for item in items:
            # item: ID, OrderID, ProductID, Qty, Price, RetQty, RetReason, RetDate, ProductName
            prod_name = item[8]
            qty = item[3]
            price = item[4]
            total_item = qty * price
            
            text += f"- {prod_name} (x{qty}) = {total_item:,.0f}\n"
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")) # or back to list?
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in buyer order details: {e}")

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

@bot.message_handler(func=lambda message: message.text == "🔙 رجوع")
def handle_back_button(message):
    telegram_id = message.from_user.id
    
    # التحقق إذا كان المستخدم زائراً
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

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية")
def handle_main_menu(message):
    telegram_id = message.from_user.id
    
    # Clear any active state when Main Button is pressed!
    if telegram_id in user_states:
        del user_states[telegram_id]
    
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

# ====== تنظيف الصور غير المستخدمة ======
@bot.message_handler(commands=['clean_images', 'clear_images'])
def clean_unused_images(message):
    if not is_bot_admin(message.from_user.id):
        return

    try:
        bot.send_message(message.chat.id, "🔄 **جاري فحص الصور غير المستخدمة...**")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get all used images from DB (Sellers, Categories, Products)
        used_images = set()
        
        # Products
        cursor.execute("SELECT ImagePath FROM Products WHERE ImagePath IS NOT NULL AND ImagePath != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0])) # Store filename only
            
        # Categories
        cursor.execute("SELECT ImagePath FROM Categories WHERE ImagePath IS NOT NULL AND ImagePath != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0]))
            
        # Sellers
        cursor.execute("SELECT ImagePath FROM Sellers WHERE ImagePath IS NOT NULL AND ImagePath != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0]))
            
        # 2. Clean ImageStorage Table (Cloud Backup)
        # We need to delete rows where FileName is NOT in used_images
        # Since we are using DBWrapper/CursorWrapper, we should check if table exists first
        deleted_db_count = 0
        try:
            # Get all stored images
            cursor.execute("SELECT FileName FROM ImageStorage")
            stored_files = cursor.fetchall()
            
            for row in stored_files:
                file_name = row[0]
                if file_name not in used_images:
                     cursor.execute("DELETE FROM ImageStorage WHERE FileName = ?", (file_name,))
                     deleted_db_count += 1
                     print(f"🗑️ Cleaned cloud image: {file_name}")
            
            conn.commit()
        except Exception as db_e:
            print(f"⚠️ ImageStorage cleanup skipped (Table might not exist): {db_e}")

        conn.close()
        
        # 3. Clean Local Disk (Images Folder)
        images_dir = os.path.join(DATA_DIR, 'Images')
        deleted_disk_count = 0
        reclaimed_space = 0
        
        if os.path.exists(images_dir):
            all_files = os.listdir(images_dir)
            for filename in all_files:
                file_path = os.path.join(images_dir, filename)
                
                # Skip valid usage
                if filename in used_images:
                    continue
                    
                # Skip non-files
                if not os.path.isfile(file_path):
                    continue
                    
                # DELETE ORPHAN
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_disk_count += 1
                    reclaimed_space += file_size
                    print(f"🗑️ Cleaned disk image: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to delete {filename}: {e}")
        
        # Convert bytes to readable
        size_str = f"{reclaimed_space} B"
        if reclaimed_space > 1024:
            size_str = f"{reclaimed_space / 1024:.2f} KB"
        if reclaimed_space > 1024 * 1024:
            size_str = f"{reclaimed_space / (1024 * 1024):.2f} MB"

        msg = (f"✅ **تم تنظيف الصور!**\n\n"
               f"🗑️ محذوف من السحابة (DB): {deleted_db_count}\n"
               f"🗑️ محذوف من القرص (Disk): {deleted_disk_count}\n"
               f"💾 مساحة القرص المسترجعة: {size_str}\n"
               f"🖼️ الصور النشطة المتبقية: {len(used_images)}")

        if used_images:
            msg += "\n\n📂 **قائمة الصور النشطة:**\n"
            # Show first 20 images
            for img in list(used_images)[:20]:
                msg += f"- `{img}`\n"
                
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {e}")
        print(f"Clean Images Error: {e}")
        traceback.print_exc()

@bot.message_handler(commands=['find_image'])
def find_image_usage(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Usage: /find_image <filename>")
            return
            
        target_name = args[1]
        bot.reply_to(message, f"🔍 Searching for '{target_name}'...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        found_msg = ""
        
        # Products
        if IS_POSTGRES:
            cursor.execute("SELECT ProductID, Name FROM Products WHERE ImagePath LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT ProductID, Name FROM Products WHERE ImagePath LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"📦 **Product:** {row[1]} (ID: {row[0]})\n"
            
        # Categories
        if IS_POSTGRES:
            cursor.execute("SELECT CategoryID, Name FROM Categories WHERE ImagePath LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT CategoryID, Name FROM Categories WHERE ImagePath LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"📂 **Category:** {row[1]} (ID: {row[0]})\n"
            
        # Sellers
        if IS_POSTGRES:
            cursor.execute("SELECT SellerID, StoreName FROM Sellers WHERE ImagePath LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT SellerID, StoreName FROM Sellers WHERE ImagePath LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"🏪 **Seller:** {row[1]} (ID: {row[0]})\n"
            
        conn.close()
        
        if found_msg:
             bot.reply_to(message, f"✅ **Found References:**\n{found_msg}", parse_mode='Markdown')
        else:
             bot.reply_to(message, "❌ Image not found in any active table.")
             
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

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


# ====== Start Command ======
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        # Register user if not exists
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM Users WHERE TelegramID = %s", (user_id,))
        else:
            cursor.execute("SELECT * FROM Users WHERE TelegramID = ?", (user_id,))
            
        user = cursor.fetchone()
        
        if not user:
            if IS_POSTGRES:
                cursor.execute("INSERT INTO Users (TelegramID, UserName, FullName, UserType) VALUES (%s, %s, %s, 'customer')", (user_id, username, full_name))
            else:
                cursor.execute("INSERT INTO Users (TelegramID, UserName, FullName, UserType) VALUES (?, ?, ?, 'customer')", (user_id, username, full_name))
            conn.commit()
            print(f"✅ New user registered: {full_name}")
            
        conn.close()

        # Send Welcome Message
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("🛍️ تصفح المنتجات", callback_data='browse_products')
        btn2 = types.InlineKeyboardButton("🛒 سلة التسوق", callback_data='view_cart')
        btn4 = types.InlineKeyboardButton("📞 تواصل معنا", callback_data='contact_us')
        markup.add(btn1, btn2, btn4)
        
        bot.reply_to(message, f"👋 أهلاً بك {full_name} في متجرنا!\n\nيمكنك البدء بالتسوق الآن:", reply_markup=markup)
        
    except Exception as e:
        print(f"Error in start command: {e}")
        bot.reply_to(message, "حدث خطأ بسيط، حاول مرة أخرى.")

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


# ====== Ping Command (No DB) ======
@bot.message_handler(commands=['ping'])
def ping_pong(message):
    try:
        bot.reply_to(message, "Pong! 🏓\nI am alive and listening.")
    except Exception as e:
        print(f"Ping error: {e}")


# ====== إدارة الطلبات (أزرار البطاقة) ======
@bot.callback_query_handler(func=lambda call: call.data.startswith(('confirm_order_', 'ship_order_', 'delete_order_', 'order_details_')))
def handle_order_actions(call):
    try:
        parts = call.data.split('_')
        action = parts[0] + '_' + parts[1] # e.g. confirm_order
        order_id = int(parts[2])
        
        seller_id = call.from_user.id
        # Verify seller owns this order (Basic check via DB helps security)
        # For now, simplistic status update.
        
        new_status = None
        notify_user_msg = None
        
        if action == "confirm_order":
            new_status = "Confirmed"
            notify_user_msg = "✅ تم تأكيد طلبك! سيتم تجهيزه قريباً."
            feedback = "✅ تم تأكيد الطلب بنجاح."
            
        elif action == "ship_order":
            new_status = "Shipped"
            notify_user_msg = "🚚 تم شحن طلبك! وهو في الطريق إليك."
            feedback = "🚚 تم تحديث الحالة إلى 'تم الشحن'."
            
        elif action == "delete_order":
            # Just Cancelled or actually Delete? 
            # Usually Cancelled is better for records.
            new_status = "Cancelled" 
            notify_user_msg = "❌ تم إلغاء طلبك من قبل المتجر."
            feedback = "🗑️ تم إلغاء الطلب."
        
        elif action == "order_details":
            # Show full text details
            order, items = get_order_details(order_id)
            if order:
                # Reuse notification logic or simple text
                 # بناء النص
                txt = f"📝 تفاصيل الطلب #{order_id}\n\n"
                txt += f"👤 المشتري: {order[11]}\n" # FullName from query
                txt += f"📞 {order[12]}\n"
                txt += f"📍 {order[6]}\n"
                txt += "📦 المنتجات:\n"
                for it in items:
                     txt += f"- {it[8]} (x{it[3]}) - {it[8]} IQD\n" # Index 8=Name
                
                bot.send_message(call.message.chat.id, txt)
                bot.answer_callback_query(call.id)
                return

        if new_status:
            # Update DB
            update_order_status(order_id, new_status)
            bot.answer_callback_query(call.id, feedback)
            bot.send_message(call.message.chat.id, f"📝 {feedback} (تسلسل #{order_id})")
            
            # Notify Buyer
            order_info, _ = get_order_details(order_id)
            if order_info:
                buyer_id = order_info[1]
                try:
                    bot.send_message(buyer_id, f"🔔 تحديث حالة الطلب #{order_id}:\n{notify_user_msg}")
                except:
                    pass

    except Exception as e:
        print(f"Order Action Error: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ أثناء تنفيذ الإجراء")

# تشغيل البوت
if __name__ == "__main__":
    print("🚀 SYSTEM STARTUP: Bot script is running...")
    
    # 1. Log Token Status
    if TOKEN:
        print(f"🔑 Token Loaded: {TOKEN[:5]}...{TOKEN[-5:]} (Length: {len(TOKEN)})")
    else:
        print("❌ CRITICAL: No Token Found in Environment!")

    if os.environ.get('DATABASE_URL'):
        print("☁️ DATABASE MODE: CLOUD (PostgreSQL)")
    else:
        print("💻 DATABASE MODE: LOCAL (SQLite)")

    try:
        print("🛠️ Initializing Database...")
        init_db()
        print("✅ Database Initialized Successfully")
        
        # Debug: Check products count after initialization
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Products")
        result = cursor.fetchone()
        product_count = result[0] if result else 0
        print(f"📊 Total products in database: {product_count}")
        
        cursor.execute("SELECT COUNT(*) FROM Products WHERE Quantity > 0 AND Status='active'")
        result = cursor.fetchone()
        active_product_count = result[0] if result else 0
        print(f"📊 Active products with Quantity > 0: {active_product_count}")
        
        conn.close()
    except Exception as e:
        print(f"❌ CRITICAL DATABASE ERROR: {e}")
        traceback.print_exc()
        # Non-fatal? Maybe allow bot to try starting anyway, or fail loud?
        # For now, let's fail loud but AFTER printing the error.
    try:
        print("🧹 Clearing Webhooks...")
        bot.remove_webhook()
        
    except Exception as e:
        print(f"⚠️ Failed to remove webhook: {e}")

    print("📡 Starting Polling...")
    
    # Infinite loop to auto-restart on crashes/connection errors
    while True:
        try:
            # infinity_polling handles many errors internally, but this loop catches the rest
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=['message', 'callback_query', 'my_chat_member'])
        except Exception as e:
            print(f"⚠️ Polling Error (Restarting in 5s): {e}")
            time.sleep(5)
            continue

