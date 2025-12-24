import 'dart:io';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import 'package:image/image.dart' as img;
import 'package:uuid/uuid.dart';
import 'package:path_provider/path_provider.dart';
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
    Directory directory;
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      // 1. Check Parent (Bot Shared)
      final parentData = Directory(p.join(Directory.current.parent.path, 'data'));
      if (await parentData.exists()) {
         directory = parentData;
      } else {
         // 2. Fallback to Local
         directory = Directory(p.join(Directory.current.path, 'data'));
      }
    } else {
      directory = await getApplicationDocumentsDirectory();
    }

    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return p.join(directory.path, 'store_local_new.db');
  }

  Future<Database> _initLocalDB(String filePath) async {
    try {
      Directory directory;
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
          // Check Parent first
          final parentData = Directory(p.join(Directory.current.parent.path, 'data'));
          if (await parentData.exists()) {
             directory = parentData;
             print("📂 Using Shared Data Directory: ${directory.path}");
          } else {
             directory = Directory(p.join(Directory.current.path, 'data'));
             print("📂 Using App-Local Data Directory: ${directory.path}");
          }
      } else {
        directory = await getApplicationDocumentsDirectory();
      }

      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }
      
      final imagesDirectory = Directory(p.join(directory.path, 'Images'));
      if (!await imagesDirectory.exists()) {
        await imagesDirectory.create(recursive: true);
        print("📂 Created Images Directory at: ${imagesDirectory.path}");
      }
      
      final path = p.join(directory.path, filePath);
      print("📂 ===================================================");
      print("📂 ACTIVE DATABASE PATH: ${directory.absolute.path}");
      print("📂 ===================================================");
      


      final db = await openDatabase(
        path, 
        version: 1, 
        onCreate: _createLocalDB,
      );
      
      _localDatabase = db; // Update singleton reference immediately if valid

      // Ensure Users table exists (Migration for existing apps)
      if (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'").then((v) => v.isEmpty)) {
         await db.execute('''
           CREATE TABLE IF NOT EXISTS Users (
             UserID INTEGER PRIMARY KEY AUTOINCREMENT,
             TelegramID INTEGER UNIQUE,
             UserName TEXT,
             UserType TEXT,
             PhoneNumber TEXT,
             FullName TEXT,
             CreatedAt TEXT
           )
         ''');
         print("🛠️ Created missing Users table");
      }
      
      // Ensure DeletedSync table exists (Migration)
      if (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='DeletedSync'").then((v) => v.isEmpty)) {
         await db.execute('''
            CREATE TABLE IF NOT EXISTS DeletedSync (
              ID INTEGER PRIMARY KEY AUTOINCREMENT,
              TableName TEXT,
              RemoteID INTEGER,
              DeletedAt TEXT
            )
         ''');
         print("🛠️ Created missing DeletedSync table");
      }

      // Ensure Messages table exists (Migration)
      if (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='Messages'").then((v) => v.isEmpty)) {
         await db.execute('''
            CREATE TABLE IF NOT EXISTS Messages (
              MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
              OrderID INTEGER,
              SellerID INTEGER,
              MessageType TEXT,
              MessageText TEXT,
              IsRead INTEGER DEFAULT 0,
              CreatedAt TEXT
            )
         ''');
         print("🛠️ Created missing Messages table");
      }

      // Ensure CreditCustomers table exists (Migration)
      if (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='CreditCustomers'").then((v) => v.isEmpty)) {
         await db.execute('''
            CREATE TABLE IF NOT EXISTS CreditCustomers (
              CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
              SellerID INTEGER,
              FullName TEXT,
              PhoneNumber TEXT,
              CreatedAt TEXT
            )
         ''');
         print("🛠️ Created missing CreditCustomers table");
      }

       // Ensure CustomerCredit table exists (Migration)
      if (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='CustomerCredit'").then((v) => v.isEmpty)) {
         await db.execute('''
            CREATE TABLE IF NOT EXISTS CustomerCredit (
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
         print("🛠️ Created missing CustomerCredit table");
      }

      return db;
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

      Directory directory;
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
        // Check Parent first
        final parentImg = Directory(p.join(Directory.current.parent.path, 'data', 'Images'));
        if (await parentImg.exists()) {
           directory = parentImg;
        } else {
           directory = Directory(p.join(Directory.current.path, 'data', 'Images'));
        }
      } else {
        final docs = await getApplicationDocumentsDirectory();
        directory = Directory(p.join(docs.path, 'Images'));
      }

      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }

      // Generate UUID-based filename (Bot Style: timestamp_uuidhex.jpg)
      // Strategy: Unify naming to match Python Bot: f"{int(time.time())}_{uuid.uuid4().hex}{ext}"
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final uuidHex = const Uuid().v4().replaceAll('-', '');
      final fileName = '${timestamp}_$uuidHex.jpg';
      final newPath = p.join(directory.path, fileName);
      
      print("🔄 Processing Image: $sourcePath -> $newPath");

      // Read & Process
      final bytes = await sourceFile.readAsBytes();
      img.Image? image = img.decodeImage(bytes);
      
      if (image == null) {
          // Fallback: Just copy if decoding fails
          print("⚠️ Image decoding failed, falling back to simple copy.");
          await sourceFile.copy(newPath);
          return newPath;
      }

      // Resize: Match Telegram-ish specs (Max dim ~1280)
      // Only resize if width > 1280. 
      if (image.width > 1280) {
        image = img.copyResize(image, width: 1280);
      }

      // Encode to JPG with 85% quality
      // Note: encodeJpg returns Uint8List in newer versions or List<int> in older. 
      // check version: ^4.0.17 usually returns Uint8List.
      final jpgBytes = img.encodeJpg(image, quality: 85);
      
      final newFile = File(newPath);
      await newFile.writeAsBytes(jpgBytes);
      
      print("✅ Saved Processed Image to: $newPath");
      return newPath;
    } catch (e) {
      print("❌ Failed to save image: $e");
      // Fallback: try simple copy with new name if processing failed
      try {
         final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
         final uuidHex = const Uuid().v4().replaceAll('-', '');
         final fileName = '${timestamp}_$uuidHex.jpg';
         final newPath = p.join(Directory.current.path, 'data', 'Images', fileName);
         
         // Ensure dir exists
         final dir = Directory(p.dirname(newPath));
         if (!await dir.exists()) await dir.create(recursive: true);

         await File(sourcePath).copy(newPath);
         return newPath;
      } catch (ex) {
         return sourcePath;
      }
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

    // DeletedSync Queue
    await db.execute('''
      CREATE TABLE DeletedSync (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        TableName TEXT,
        RemoteID INTEGER,
        DeletedAt TEXT
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
    
    // Check for duplicate (Check-First can be flaky depending on transaction state, so we also Catch on Insert)
    final existing = await db.query('Sellers', where: 'TelegramID = ?', whereArgs: [telegramId]);
    if (existing.isNotEmpty) {
       throw 'المتجر بهذا المعرف (Telegram ID) مسجل مسبقاً!';
    }

    final localImagePath = await _saveImageLocally(imagePath);
    
    try {
      await db.insert('Sellers', {
        'TelegramID': telegramId,
        'StoreName': storeName,
        'UserName': userName,
        'Status': 'active',
        'ImagePath': localImagePath,
        'CreatedAt': DateTime.now().toIso8601String(),
      });
    } catch (e) {
       if (e.toString().contains('UNIQUE') || e.toString().contains('constraint')) {
          throw 'المتجر بهذا المعرف (Telegram ID) مسجل مسبقاً!';
       }
       rethrow;
    }
  }
  
  Future<void> updateSeller(Seller seller) async {
     final db = await database;
     
     // Check if image path changed? Or just always try to save?
     // If path is already in 'data/Images', _saveImageLocally will create a copy?
     // We should check if it's already local.
     // Optimization: If path starts with our data dir, skip.
     String? newPath = seller.imagePath;
     // Check if path is already in our Images folder
     // Mobile paths might be /data/user/0/.../app_flutter/Images/filename
     // Desktop paths might be C:\...\data\Images\filename
     if (seller.imagePath != null && !seller.imagePath!.contains('Images')) {
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
    if (category.imagePath != null && !category.imagePath!.contains('Images')) {
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
     
     // 1. Get Old Image Path
     final oldProductResult = await db.query('Products', columns: ['ImagePath'], where: 'ProductID = ?', whereArgs: [product.productId]);
     String? oldImagePath;
     if (oldProductResult.isNotEmpty) {
       oldImagePath = oldProductResult.first['ImagePath'] as String?;
     }

     String? newPath = product.imagePath;
     if (product.imagePath != null && !product.imagePath!.contains('Images')) {
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
     
     // 2. Delete Old Image if changed and valid
     if (oldImagePath != null && oldImagePath != newPath && oldImagePath.isNotEmpty) {
        try {
           final oldFile = File(oldImagePath);
           if (await oldFile.exists()) {
              await oldFile.delete();
              print("🗑️ Deleted old image: $oldImagePath");
           }
        } catch (e) {
           print("⚠️ Failed to delete old image: $e");
        }
     }
  }

  Future<void> deleteProduct(int productId) async {
    final db = await database;
    await db.delete('Products', where: 'ProductID = ?', whereArgs: [productId]);
  }
  
   // --- Cart ---
  Future<void> addToCart(int userId, int productId, int quantity, double price) async {
    final db = await database;
    
    // Check if exists first to increment
    final existing = await db.query('Carts', 
      columns: ['CartID', 'Quantity'], 
      where: 'UserID = ? AND ProductID = ?', 
      whereArgs: [userId, productId]
    );

    if (existing.isNotEmpty) {
      final currentQty = existing.first['Quantity'] as int;
      final cartId = existing.first['CartID'] as int;
      await db.update('Carts', {
        'Quantity': currentQty + quantity,
        'AddedAt': DateTime.now().toIso8601String()
      }, where: 'CartID = ?', whereArgs: [cartId]);
      print("🛒 Cart: Incremented Item $productId by $quantity (Total: ${currentQty + quantity})");
    } else {
      await db.insert('Carts', {
        'UserID': userId,
        'ProductID': productId,
        'Quantity': quantity,
        'Price': price,
        'AddedAt': DateTime.now().toIso8601String()
      });
      print("🛒 Cart: Added Item $productId (Qty: $quantity)");
    }
  }

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    final db = await database;
    final result = await db.rawQuery('''
      SELECT c.*, p.Name, p.ImagePath, p.SellerID, s.StoreName
      FROM Carts c
      LEFT JOIN Products p ON c.ProductID = p.ProductID
      LEFT JOIN Sellers s ON p.SellerID = s.SellerID
      WHERE c.UserID = ?
    ''', [userId]);
    
    print("🛒 Cart: Fetched ${result.length} items for User $userId");
    for (var r in result) {
       print("   - Item: ${r['Name']} (Store: ${r['StoreName']})");
    }
    return result;
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
    try {
       print('DEBUG: Starting Direct Order Insert for Seller $sellerId');
       if (items.isEmpty) throw Exception("Empty Items List");

       // 1. Insert Order
       final orderId = await db.insert('Orders', {
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
       print('DEBUG: inserted order $orderId');

       // 2. Insert Items (Directly)
       for (var item in items) {
          final productId = item['ProductID'] ?? item['productID'] ?? item['productId'];
          print('DEBUG: Inserting Item $productId');
          
          await db.insert('OrderItems', {
            'OrderID': orderId,
            'ProductID': productId,
            'Quantity': item['Quantity'],
            'Price': item['Price']
          });
       }
       
       // 3. VERIFY INSERTION IMMEDIATELY
       final countRes = await db.rawQuery('SELECT count(*) as c FROM OrderItems WHERE OrderID = ?', [orderId]);
       final count = Sqflite.firstIntValue(countRes) ?? 0;
       
       print('DEBUG: Verified $count items for Order $orderId');
       
       if (count == 0) {
          throw Exception("DB ERROR: Wrote ${items.length} items but found 0!");
       }

       print('DEBUG: Finished creating order $orderId');
       return orderId;
    } catch (e) {
      print("CRITICAL DB ERROR: $e");
      rethrow;
    }
  }
  Future<List<Map<String, dynamic>>> getItemsForOrder(int orderId) async {
    final db = await database;
    final res = await db.rawQuery('''
      SELECT oi.OrderItemID, oi.ProductID, oi.Quantity, oi.Price, p.Name, p.ImagePath 
      FROM OrderItems oi
      LEFT JOIN Products p ON oi.ProductID = p.ProductID
      WHERE oi.OrderID = ?
    ''', [orderId]);
    print("DEBUG: getItemsForOrder($orderId) returned ${res.length} rows");
    return res;
  }

  Future<void> deleteOrder(int orderId) async {
    final db = await database;
    await db.transaction((txn) async {
        // 1. Restore Stock
        final items = await txn.rawQuery("SELECT ProductID, Quantity FROM OrderItems WHERE OrderID = ?", [orderId]);
        for (var item in items) {
           final pid = item['ProductID'] as int;
           final qty = item['Quantity'] as int;
           await txn.rawUpdate("UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?", [qty, pid]);
        }
        
        // 2. Delete Remote Messages (Clean up local)
        await txn.delete('Messages', where: 'OrderID = ?', whereArgs: [orderId]);

        // 3. Delete Order & Items
        await txn.delete('Orders', where: 'OrderID = ?', whereArgs: [orderId]);
        await txn.delete('OrderItems', where: 'OrderID = ?', whereArgs: [orderId]);
        
        // 4. Track for Sync
        await txn.insert('DeletedSync', {
          'TableName': 'Orders',
          'RemoteID': orderId,
          'DeletedAt': DateTime.now().toIso8601String()
        });
    });
  }

  Future<List<Map<String, dynamic>>> getDeletedItems() async {
    final db = await database;
    return await db.query('DeletedSync');
  }

  Future<void> clearDeletedItems(List<int> ids) async {
    final db = await database;
    await db.delete('DeletedSync', where: 'ID IN (${ids.join(',')})');
  }
  
  // --- Counts for Badges ---
  Future<int> getProductsCount(int sellerId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Products WHERE SellerID = ?', [sellerId])) ?? 0;
  }
  
  Future<int> getMessagesCount(int sellerId) async {
    final db = await database;
    // Return total messages (or unread? User said "Messages 7", usually implies total or unread. Let's do Unread for utility, or Total per request).
    // Let's do Total for now as requested "Count", or specific "Unread".
    // Usually badges are unread. But let's return count of ALL for now to match "4 products, 7 messages" example.
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Messages WHERE SellerID = ?', [sellerId])) ?? 0;
  }



  // --- Stock Management ---
  Future<void> deductStockForOrder(int orderId) async {
    final db = await database;
    await db.transaction((txn) async {
      // 1. Get Order Items
      final items = await txn.rawQuery("SELECT ProductID, Quantity FROM OrderItems WHERE OrderID = ?", [orderId]);
      
      for (var item in items) {
        final productId = item['ProductID'] as int;
        final quantity = item['Quantity'] as int;
        
        // 2. Decrement Product Quantity
        await txn.rawUpdate(
          "UPDATE Products SET Quantity = Quantity - ? WHERE ProductID = ?",
          [quantity, productId]
        );
      }
    });
  }
  
  Future<int> getUnreadMessagesCount(int sellerId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Messages WHERE SellerID = ? AND IsRead = 0', [sellerId])) ?? 0;
  }

  Future<int> getCartCount(int userId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Carts WHERE UserID = ?', [userId])) ?? 0;
  }

  Future<int> getOrdersCount(int sellerId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Orders WHERE SellerID = ?', [sellerId])) ?? 0;
  }

  Future<int> getCategoriesCount(int sellerId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM Categories WHERE SellerID = ?', [sellerId])) ?? 0;
  }
  
  Future<int> getCustomersCount(int sellerId) async {
    final db = await database;
    return Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM CreditCustomers WHERE SellerID = ?', [sellerId])) ?? 0;
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

  // --- Messages ---
  Future<List<Message>> getMessages(int sellerId) async {
  final db = await database;
  // Exclude 'system' messages (Outgoing notifications) from Inbox
  final result = await db.query('Messages', 
      where: 'SellerID = ? AND (MessageType IS NULL OR MessageType != ?)', 
      whereArgs: [sellerId, 'system'],
      orderBy: 'CreatedAt DESC');
  return result.map((e) => Message.fromMap(e)).toList();
}

  Future<void> markMessageAsRead(int messageId) async {
    final db = await database;
    await db.update('Messages', {'IsRead': 1}, where: 'MessageID = ?', whereArgs: [messageId]);
  }

  Future<void> deleteMessage(int messageId) async {
    final db = await database;
    await db.delete('Messages', where: 'MessageID = ?', whereArgs: [messageId]);
  }

  Future<void> deleteMessageByOrderId(int orderId) async {
    final db = await database;
    // Delete only incoming/request messages, preserve system logs/outgoing
    await db.delete('Messages', where: 'OrderID = ? AND (MessageType IS NULL OR MessageType != ?)', whereArgs: [orderId, 'system']);
  }

  Future<void> addSystemMessage(int orderId, int buyerId, String text) async {
    final db = await database;
    // System messages: SellerID is effectively the Platform or the Seller (context dependent).
    // For Order updates, we want the Buyer to see it from the Seller.
    // We need to look up sellerId from the order if not passed
    final orderRes = await db.query('Orders', columns: ['SellerID'], where: 'OrderID = ?', whereArgs: [orderId]);
    int? sellerId;
    if (orderRes.isNotEmpty) {
       sellerId = orderRes.first['SellerID'] as int;
    }

    await db.insert('Messages', {
      'OrderID': orderId,
      'SellerID': sellerId, 
      'MessageType': 'system', 
      'MessageText': text,
      'IsRead': 0,
      'CreatedAt': DateTime.now().toIso8601String()
    });
  }

  Future<void> close() async {
    final db = _localDatabase;
    if (db != null) {
      await db.close();
      _localDatabase = null;
      print("🔒 Database Closed");
    }
  }
}
