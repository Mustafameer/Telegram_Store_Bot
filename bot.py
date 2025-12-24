import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv
import re
import sys
import traceback
import time
import uuid
from datetime import datetime
import base64
import shutil
import urllib.parse
from contextlib import contextmanager

# استيراد مكتبات إضافية
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

# ----------------- إعداد البوت وملفات -----------------
load_dotenv()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if TOKEN:
    TOKEN = TOKEN.strip()

if not TOKEN:
    print("❌ FATAL ERROR: TELEGRAM_BOT_TOKEN environment variable is NOT set!")
    sys.exit(1)
else:
    print(f"[OK] DEBUG: TELEGRAM_BOT_TOKEN found. Starts with: {TOKEN[:10]}... Ends with: ...{TOKEN[-5:]}")
    print(f"[OK] DEBUG: Token Length: {len(TOKEN)}")

bot = telebot.TeleBot(TOKEN)
IS_POSTGRES = (os.environ.get('DATABASE_URL') is not None) and (psycopg2 is not None)

# إضافة معرف صاحب البوت (أدمن) - للتحكم التقني فقط
BOT_ADMIN_ID = 1041977029

@bot.message_handler(commands=['sys_info'])
def sys_info(message):
    try:
        import sys
        info = f"🤖 **System Diagnostics**\n\n"
        info += f"🐍 Python: {sys.version.split()[0]}\n"
        info += f"📦 IS_POSTGRES: `{IS_POSTGRES}`\n"
        info += f"🔑 DATABASE_URL: {'✅ Found' if os.environ.get('DATABASE_URL') else '❌ Missing'}\n"
        info += f"🐘 psycopg2: {'✅ Imported' if psycopg2 else '❌ Missing'}\n"
        
        try:
            import psycopg2 as pg2_test
            info += "🐘 Import Test: OK\n"
        except ImportError as e:
            info += f"🐘 Import Test: ❌ {e}\n"
            
        bot.reply_to(message, info, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed_data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")
os.makedirs(IMAGES_FOLDER, exist_ok=True)

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
        self.lastrowid = None

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def execute(self, query, params=None):
        if self.is_postgres:
            query = query.replace('?', '%s')
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            query = query.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            query = query.replace('DATETIME', 'TIMESTAMP')
        
        try:
            if params is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, params)
                
            if not self.is_postgres:
                self.lastrowid = self.cursor.lastrowid
            else:
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
            print(f"[SUCCESS] BOT CONNECTED TO POSTGRES (Cloud)")
            print(f"   Host: {hostname}")
            print("="*50 + "\n")
            return DBWrapper(conn, is_postgres=True)
        except Exception as e:
            print(f"[CRITICAL ERROR] connecting to Postgres: {e}")
            raise e
    else:
        print("\n" + "="*50)
        print(f"⚠️ BOT CONNECTED TO LOCAL SQLITE (No DATABASE_URL)")
        print(f"   File: {DB_FILE}")
        print("="*50 + "\n")
        return DBWrapper(sqlite3.connect(DB_FILE), is_postgres=False)

# ===================== قاعدة البيانات =====================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users
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

    # 2. Sellers
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

    # 3. CreditCustomers
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

    # 4. CreditLimits
    cursor.execute("""
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

    # 5. Categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories(
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            Name TEXT,
            OrderIndex INTEGER DEFAULT 0,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 6. Products
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

    # 7. Carts
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

    # 8. Orders
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
            FullyPaid BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 9. OrderItems
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

    # 10. Returns
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

    # 11. Messages
    cursor.execute("""
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

    # 12. CustomerCredit
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

    # 13. Image Storage
    if IS_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BYTEA,
                UploadedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BLOB,
                UploadedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    # ----------------- MIGRATIONS -----------------
    def ensure_column(table, column, definition):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
            print(f"[OK] Migrated: Added {column} to {table}")
        except Exception as e:
            pass
            
    ensure_column('Sellers', 'ImagePath', 'TEXT')
    ensure_column('Categories', 'ImagePath', 'TEXT')
    ensure_column('Products', 'ImagePath', 'TEXT')
    ensure_column('Sellers', 'SuspensionReason', 'TEXT')
    ensure_column('Sellers', 'SuspendedBy', 'INTEGER')
    ensure_column('Sellers', 'SuspendedAt', 'DATETIME')
    
    conn.commit()
    conn.close()

init_db()

# ===================== دوال النظام =====================
def add_user(telegram_id, username, usertype, phone_number=None, full_name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (TelegramID) 
            DO UPDATE SET 
                UserName = EXCLUDED.UserName, 
                UserType = EXCLUDED.UserType, 
                PhoneNumber = COALESCE(EXCLUDED.PhoneNumber, Users.PhoneNumber), 
                FullName = COALESCE(EXCLUDED.FullName, Users.FullName)
        """, (telegram_id, username, usertype, phone_number, full_name))
    else:
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
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO Sellers (TelegramID, UserName, StoreName)
            VALUES (%s, %s, %s)
            ON CONFLICT (TelegramID) DO NOTHING
        """, (telegram_id, username, store_name))
    else:
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
    
    if not seller:
        user = get_user(telegram_id)
        if user and user[3] == 'seller':
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
    product = get_product_by_id(product_id)
    if not product:
        return None
    
    # التحقق إذا كان الزبون آجلاً
    if phone_number or full_name:
        if is_credit_customer(seller_id, phone_number, full_name):
            return product[6] if product[6] is not None and product[6] > 0 else product[5]
    
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

def update_cart_quantity_db(user_id, product_id, new_quantity):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Carts SET Quantity=? WHERE UserID=? AND ProductID=?", 
                  (new_quantity, user_id, product_id))
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
    
    if IS_POSTGRES and not order_id:
        try:
            res = cursor.fetchone()
            if res:
                order_id = res[0]
        except Exception as e:
            print(f"DEBUG: Error in fallback fetchone: {e}")

    for pid, qty, price in cart_items:
        cursor.execute("SELECT Quantity FROM Products WHERE ProductID = ?", (pid,))
        res = cursor.fetchone()
        
        if not res:
            print(f"⚠️ Warning: Product {pid} not found during Order {order_id} creation. Skipping Item.")
            continue
            
        current_qty_in_db = res[0]
        
        cursor.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                       (order_id, pid, qty, price))
                       
        new_qty = current_qty_in_db - qty
        if new_qty < 0:
            new_qty = 0
        cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
    
    if payment_method == 'credit' and not fully_paid:
        buyer_info = get_user(buyer_id)
        if buyer_info:
            phone = buyer_info[4]
            full_name = buyer_info[5]
            customer = get_credit_customer(seller_id, phone, full_name)
            if customer:
                can_purchase, message, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, total)
                if not can_purchase:
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
        LEFT JOIN Products p ON oi.ProductID = p.ProductID
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

# ===================== نظام الزبائن الآجل =====================
def add_credit_customer(seller_id, full_name, phone_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO CreditCustomers (SellerID, FullName, PhoneNumber)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (seller_id, full_name, phone_number))
        else:
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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cc.*, 
               COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
               COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
               COALESCE(cl.IsActive, TRUE) as LimitActive
        FROM CreditCustomers cc
        LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
        WHERE cc.SellerID=? 
        ORDER BY cc.FullName
    """, (seller_id,))
    
    customers = cursor.fetchall()
    conn.close()
    return customers

def is_credit_customer(seller_id, phone_number, full_name):
    customer = get_credit_customer(seller_id, phone_number, full_name)
    return customer is not None

# ===================== نظام كشف حساب الزبائن الآجل =====================
def add_credit_transaction(customer_id, seller_id, transaction_type, amount, description=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    query = """
        INSERT INTO CustomerCredit 
        (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if IS_POSTGRES:
        query += " RETURNING CreditID"
    
    cursor.execute(query, (customer_id, seller_id, transaction_type, amount, description, balance_before, balance_after))
    
    if transaction_type in ['purchase', 'payment']:
        update_credit_usage(customer_id, seller_id, amount, transaction_type)
    
    conn.commit()
    conn.close()
    return True

def get_customer_balance(customer_id, seller_id):
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

# ===================== نظام حدود الائتمان =====================
def check_credit_limit(customer_id, seller_id, new_amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount 
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
    """, (customer_id, seller_id))
    
    limit_data = cursor.fetchone()
    
    if not limit_data:
        conn.close()
        return True, "لا يوجد حد ائتماني محدد", 0, 0, 0
    
    max_limit, current_used = limit_data
    new_total = current_used + new_amount
    
    if new_total > max_limit:
        remaining = max_limit - current_used
        conn.close()
        return False, f"❌ تجاوز الحد الائتماني! الحد الأقصى: {max_limit:,.0f} دينار، المستخدم: {current_used:,.0f} دينار، المتبقي: {remaining:,.0f} دينار", max_limit, current_used, remaining
    
    warning_percentage = current_used / max_limit if max_limit > 0 else 0
    
    if warning_percentage >= 0.8:
        conn.close()
        return True, f"⚠️ تحذير: وصلت إلى {warning_percentage*100:.0f}% من حدك الائتماني", max_limit, current_used, max_limit - current_used
    
    conn.close()
    return True, f"✅ الحد الائتماني مناسب. المتبقي: {max_limit - current_used:,.0f} دينار", max_limit, current_used, max_limit - current_used

def update_credit_usage(customer_id, seller_id, amount, transaction_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    
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

# ===================== دوال إدارة الحسابات =====================
def suspend_seller(seller_id, suspended_by, reason=None):
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
    seller = get_seller_by_telegram(seller_telegram_id)
    return seller and seller[5] == 'active'

# ===================== دالة حذف الطلب مع تحديث الكميات =====================
def delete_order_and_restore_quantities(order_id, seller_id):
    """حذف الطلب وإعادة الكميات للمخزون"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. الحصول على عناصر الطلب
        cursor.execute("""
            SELECT ProductID, Quantity 
            FROM OrderItems 
            WHERE OrderID = ?
        """, (order_id,))
        order_items = cursor.fetchall()
        
        # 2. إعادة الكميات إلى المخزون
        for product_id, quantity in order_items:
            cursor.execute("""
                UPDATE Products 
                SET Quantity = Quantity + ? 
                WHERE ProductID = ?
            """, (quantity, product_id))
        
        # 3. حذف الرسائل المرتبطة بالطلب
        cursor.execute("DELETE FROM Messages WHERE OrderID = ?", (order_id,))
        
        # 4. حذف عناصر الطلب
        cursor.execute("DELETE FROM OrderItems WHERE OrderID = ?", (order_id,))
        
        # 5. حذف الطلب نفسه
        cursor.execute("DELETE FROM Orders WHERE OrderID = ? AND SellerID = ?", (order_id, seller_id))
        
        conn.commit()
        conn.close()
        
        return True, f"✅ تم حذف الطلب #{order_id} وإعادة الكميات إلى المخزون"
        
    except Exception as e:
        print(f"Error deleting order: {e}")
        return False, f"❌ حدث خطأ أثناء حذف الطلب: {str(e)}"

# ===================== إشعار البائع بطلب جديد =====================
def notify_seller_of_order(order_id, buyer_id, seller_id):
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
    
    full_notification = f"🛎️ **طلب جديد!**\n\n"
    full_notification += f"🏪 المتجر: {store_name}\n"
    full_notification += f"🆔 رقم الطلب: {order_id}\n"
    full_notification += f"👤 المشتري: {buyer_name}\n"
    full_notification += f"📞 رقم الهاتف: {buyer_phone}\n"
    full_notification += f"💰 الإجمالي: {order_details[3]} IQD\n"
    full_notification += f"💳 طريقة الدفع: {'نقداً' if order_details[8] == 'cash' else 'على الحساب'}\n"
    full_notification += f"💵 حالة الدفع: {'مدفوع بالكامل' if order_details[9] == 1 else 'غير مدفوع بالكامل'}\n"
    
    order_date = str(order_details[5]).split()[0]
    full_notification += f"📅 تاريخ الطلب: {order_date}\n"
    
    if order_details[6]:
        full_notification += f"📍 العنوان: {order_details[6]}\n"
    
    full_notification += f"\n📦 **المنتجات:**\n"
    
    for item in items:
        item_id, order_id_val, product_id, quantity, price, returned_qty, return_reason, return_date = item[:8]
        product_name = item[8] if len(item) > 8 else "منتج"
        full_notification += f"• {product_name} × {quantity} = {quantity * price} IQD\n"

    short_caption = f"🛎️ **طلب جديد #{order_id}**\n💰 الإجمالي: {order_details[3]} IQD"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("تفاصيل 📄", callback_data=f"order_details_{order_id}"),
               types.InlineKeyboardButton("تأكيد ✅", callback_data=f"confirm_order_{order_id}"))
    markup.add(types.InlineKeyboardButton("شحن 🚚", callback_data=f"ship_order_{order_id}"),
               types.InlineKeyboardButton("حذف 🗑️", callback_data=f"delete_order_{order_id}"))
    markup.add(types.InlineKeyboardButton("الرئيسية 🏠", callback_data="seller_main_menu"))
    
    create_message(order_id, seller_id, 'new_order', full_notification)
    
    try:
        from utils.receipt_generator import generate_order_card
        
        receipt_img = generate_order_card(order_details, items, buyer_name, buyer_phone, store_name)
        
        if receipt_img:
            receipt_img.name = f"receipt_{order_id}.png"
            bot.send_photo(seller_telegram_id, receipt_img, caption=short_caption, reply_markup=markup, parse_mode='Markdown')
            print(f"✅ Sent Visual Receipt for Order #{order_id}")
            return
    except ImportError:
        pass
    except Exception as img_err:
        print(f"⚠️ Failed to generate/send receipt image: {img_err}")
    
    bot.send_message(seller_telegram_id, full_notification, reply_markup=markup, parse_mode='Markdown')

# ===================== معالجات البحث عن طلب =====================
user_states = {}

@bot.message_handler(func=lambda message: "🔍 بحث عن طلب" in message.text and is_seller(message.from_user.id))
def handle_search_order_request(message):
    try:
        msg = bot.send_message(message.chat.id, "🔍 **بحث عن طلب**\n\nيرجى إدخال رقم الطلب (ID) للبحث عنه:", parse_mode='Markdown')
        user_states[message.from_user.id] = {'state': 'searching_order'}
        bot.register_next_step_handler(msg, process_search_order)
    except Exception as e:
        print(f"Error in search request: {e}")
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في بدء عملية البحث.")

def process_search_order(message):
    try:
        telegram_id = message.from_user.id
        
        if telegram_id not in user_states or user_states[telegram_id].get('state') != 'searching_order':
            bot.send_message(message.chat.id, "⚠️ انتهت جلسة البحث. يرجى المحاولة مرة أخرى.")
            return
            
        del user_states[telegram_id]
        
        if not message.text or not message.text.strip().isdigit():
            bot.send_message(message.chat.id, "⚠️ الرجاء إدخال رقم صحيح.")
            return

        order_id = int(message.text.strip())
        seller = get_seller_by_telegram(telegram_id)
        if not seller:
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT OrderID FROM Orders WHERE OrderID = ? AND SellerID = ?", (order_id, seller[0]))
        order = cursor.fetchone()
        conn.close()

        if not order:
            bot.send_message(message.chat.id, f"⚠️ الطلب #{order_id} غير موجود أو لا يتبع لمتجرك.")
            return

        order_details, items = get_order_details(order_id)
        
        if not order_details:
            bot.send_message(message.chat.id, "⚠️ خطأ في استرجاع بيانات الطلب.")
            return
            
        try:
            from utils.receipt_generator import generate_order_card
            
            buyer_name = order_details[11] or "زائر"
            buyer_phone = order_details[12] or "غير متوفر"
            store_name = order_details[14] or "متجرك"
            
            card_img = generate_order_card(order_details, items, buyer_name, buyer_phone, store_name)
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton(f"🗑️ حذف الطلب #{order_id}", callback_data=f"delete_order_{order_id}"))
            
            status_buttons = []
            current_status = order_details[4]
            
            if current_status == 'Pending':
                status_buttons.append(types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_order_{order_id}"))
            elif current_status == 'Confirmed':
                status_buttons.append(types.InlineKeyboardButton("🚚 شحن", callback_data=f"ship_order_{order_id}"))
            elif current_status == 'Shipped':
                status_buttons.append(types.InlineKeyboardButton("🎉 تسليم", callback_data=f"deliver_order_{order_id}"))
            
            status_buttons.append(types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_order_{order_id}"))
            
            if status_buttons:
                markup.row(*status_buttons)
            
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
            
            if card_img:
                card_img.name = f"order_{order_id}.png"
                caption = f"🔎 **نتيجة البحث: الطلب #{order_id}**\n"
                caption += f"📊 الحالة: {current_status}\n"
                caption += f"💰 الإجمالي: {order_details[3]:,.0f} دينار\n"
                caption += f"📅 التاريخ: {str(order_details[5]).split()[0]}"
                
                bot.send_photo(message.chat.id, card_img, caption=caption, reply_markup=markup, parse_mode='Markdown')
            else:
                text = f"🔎 **نتيجة البحث: الطلب #{order_id}**\n\n"
                text += f"📊 الحالة: {current_status}\n"
                text += f"💰 الإجمالي: {order_details[3]:,.0f} دينار\n"
                text += f"👤 المشتري: {buyer_name}\n"
                text += f"📞 الهاتف: {buyer_phone}\n"
                text += f"📅 التاريخ: {str(order_details[5]).split()[0]}\n"
                
                if order_details[6]:
                    text += f"📍 العنوان: {order_details[6]}\n"
                
                text += f"\n📦 **المنتجات:**\n"
                for item in items:
                    product_name = item[8] if len(item) > 8 else "منتج"
                    quantity = item[3]
                    price = item[4]
                    text += f"• {product_name} × {quantity} = {quantity * price:,.0f} دينار\n"
                
                bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
                
        except Exception as e:
            print(f"Error generating order card: {e}")
            bot.send_message(message.chat.id, 
                           f"🔎 **الطلب #{order_id}**\n\n"
                           f"📊 الحالة: {order_details[4]}\n"
                           f"💰 الإجمالي: {order_details[3]:,.0f} دينار\n"
                           f"⚠️ *ملاحظة:* تعذر عرض التفاصيل المرئية، يتم عرض النص فقط.",
                           parse_mode='Markdown')

    except Exception as e:
        print(f"Error in process_search: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, "⚠️ حدث خطأ أثناء البحث. يرجى المحاولة مرة أخرى.")

# ===================== معالجات حذف الطلب =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_order_"))
def handle_delete_order_callback(call):
    try:
        order_id = int(call.data.split("_")[2])
        seller = get_seller_by_telegram(call.from_user.id)
        if not seller:
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية.")
            return

        # استخدام الدالة المحسنة لحذف الطلب
        success, message = delete_order_and_restore_quantities(order_id, seller[0])
        
        if success:
            bot.answer_callback_query(call.id, message)
            bot.edit_message_text(
                f"🗑️ **تم حذف الطلب #{order_id}**\n\nتم إعادة الكميات للمخزون.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(call.id, message)
            
    except Exception as e:
        print(f"Delete Error: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ أثناء الحذف.")

# ===================== القوائم الرئيسية =====================
def show_bot_admin_menu(message):
    telegram_id = message.from_user.id
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
    
    store_name = seller[3] if seller else "المتجر الإداري"
    unread_count = len(get_unread_messages(seller[0])) if seller else 0
    messages_badge = f" 📨({unread_count})" if unread_count > 0 else ""
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row("👑 لوحة التحكم الإدارية", "🏪 منتجاتي", "📁 الأقسام")
    markup.row("📦 الطلبات", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    markup.row("🔍 بحث عن طلب", "🔗 رابط المتجر", "📊 إحصائيات النظام")
    markup.row("🗑️ حذف متجر", "➕ إضافة متجر", "📋 قائمة المتاجر")
    markup.row("👑 إدارة الحسابات", "🛍️ وضع المشتري", "🏠 الرئيسية")
    
    welcome_msg = f"👑🏪 **مرحباً بأدمن البوت وصاحب المتجر!**\n\n"
    welcome_msg += f"🏪 متجرك: {store_name}\n"
    welcome_msg += f"👑 صلاحياتك: إدارة النظام الكاملة"
    
    if unread_count > 0:
        welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

def show_seller_menu(message):
    telegram_id = message.from_user.id
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ? AND Status IN ('Pending', 'Confirmed')", (seller[0],))
    pending_count = cursor.fetchone()[0]
    conn.close()
    
    orders_badge = f" ({pending_count})" if pending_count > 0 else ""
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row("🏪 منتجاتي", "📁 الأقسام", f"📦 الطلبات{orders_badge}")
    markup.row("🔍 بحث عن طلب", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    markup.row("🔗 رابط المتجر", "🛍️ وضع المشتري", "🏠 الرئيسية")
    
    welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
    welcome_msg += f"🏪 متجرك: {store_name}"
    
    if pending_count > 0:
        welcome_msg += f"\n\nلديك {pending_count} طلبات جديدة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

def show_buyer_main_menu(message):
    telegram_id = message.from_user.id
    user = get_user(telegram_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
    markup.row("💰 كشف حسابي الآجل", "👤 تعديل بياناتي", "🏪 إنشاء متجر جديد")
    markup.row("🏠 الرئيسية")
    
    welcome_msg = "👋 **مرحباً بك كـ مشتري!**\nاختر من القائمة:"
    
    if user and (user[4] or user[5]):
        welcome_msg += f"\n\n👤 الاسم: {user[5] if user[5] else 'غير محدد'}"
        welcome_msg += f"\n📞 الهاتف: {user[4] if user[4] else 'غير محدد'}"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# ===================== /start command =====================
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
            
            if telegram_id == seller_telegram_id:
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
                    bot.send_message(message.chat.id,
                                    "⚠️ **لست مسجلاً كبائع**\n\n"
                                    "يبدو أنك لست مسجلاً كصاحب متجر.\n"
                                    "يرجى التواصل مع الإدارة.")
            else:
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
            add_user(telegram_id, username, "buyer")
            show_buyer_main_menu(message)
    elif user_type == 'buyer':
        show_buyer_main_menu(message)
    else:
        add_user(telegram_id, username, "buyer")
        show_buyer_main_menu(message)

# ===================== دوال مساعدة =====================
def escape_markdown_v1(text):
    if not text:
        return ""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

def format_seller_mention(username, seller_telegram_id):
    try:
        if not username:
            return ''
        if seller_telegram_id == BOT_ADMIN_ID:
            return escape_markdown_v1(username)
        return f"@{escape_markdown_v1(username)}"
    except:
        return escape_markdown_v1(username) or ''

def generate_store_link(telegram_id):
    bot_info = get_bot_info()
    if bot_info['username']:
        return f"https://t.me/{bot_info['username']}?start=store_{telegram_id}"
    return None

def get_bot_info():
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
    cursor.execute("UPDATE Messages SET IsRead = TRUE WHERE MessageID = ?", (message_id,))
    conn.commit()
    conn.close()

# ===================== معالجات أخرى =====================
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_order_"))
def handle_confirm_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Confirmed")
    bot.answer_callback_query(call.id, "✅ تم تأكيد الطلب")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ship_order_"))
def handle_ship_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Shipped")
    bot.answer_callback_query(call.id, "🚚 تم تحديث حالة الشحن")

@bot.callback_query_handler(func=lambda call: call.data.startswith("deliver_order_"))
def handle_deliver_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Delivered")
    bot.answer_callback_query(call.id, "✅ تم تسليم الطلب")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_order_"))
def handle_reject_order(call):
    order_id = int(call.data.split("_")[2])
    update_order_status(order_id, "Rejected")
    bot.answer_callback_query(call.id, "❌ تم رفض الطلب")

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية")
def handle_main_menu(message):
    telegram_id = message.from_user.id
    
    if telegram_id in user_states:
        del user_states[telegram_id]
    
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(message)
    elif is_seller(telegram_id):
        show_seller_menu(message)
    else:
        show_buyer_main_menu(message)

# ===================== تشغيل البوت =====================
print("🚀 بدأ تشغيل بوت متجرنا...")
print("✅ النظام الجديد شامل جميع الميزات:")

if __name__ == "__main__":
    print("🛠️ Initializing Database...")
    init_db()
    print("✅ Database Initialized Successfully")
    
    print("📡 Starting Polling...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=['message', 'callback_query'])
        except Exception as e:
            print(f"⚠️ Polling Error (Restarting in 5s): {e}")
            time.sleep(5)
            continue