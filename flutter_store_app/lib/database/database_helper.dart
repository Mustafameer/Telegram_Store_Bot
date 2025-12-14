
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../models/database_models.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _database;

  DatabaseHelper._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('store.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    sqfliteFfiInit();
    var databaseFactory = databaseFactoryFfi;
    
    // Logic to find the database file. 
    // Since the app is in `flutter_store_app` and db is in `TelegramStoreBot/data` (parent/data),
    // we look one level up then into data.
    
    // Try to locate the file safely
    String dbPath = p.join(Directory.current.parent.path, 'data', 'store.db');
    
    if (!File(dbPath).existsSync()) {
      // Fallback: Try absolute path if we know it (from context)
       if (File(p.join(Directory.current.path, 'data', 'store.db')).existsSync()) {
         dbPath = p.join(Directory.current.path, 'data', 'store.db');
       } else {
         // Harcoded path specific to this user's request context
         dbPath = r'c:\Users\Hp\Desktop\TelegramStoreBot\data\store.db';
       }
    }

    // ignore: avoid_print
    print("Opening database at: $dbPath");

    return await databaseFactory.openDatabase(
      dbPath,
      options: OpenDatabaseOptions(
        version: 1,
        // We do not want to onCreate because the DB should exist.
        // But if it doesn't, we might need to initialize it (though user said same DB)
        onOpen: (db) {
          // ignore: avoid_print
          print("Database opened successfully");
        },
      ),
    );
  }

  // --- Users ---
  Future<List<User>> getAllUsers() async {
    final db = await database;
    final result = await db.query('Users');
    return result.map((json) => User.fromMap(json)).toList();
  }

  // --- Sellers ---
  Future<List<Seller>> getAllSellers() async {
    final db = await database;
    final result = await db.query('Sellers');
    return result.map((json) => Seller.fromMap(json)).toList();
  }

    // --- Categories ---
  Future<List<Category>> getCategories(int sellerId) async {
    final db = await database;
    final result = await db.query(
      'Categories',
      where: 'SellerID = ?',
      whereArgs: [sellerId],
      orderBy: 'OrderIndex',
    );
    return result.map((json) => Category.fromMap(json)).toList();
  }

  // --- Login Helpers ---
  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    final db = await database;
    final result = await db.query(
      'Sellers',
      where: 'TelegramID = ?',
      whereArgs: [telegramId],
    );
    if (result.isNotEmpty) {
      return Seller.fromMap(result.first);
    }
    return null;
  }

  // --- Seller Management (Admin) ---
  Future<void> updateSellerStatus(int sellerId, String status) async {
    final db = await database;
    await db.update(
      'Sellers',
      {'Status': status},
      where: 'SellerID = ?',
      whereArgs: [sellerId],
    );
  }

  Future<void> addSeller(String storeName, int telegramId, String userName) async {
    final db = await database;
    await db.insert('Sellers', {
      'TelegramID': telegramId,
      'StoreName': storeName,
      'UserName': userName,
      'Status': 'active',
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }

  // --- Products ---
  Future<List<Product>> getProducts(int sellerId, {int? categoryId}) async {
    final db = await database;
    String where = 'SellerID = ?';
    List<dynamic> args = [sellerId];

    if (categoryId != null) {
      where += ' AND CategoryID = ?';
      args.add(categoryId);
    }

    final result = await db.query(
      'Products',
      where: where,
      whereArgs: args,
    );
    return result.map((json) => Product.fromMap(json)).toList();
  }

  Future<void> addProduct(Product product) async {
    final db = await database;
    await db.insert(
      'Products',
      {
        'SellerID': product.sellerId,
        'CategoryID': product.categoryId,
        'Name': product.name,
        'Description': product.description,
        'Price': product.price,
        'WholesalePrice': product.wholesalePrice,
        'Quantity': product.quantity,
        'ImagePath': product.imagePath,
        'Status': product.status,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
  
  Future<void> updateProduct(Product product) async {
    final db = await database;
    await db.update(
      'Products',
      {
        'CategoryID': product.categoryId,
        'Name': product.name,
        'Description': product.description,
        'Price': product.price,
        'WholesalePrice': product.wholesalePrice,
        'Quantity': product.quantity,
        'ImagePath': product.imagePath,
        'Status': product.status,
      },
      where: 'ProductID = ?',
      whereArgs: [product.productId],
    );
  }

  Future<void> deleteProduct(int productId) async {
    final db = await database;
    await db.delete(
      'Products',
      where: 'ProductID = ?',
      whereArgs: [productId],
    );
  }

  // --- Categories Management (Seller) ---
  Future<void> addCategory(Category category) async {
    final db = await database;
    await db.insert('Categories', {
      'SellerID': category.sellerId,
      'Name': category.name,
      'OrderIndex': category.orderIndex
    });
  }

  Future<void> updateCategory(Category category) async {
    final db = await database;
    await db.update(
      'Categories',
      {'Name': category.name},
      where: 'CategoryID = ?',
      whereArgs: [category.categoryId],
    );
  }

  Future<void> deleteCategory(int categoryId) async {
    final db = await database;
    await db.delete(
      'Categories',
      where: 'CategoryID = ?',
      whereArgs: [categoryId],
    );
  }

  // --- Orders ---
  Future<List<Order>> getOrders(int sellerId) async {
    final db = await database;
    final result = await db.query(
      'Orders',
      where: 'SellerID = ?',
      whereArgs: [sellerId],
      orderBy: 'CreatedAt DESC',
    );
    return result.map((json) => Order.fromMap(json)).toList();
  }

  Future<void> updateOrderStatus(int orderId, String status) async {
    final db = await database;
    await db.update(
      'Orders',
      {'Status': status},
      where: 'OrderID = ?',
      whereArgs: [orderId],
    );
  }
  
  // --- Messages ---
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

  // --- Cart ---
  // Simple cart implementation: Using the existing Carts table
  // But we need a way to identify the "current user" of the desktop app if acting as buyer.
  // We can use a special UserID or just the logged in UserID.

  Future<void> addToCart(int userId, int productId, int quantity, double price) async {
    final db = await database;
    await db.insert(
      'Carts',
      {
        'UserID': userId,
        'ProductID': productId,
        'Quantity': quantity,
        'Price': price,
        'AddedAt': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
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
      await db.update(
        'Carts',
        {'Quantity': quantity},
        where: 'CartID = ?',
        whereArgs: [cartId],
      );
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

  // --- Create Order ---
  Future<int> createOrder(int buyerId, int sellerId, double total, String address, String notes, List<Map<String, dynamic>> items) async {
    final db = await database;
    return await db.transaction((txn) async {
      final orderId = await txn.insert('Orders', {
        'BuyerID': buyerId,
        'SellerID': sellerId,
        'Total': total,
        'Status': 'Pending',
        'CreatedAt': DateTime.now().toString(), // Format like SQLite default
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
          'Price': item['Price'],
        });
      }
      return orderId;
    });
  }
}
