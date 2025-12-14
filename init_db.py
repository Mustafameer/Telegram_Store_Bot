import sqlite3
import os

# استخدام المسار المطلق للتأكد من الاتساق
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "store.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")

def init_db():
    """تهيئة قاعدة البيانات وإنشاء جميع الجداول إذا لم تكن موجودة"""
    
    # إنشاء مجلد الصور إذا لم يكن موجوداً
    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("🔄 جاري إنشاء قاعدة البيانات...")

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
    print("✅ تم إنشاء جدول CreditCustomers")

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
    print("✅ تم إنشاء جدول CreditLimits")

    # جدول المستخدمين
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
    print("✅ تم إنشاء جدول Users")

    # جدول البائعين
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
    print("✅ تم إنشاء جدول Sellers")

    # جدول كشف حساب الزبائن الآجل
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
    print("✅ تم إنشاء جدول CustomerCredit")

    # جدول الأقسام
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories(
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            Name TEXT,
            OrderIndex INTEGER DEFAULT 0,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)
    print("✅ تم إنشاء جدول Categories")

    # جدول المنتجات
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
    print("✅ تم إنشاء جدول Products")

    # جدول سلة المشتريات
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
    print("✅ تم إنشاء جدول Carts")

    # جدول الطلبات
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
    print("✅ تم إنشاء جدول Orders")

    # جدول عناصر الطلب
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
    print("✅ تم إنشاء جدول OrderItems")

    # جدول المرتجعات
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
    print("✅ تم إنشاء جدول Returns")

    # جدول الرسائل
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
    print("✅ تم إنشاء جدول Messages")

    conn.commit()
    conn.close()
    
    print("🎉 تم إنشاء قاعدة البيانات بنجاح!")
    print(f"📁 قاعدة البيانات موجودة في: {DB_FILE}")
    print(f"📁 مجلد الصور: {IMAGES_FOLDER}")

def check_and_fix_db():
    """التحقق من وجود جميع الجداول وإصلاح النواقص"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    tables = [
        'CreditCustomers', 'CreditLimits', 'Users', 'Sellers', 'CustomerCredit', 
        'Categories', 'Products', 'Carts', 'Orders', 'OrderItems', 'Returns', 'Messages'
    ]
    
    missing_tables = []
    
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            missing_tables.append(table)
    
    conn.close()
    
    if missing_tables:
        print(f"⚠️ الجداول التالية غير موجودة: {missing_tables}")
        print("🔄 جاري إصلاح قاعدة البيانات...")
        init_db()
    else:
        print("✅ جميع الجداول موجودة وسليمة")

def add_sample_data():
    """إضافة بيانات تجريبية للاختبار"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # التحقق إذا كانت هناك بيانات موجودة
    cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        print("📊 جاري إضافة بيانات تجريبية...")
        
        # إضافة أدمن البوت
        cursor.execute("""
            INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, FullName) 
            VALUES (?, ?, ?, ?)
        """, (1041977029, 'admin', 'bot_admin', 'أدمن النظام'))
        
        # إضافة بائع تجريبي
        cursor.execute("""
            INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, FullName) 
            VALUES (?, ?, ?, ?)
        """, (123456789, 'seller1', 'seller', 'محمد أحمد'))
        
        cursor.execute("""
            INSERT OR REPLACE INTO Sellers (TelegramID, UserName, StoreName) 
            VALUES (?, ?, ?)
        """, (123456789, 'seller1', 'متجر الإلكترونيات'))
        
        # إضافة مشتري تجريبي
        cursor.execute("""
            INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, FullName, PhoneNumber) 
            VALUES (?, ?, ?, ?, ?)
        """, (987654321, 'buyer1', 'buyer', 'علي حسن', '07901234567'))
        
        # إضافة أقسام
        cursor.execute("""
            INSERT INTO Categories (SellerID, Name, OrderIndex) 
            VALUES (?, ?, ?)
        """, (1, 'هواتف ذكية', 1))
        
        cursor.execute("""
            INSERT INTO Categories (SellerID, Name, OrderIndex) 
            VALUES (?, ?, ?)
        """, (1, 'حواسيب محمولة', 2))
        
        cursor.execute("""
            INSERT INTO Categories (SellerID, Name, OrderIndex) 
            VALUES (?, ?, ?)
        """, (1, 'إكسسوارات', 3))
        
        # إضافة منتجات تجريبية
        cursor.execute("""
            INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, 1, 'سامسونج جالاكسي S23', 'هاتف ذكي بشاشة 6.1 بوصة، كاميرا 50 ميجابكسل', 500000, 450000, 10))
        
        cursor.execute("""
            INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, 1, 'آيفون 14', 'هاتف آيفون بشاشة 6.1 بوصة، معالج A15', 600000, 550000, 5))
        
        cursor.execute("""
            INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, 2, 'لابتوب ديل XPS 13', 'لابتوب بشاشة 13 بوصة، معالج i7، 16GB RAM', 1500000, 1400000, 3))
        
        cursor.execute("""
            INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, 3, 'سماعات ايربودز', 'سماعات لاسلكية مع شاحن', 150000, 130000, 20))
        
        # إضافة زبون آجل تجريبي
        cursor.execute("""
            INSERT INTO CreditCustomers (SellerID, FullName, PhoneNumber) 
            VALUES (?, ?, ?)
        """, (1, 'علي حسن', '07901234567'))
        
        conn.commit()
        print("✅ تم إضافة البيانات التجريبية بنجاح")
    else:
        print("✅ قاعدة البيانات تحتوي بالفعل على بيانات")
    
    conn.close()

def backup_database():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    import shutil
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BASE_DIR, f"store_backup_{timestamp}.db")
    
    try:
        shutil.copy2(DB_FILE, backup_file)
        print(f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
        return None

def restore_database(backup_file):
    """استعادة قاعدة البيانات من نسخة احتياطية"""
    import shutil
    
    if not os.path.exists(backup_file):
        print(f"❌ ملف النسخة الاحتياطية غير موجود: {backup_file}")
        return False
    
    try:
        # إيقاف الاتصالات الحالية مع قاعدة البيانات
        try:
            import sqlite3
            conn = sqlite3.connect(DB_FILE)
            conn.close()
        except:
            pass
        
        # استعادة النسخة الاحتياطية
        shutil.copy2(backup_file, DB_FILE)
        print(f"✅ تم استعادة قاعدة البيانات من: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ خطأ في استعادة قاعدة البيانات: {e}")
        return False

def show_database_stats():
    """عرض إحصائيات قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("\n📊 **إحصائيات قاعدة البيانات:**\n")
    
    # عدد المستخدمين حسب النوع
    cursor.execute("SELECT UserType, COUNT(*) FROM Users GROUP BY UserType")
    user_types = cursor.fetchall()
    
    for user_type, count in user_types:
        print(f"👥 {user_type}: {count}")
    
    # عدد المتاجر
    cursor.execute("SELECT COUNT(*) FROM Sellers")
    seller_count = cursor.fetchone()[0]
    print(f"🏪 عدد المتاجر: {seller_count}")
    
    # عدد المنتجات
    cursor.execute("SELECT COUNT(*) FROM Products")
    product_count = cursor.fetchone()[0]
    print(f"🛒 عدد المنتجات: {product_count}")
    
    # عدد الطلبات
    cursor.execute("SELECT COUNT(*) FROM Orders")
    order_count = cursor.fetchone()[0]
    print(f"📦 عدد الطلبات: {order_count}")
    
    # عدد الزبائن الآجلين
    cursor.execute("SELECT COUNT(*) FROM CreditCustomers")
    credit_customer_count = cursor.fetchone()[0]
    print(f"💰 عدد الزبائن الآجلين: {credit_customer_count}")
    
    # عدد المرتجعات
    cursor.execute("SELECT COUNT(*) FROM Returns")
    return_count = cursor.fetchone()[0]
    print(f"📦 عدد المرتجعات: {return_count}")
    
    # عدد الرسائل غير المقروءة
    cursor.execute("SELECT COUNT(*) FROM Messages WHERE IsRead = 0")
    unread_messages = cursor.fetchone()[0]
    print(f"📩 الرسائل غير المقروءة: {unread_messages}")
    
    conn.close()

def reset_database():
    """إعادة تعيين قاعدة البيانات (بحذف جميع البيانات)"""
    confirmation = input("⚠️  هل أنت متأكد من حذف جميع البيانات؟ (اكتب 'نعم' للتأكيد): ")
    
    if confirmation != 'نعم':
        print("❌ تم إلغاء العملية")
        return
    
    # إنشاء نسخة احتياطية أولاً
    backup_file = backup_database()
    
    # حذف قاعدة البيانات الحالية
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("🗑️  تم حذف قاعدة البيانات القديمة")
    
    # إنشاء قاعدة بيانات جديدة
    init_db()
    
    print("🔄 تم إعادة تعيين قاعدة البيانات بنجاح")
    if backup_file:
        print(f"💾 النسخة الاحتياطية محفوظة في: {backup_file}")

def main():
    """الدالة الرئيسية"""
    print("=" * 50)
    print("🗃️  مدير قاعدة بيانات بوت المتجر")
    print("=" * 50)
    print("\nاختر الإجراء المطلوب:")
    print("1. إنشاء قاعدة البيانات (أو التحقق منها)")
    print("2. إضافة بيانات تجريبية")
    print("3. عرض إحصائيات قاعدة البيانات")
    print("4. إنشاء نسخة احتياطية")
    print("5. استعادة من نسخة احتياطية")
    print("6. إعادة تعيين قاعدة البيانات")
    print("7. الخروج")
    
    choice = input("\nاختر رقم الإجراء: ")
    
    if choice == '1':
        init_db()
        check_and_fix_db()
    elif choice == '2':
        init_db()
        add_sample_data()
    elif choice == '3':
        if os.path.exists(DB_FILE):
            show_database_stats()
        else:
            print("❌ قاعدة البيانات غير موجودة. قم بإنشائها أولاً.")
    elif choice == '4':
        backup_database()
    elif choice == '5':
        backup_files = [f for f in os.listdir(BASE_DIR) if f.startswith('store_backup_') and f.endswith('.db')]
        if backup_files:
            print("\n📁 النسخ الاحتياطية المتاحة:")
            for i, file in enumerate(sorted(backup_files, reverse=True)[:5], 1):
                print(f"{i}. {file}")
            
            file_choice = input("\nاختر رقم النسخة الاحتياطية (أو 0 للرجوع): ")
            if file_choice.isdigit() and 0 < int(file_choice) <= len(backup_files):
                backup_file = os.path.join(BASE_DIR, backup_files[int(file_choice)-1])
                restore_database(backup_file)
        else:
            print("❌ لا توجد نسخ احتياطية متاحة")
    elif choice == '6':
        reset_database()
    elif choice == '7':
        print("👋 مع السلامة!")
        return
    else:
        print("❌ اختيار غير صحيح")
    
    input("\nاضغط Enter للعودة للقائمة الرئيسية...")
    main()

if __name__ == "__main__":
    main()