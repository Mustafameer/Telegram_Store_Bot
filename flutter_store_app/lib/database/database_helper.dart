import 'dart:io';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import '../models/database_models.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _localDatabase;

  DatabaseHelper._init();

  Future<Database> get database async {
    if (_localDatabase != null) return _localDatabase!;
    _localDatabase = await _initLocalDB('store_local_new.db');
    return _localDatabase!;
  }

  Future<String> getDbPath() async {
    final directory = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data');
    return p.join(directory.path, 'store_local_new.db');
  }

  Future<Database> _initLocalDB(String filePath) async {
    try {
      final directory = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data');
      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }
      
      final imagesDirectory = Directory(p.join(directory.path, 'Images'));
      if (!await imagesDirectory.exists()) {
        await imagesDirectory.create(recursive: true);
        print("📂 Created Images Directory at: ${imagesDirectory.path}");
      }
      
      final path = p.join(directory.path, filePath);
      print("📂 Opening Database at: $path");

      return await openDatabase(
        path, 
        version: 1, 
        onCreate: _createLocalDB,
      );
    } catch (e) {
      print("❌ Database Init Error: $e");
      rethrow;
    }
  }

  Future<String?> _saveImageLocally(String? sourcePath) async {
    if (sourcePath == null || sourcePath.isEmpty) return null;
    try {
      final sourceFile = File(sourcePath);
      if (!await sourceFile.exists()) return null;

      final directory = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images');
      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }

      final fileName = p.basename(sourcePath);
      // Generate unique name to prevent overwrite if needed, or keep original. 
      // Using original name for now, or timestamp prefix.
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      // final extension = extension(sourcePath); // FIX: "extension" usage
      
      final newFileName = '${timestamp}_$fileName';
      final newPath = p.join(directory.path, newFileName);
      
      await sourceFile.copy(newPath);
      print("🖼️ Saved Image to: $newPath");
      return newPath;
    } catch (e) {
      print("❌ Failed to save image: $e");
      return sourcePath; // Fallback to original path if copy fails
    }
  }

  Future<void> _createLocalDB(Database db, int version) async {
    print("Creating Local DB Tables...");
    
    // Sellers
    await db.execute('''
      CREATE TABLE Sellers (
        SellerID INTEGER PRIMARY KEY AUTOINCREMENT,
        TelegramID INTEGER UNIQUE,
        UserName TEXT,
        StoreName TEXT,
        CreatedAt TEXT,
        Status TEXT DEFAULT 'active',
        ImagePath TEXT
      )
    ''');

    // Categories
    await db.execute('''
      CREATE TABLE Categories (
        CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
        SellerID INTEGER,
        Name TEXT,
        OrderIndex INTEGER DEFAULT 0,
        ImagePath TEXT
      )
    ''');

    // Products
    await db.execute('''
      CREATE TABLE Products (
        ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
        SellerID INTEGER,
        CategoryID INTEGER,
        Name TEXT,
        Description TEXT,
        Price REAL,
        WholesalePrice REAL,
        Quantity INTEGER,
        ImagePath TEXT,
        Status TEXT DEFAULT 'active'
      )
    ''');

    // Orders
    await db.execute('''
      CREATE TABLE Orders (
        OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
        BuyerID INTEGER,
        SellerID INTEGER,
        Total REAL,
        Status TEXT,
        CreatedAt TEXT,
        DeliveryAddress TEXT,
        Notes TEXT,
        PaymentMethod TEXT,
        FullyPaid INTEGER
      )
    ''');
    
    // OrderItems
    await db.execute('''
      CREATE TABLE OrderItems (
        OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
        OrderID INTEGER,
        ProductID INTEGER,
        Quantity INTEGER,
        Price REAL
      )
    ''');
    
    // Carts
    await db.execute('''
      CREATE TABLE Carts (
        CartID INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID INTEGER,
        ProductID INTEGER,
        Quantity INTEGER,
        Price REAL,
        AddedAt TEXT,
        UNIQUE(UserID, ProductID)
      )
    ''');

    // CreditCustomers
    await db.execute('''
      CREATE TABLE CreditCustomers (
        CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
        SellerID INTEGER,
        FullName TEXT,
        PhoneNumber TEXT,
        CreatedAt TEXT
      )
    ''');
    
     // CustomerCredit
     await db.execute('''
      CREATE TABLE CustomerCredit (
        CreditID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID INTEGER,
        SellerID INTEGER,
        TransactionType TEXT,
        Amount REAL,
        Description TEXT,
        BalanceBefore REAL,
        BalanceAfter REAL,
        TransactionDate TEXT
      )
    ''');
    
    // Messages
    await db.execute('''
      CREATE TABLE Messages (
        MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
        OrderID INTEGER,
        SellerID INTEGER,
        MessageType TEXT,
        MessageText TEXT,
        IsRead INTEGER DEFAULT 0,
        CreatedAt TEXT
      )
    ''');
  }

  // --- CRUD Methods (Pure Local SQLite) ---
  
  Future<List<Seller>> getAllSellers({bool forceRefresh = false}) async {
    final db = await database;
    final result = await db.query('Sellers');
    return result.map((e) => Seller.fromMap(e)).toList();
  }
  
  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    final db = await database;
    final result = await db.query('Sellers', where: 'TelegramID = ?', whereArgs: [telegramId]);
    if (result.isNotEmpty) return Seller.fromMap(result.first);
    return null;
  }
  
  Future<void> addSeller(String storeName, int telegramId, String userName, {String? imagePath}) async {
    final db = await database;
    final localImagePath = await _saveImageLocally(imagePath);
    await db.insert('Sellers', {
      'TelegramID': telegramId,
      'StoreName': storeName,
      'UserName': userName,
      'Status': 'active',
      'ImagePath': localImagePath,
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }
  
  Future<void> updateSeller(Seller seller) async {
     final db = await database;
     
     // Check if image path changed? Or just always try to save?
     // If path is already in 'data/Images', _saveImageLocally will create a copy?
     // We should check if it's already local.
     // Optimization: If path starts with our data dir, skip.
     String? newPath = seller.imagePath;
     if (seller.imagePath != null && !seller.imagePath!.contains(r'TelegramStoreBot\data\Images')) {
        newPath = await _saveImageLocally(seller.imagePath);
     }
     
     await db.update('Sellers', {
       'StoreName': seller.storeName,
       'UserName': seller.userName,
       'ImagePath': newPath,
     }, where: 'SellerID = ?', whereArgs: [seller.sellerId]);
  }

  Future<void> updateSellerStatus(int sellerId, String status) async {
    final db = await database;
     await db.update('Sellers', {
       'Status': status
     }, where: 'SellerID = ?', whereArgs: [sellerId]);
  }
  
  Future<void> deleteSeller(int sellerId) async {
     final db = await database;
     await db.delete('Sellers', where: 'SellerID = ?', whereArgs: [sellerId]);
  }

  Future<List<Category>> getCategories(int sellerId, {bool forceRefresh = false}) async {
    final db = await database;
    final result = await db.query('Categories', where: 'SellerID = ?', orderBy: 'OrderIndex', whereArgs: [sellerId]);
    return result.map((e) => Category.fromMap(e)).toList();
  }
  
   Future<void> ensureCategorySchema() async {
    // No-op for Local DB
  }

  Future<void> addCategory(Category category) async {
    final db = await database;
    final localPath = await _saveImageLocally(category.imagePath);
    await db.insert('Categories', {
      'SellerID': category.sellerId,
      'Name': category.name,
      'OrderIndex': category.orderIndex, 
      'ImagePath': localPath,
    });
  }

  Future<void> updateCategory(Category category) async {
    final db = await database;
    String? newPath = category.imagePath;
    if (category.imagePath != null && !category.imagePath!.contains(r'TelegramStoreBot\data\Images')) {
       newPath = await _saveImageLocally(category.imagePath);
    }
    await db.update('Categories', {
      'Name': category.name,
      'ImagePath': newPath,
    }, where: 'CategoryID = ?', whereArgs: [category.categoryId]);
  }
  
   Future<void> deleteCategory(int categoryId) async {
     final db = await database;
     await db.delete('Categories', where: 'CategoryID = ?', whereArgs: [categoryId]);
  }

  Future<List<Product>> getProducts(int sellerId, {int? categoryId, bool forceRefresh = false}) async {
     final db = await database;
     String where = 'SellerID = ?';
     List<dynamic> args = [sellerId];
     
     if (categoryId != null) {
       where += ' AND CategoryID = ?';
       args.add(categoryId);
     }
     
     final result = await db.query('Products', where: where, whereArgs: args);
     return result.map((e) => Product.fromMap(e)).toList();
  }

  Future<void> addProduct(Product product) async {
    final db = await database;
    final localPath = await _saveImageLocally(product.imagePath);
    await db.insert('Products', {
        'SellerID': product.sellerId,
        'CategoryID': product.categoryId,
        'Name': product.name,
        'Description': product.description,
        'Price': product.price,
        'WholesalePrice': product.wholesalePrice,
        'Quantity': product.quantity,
        'ImagePath': localPath,
        'Status': product.status,
    });
  }

  Future<void> updateProduct(Product product) async {
     final db = await database;
     String? newPath = product.imagePath;
     if (product.imagePath != null && !product.imagePath!.contains(r'TelegramStoreBot\data\Images')) {
        newPath = await _saveImageLocally(product.imagePath);
     }
     await db.update('Products', {
        'CategoryID': product.categoryId,
        'Name': product.name,
        'Description': product.description,
        'Price': product.price,
        'WholesalePrice': product.wholesalePrice,
        'Quantity': product.quantity,
        'ImagePath': newPath,
        'Status': product.status,
     }, where: 'ProductID = ?', whereArgs: [product.productId]);
  }

  Future<void> deleteProduct(int productId) async {
    final db = await database;
    await db.delete('Products', where: 'ProductID = ?', whereArgs: [productId]);
  }
  
   // --- Cart ---
  Future<void> addToCart(int userId, int productId, int quantity, double price) async {
    final db = await database;
    await db.insert('Carts', {
      'UserID': userId,
      'ProductID': productId,
      'Quantity': quantity,
      'Price': price,
      'AddedAt': DateTime.now().toIso8601String()
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    final db = await database;
    return await db.rawQuery('''
      SELECT c.*, p.Name, p.ImagePath, p.SellerID, s.StoreName
      FROM Carts c
      JOIN Products p ON c.ProductID = p.ProductID
      JOIN Sellers s ON p.SellerID = s.SellerID
      WHERE c.UserID = ?
    ''', [userId]);
  }

  Future<void> updateCartQuantity(int cartId, int quantity) async {
    final db = await database;
    if (quantity <= 0) {
      await removeFromCart(cartId);
    } else {
      await db.update('Carts', {'Quantity': quantity}, where: 'CartID = ?', whereArgs: [cartId]);
    }
  }

  Future<void> removeFromCart(int cartId) async {
    final db = await database;
    await db.delete('Carts', where: 'CartID = ?', whereArgs: [cartId]);
  }

  Future<void> clearCart(int userId) async {
    final db = await database;
    await db.delete('Carts', where: 'UserID = ?', whereArgs: [userId]);
  }


   // --- Orders --- 
  Future<List<Order>> getOrders(int sellerId) async {
     final db = await database;
     final result = await db.query('Orders', where: 'SellerID = ?', orderBy: 'CreatedAt DESC', whereArgs: [sellerId]);
     return result.map((e) => Order.fromMap(e)).toList();
  }
  
  Future<void> updateOrderStatus(int orderId, String status) async {
    final db = await database;
    await db.update('Orders', {'Status': status}, where: 'OrderID = ?', whereArgs: [orderId]);
  }
  
  Future<int> createOrder(int buyerId, int sellerId, double total, String address, String notes, List<Map<String, dynamic>> items) async {
    final db = await database;
    return await db.transaction((txn) async {
       final orderId = await txn.insert('Orders', {
         'BuyerID': buyerId,
         'SellerID': sellerId,
         'Total': total,
         'Status': 'Pending',
         'CreatedAt': DateTime.now().toIso8601String(),
         'DeliveryAddress': address,
         'Notes': notes,
         'PaymentMethod': 'cash',
         'FullyPaid': 0
       });
       
       for (var item in items) {
          await txn.insert('OrderItems', {
            'OrderID': orderId,
            'ProductID': item['ProductID'],
            'Quantity': item['Quantity'],
            'Price': item['Price']
          });
       }
       return orderId;
    });
  }
  
  // Messages
  Future<void> addMessage(int orderId, int sellerId, String messageType, String messageText) async {
    final db = await database;
    await db.insert('Messages', {
      'OrderID': orderId,
      'SellerID': sellerId,
      'MessageType': messageType,
      'MessageText': messageText,
      'IsRead': 0,
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }
  
  // Credit Customers
  Future<List<CreditCustomer>> getCreditCustomers(int sellerId) async {
    final db = await database;
    final result = await db.query('CreditCustomers', where: 'SellerID = ?', orderBy: 'FullName', whereArgs: [sellerId]);
    return result.map((e) => CreditCustomer.fromMap(e)).toList();
  }

  Future<int?> addCreditCustomer(int sellerId, String fullName, String phoneNumber) async {
    final db = await database;
    return await db.insert('CreditCustomers', {
      'SellerID': sellerId,
      'FullName': fullName,
      'PhoneNumber': phoneNumber,
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }

  Future<List<CustomerCreditTransaction>> getCustomerTransactions(int customerId) async {
     final db = await database;
     final result = await db.query('CustomerCredit', where: 'CustomerID = ?', orderBy: 'TransactionDate DESC', whereArgs: [customerId]);
     return result.map((e) => CustomerCreditTransaction.fromMap(e)).toList();
  }

  Future<void> addCreditTransaction({
    required int customerId,
    required int sellerId,
    required String transactionType, 
    required double amount,
    String? description,
  }) async {
    final db = await database;
    await db.transaction((txn) async {
       // Get balance
       final balanceRes = await txn.query('CustomerCredit', 
        where: 'CustomerID = ?', 
        orderBy: 'CreditID DESC', 
        limit: 1, 
        whereArgs: [customerId]
       );
       
       double currentBalance = 0.0;
       if (balanceRes.isNotEmpty) {
         currentBalance = (balanceRes.first['BalanceAfter'] as num).toDouble();
       }
       
       double newBalance = currentBalance;
       if (transactionType == 'credit') {
         newBalance += amount;
       } else if (transactionType == 'payment') {
         newBalance -= amount;
       }
       
       await txn.insert('CustomerCredit', {
         'CustomerID': customerId,
         'SellerID': sellerId,
         'TransactionType': transactionType,
         'Amount': amount,
         'Description': description,
         'BalanceBefore': currentBalance,
         'BalanceAfter': newBalance,
         'TransactionDate': DateTime.now().toIso8601String()
       });
    });
  }
}
