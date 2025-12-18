import 'dart:io';
import 'package:postgres/postgres.dart';
import 'package:path/path.dart' as p;
import 'package:image/image.dart' as img;
import 'package:uuid/uuid.dart';
import '../models/database_models.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  Connection? _connection;

  // Cloud Postgres Credentials (Railway)
  static const String _host = 'switchback.proxy.rlwy.net';
  static const int _port = 20266;
  static const String _databaseName = 'railway';
  static const String _username = 'postgres';
  static const String _password = 'bqcTJxNXLgwOftDoarrtmjmjYWurEIEh';

  DatabaseHelper._init();

  Future<Connection> get database async {
    if (_connection != null && _connection!.isOpen) return _connection!;
    _connection = await _initCloudDB();
    return _connection!;
  }

  Future<Connection> _initCloudDB() async {
    try {
      print("🔌 Connecting to Cloud PostgreSQL (Railway)...");
      final endpoint = Endpoint(
        host: _host,
        port: _port,
        database: _databaseName,
        username: _username,
        password: _password,
      );
      
      final conn = await Connection.open(endpoint, settings: ConnectionSettings(sslMode: SslMode.disable));
      print("✅ Connected to Cloud PostgreSQL!");

      // Note: We do NOT create tables here usually, as Bot manages Schema.
      // But keeping it harmless if they exist.
      await _createTablesIfNotExist(conn);
      return conn;
    } catch (e) {
      print("❌ Cloud Database Init Error: $e");
      rethrow;
    }
  }
  
  // Create Tables (Postgres Syntax)
  Future<void> _createTablesIfNotExist(Connection conn) async {
    // Sellers
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Sellers (
        SellerID SERIAL PRIMARY KEY,
        TelegramID BIGINT UNIQUE,
        UserName TEXT,
        StoreName TEXT,
        CreatedAt TIMESTAMP,
        Status TEXT DEFAULT 'active',
        ImagePath TEXT
      )
    ''');

    // Categories
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Categories (
        CategoryID SERIAL PRIMARY KEY,
        SellerID INTEGER,
        Name TEXT,
        OrderIndex INTEGER DEFAULT 0,
        ImagePath TEXT
      )
    ''');

    // Products
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Products (
        ProductID SERIAL PRIMARY KEY,
        SellerID INTEGER,
        CategoryID INTEGER,
        Name TEXT,
        Description TEXT,
        Price DOUBLE PRECISION,
        WholesalePrice DOUBLE PRECISION,
        Quantity INTEGER,
        ImagePath TEXT,
        Status TEXT DEFAULT 'active'
      )
    ''');

    // Orders
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Orders (
        OrderID SERIAL PRIMARY KEY,
        BuyerID BIGINT,
        SellerID INTEGER,
        Total DOUBLE PRECISION,
        Status TEXT,
        CreatedAt TIMESTAMP,
        DeliveryAddress TEXT,
        Notes TEXT,
        PaymentMethod TEXT,
        FullyPaid INTEGER
      )
    ''');
    
    // OrderItems
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS OrderItems (
        OrderItemID SERIAL PRIMARY KEY,
        OrderID INTEGER,
        ProductID INTEGER,
        Quantity INTEGER,
        Price DOUBLE PRECISION
      )
    ''');
    
    // Carts
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Carts (
        CartID SERIAL PRIMARY KEY,
        UserID BIGINT,
        ProductID INTEGER,
        Quantity INTEGER,
        Price DOUBLE PRECISION,
        AddedAt TIMESTAMP,
        UNIQUE(UserID, ProductID)
      )
    ''');

    // CreditCustomers
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS CreditCustomers (
        CustomerID SERIAL PRIMARY KEY,
        SellerID INTEGER,
        FullName TEXT,
        PhoneNumber TEXT,
        CreatedAt TIMESTAMP
      )
    ''');
    
    // CustomerCredit
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS CustomerCredit (
        CreditID SERIAL PRIMARY KEY,
        CustomerID INTEGER,
        SellerID INTEGER,
        TransactionType TEXT,
        Amount DOUBLE PRECISION,
        Description TEXT,
        BalanceBefore DOUBLE PRECISION,
        BalanceAfter DOUBLE PRECISION,
        TransactionDate TIMESTAMP
      )
    ''');
    
    // Messages
    await conn.execute('''
      CREATE TABLE IF NOT EXISTS Messages (
        MessageID SERIAL PRIMARY KEY,
        OrderID INTEGER,
        SellerID INTEGER,
        MessageType TEXT,
        MessageText TEXT,
        IsRead INTEGER DEFAULT 0,
        CreatedAt TIMESTAMP
      )
    ''');
  }

  Future<String?> _saveImageLocally(String? sourcePath) async {
    if (sourcePath == null || sourcePath.isEmpty) return null;
    // Check if valid URL or valid path
    bool isUrl = sourcePath.startsWith('http');
    bool isFile = await File(sourcePath).exists();
    if (!isFile && !isUrl) return sourcePath; // Return as is if not valid file to process

    try {
      final directory = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images');
      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }

      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final uuidHex = const Uuid().v4().replaceAll('-', '');
      final fileName = '${timestamp}_$uuidHex.jpg';
      final newPath = p.join(directory.path, fileName);
      
      final sourceFile = File(sourcePath);
      await sourceFile.copy(newPath);
      return newPath;
    } catch (e) {
      print("❌ Failed to save image: $e");
      return sourcePath;
    }
  }

  // --- CRUD Methods (PostgreSQL) ---
  
  Future<List<Seller>> getAllSellers({bool forceRefresh = false}) async {
    final conn = await database;
    final result = await conn.execute('SELECT * FROM Sellers');
    return result.map((row) => Seller.fromMap(row.toColumnMap())).toList();
  }
  
  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    final conn = await database;
    final result = await conn.execute(Sql.named('SELECT * FROM Sellers WHERE TelegramID = @id'), parameters: {'id': telegramId});
    if (result.isNotEmpty) return Seller.fromMap(result.first.toColumnMap());
    return null;
  }
  
  Future<void> addSeller(String storeName, int telegramId, String userName, {String? imagePath}) async {
    final conn = await database;
    final localImagePath = await _saveImageLocally(imagePath);
    await conn.execute(
      Sql.named('''
        INSERT INTO Sellers (TelegramID, StoreName, UserName, Status, ImagePath, CreatedAt)
        VALUES (@tid, @name, @user, 'active', @img, @date)
      '''),
      parameters: {
        'tid': telegramId,
        'name': storeName,
        'user': userName,
        'img': localImagePath,
        'date': DateTime.now().toIso8601String() // Postgres can interpret ISO string as Timestamp
      }
    );
  }
  
  Future<void> updateSeller(Seller seller) async {
     final conn = await database;
     String? newPath = seller.imagePath;
     if (seller.imagePath != null && !seller.imagePath!.contains(r'TelegramStoreBot\data\Images')) {
        newPath = await _saveImageLocally(seller.imagePath);
     }
     
     await conn.execute(
       Sql.named('UPDATE Sellers SET StoreName=@name, UserName=@user, ImagePath=@img WHERE SellerID=@id'),
       parameters: {
         'name': seller.storeName,
         'user': seller.userName,
         'img': newPath,
         'id': seller.sellerId
       }
     );
  }

  Future<void> updateSellerStatus(int sellerId, String status) async {
    final conn = await database;
    await conn.execute(
       Sql.named('UPDATE Sellers SET Status=@status WHERE SellerID=@id'),
       parameters: {'status': status, 'id': sellerId}
    );
  }
  
  Future<void> deleteSeller(int sellerId) async {
     final conn = await database;
     await conn.execute(Sql.named('DELETE FROM Sellers WHERE SellerID=@id'), parameters: {'id': sellerId});
  }

  Future<List<Category>> getCategories(int sellerId, {bool forceRefresh = false}) async {
    final conn = await database;
    final result = await conn.execute(
       Sql.named('SELECT * FROM Categories WHERE SellerID=@id ORDER BY OrderIndex'),
       parameters: {'id': sellerId}
    );
    return result.map((e) => Category.fromMap(e.toColumnMap())).toList();
  }

  Future<void> addCategory(int sellerId, String name) async {
    final conn = await database;
    await conn.execute(
      Sql.named('INSERT INTO Categories (SellerID, Name) VALUES (@sid, @name)'),
      parameters: {'sid': sellerId, 'name': name}
    );
  }

  Future<void> updateCategory(Category category) async {
    final conn = await database;
    await conn.execute(
      Sql.named('UPDATE Categories SET Name=@name WHERE CategoryID=@id'),
      parameters: {'name': category.name, 'id': category.categoryId}
    );
  }

  Future<void> deleteCategory(int categoryId) async {
    final conn = await database;
    await conn.execute(Sql.named('DELETE FROM Categories WHERE CategoryID=@id'), parameters: {'id': categoryId});
    // In Postgres, logic cascades usually handle products, but here we do manually or just unlink
  }

  Future<List<Product>> getProducts(int sellerId, {bool forceRefresh = false}) async {
    final conn = await database;
    final result = await conn.execute(
       Sql.named('SELECT * FROM Products WHERE SellerID=@id'),
       parameters: {'id': sellerId}
    );
    return result.map((e) => Product.fromMap(e.toColumnMap())).toList();
  }

  Future<void> addProduct(Product product) async {
    final conn = await database;
    final newPath = await _saveImageLocally(product.imagePath);
    await conn.execute(
      Sql.named('''
        INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
        VALUES (@sid, @cid, @name, @desc, @price, @wprice, @qty, @img, 'active')
      '''),
      parameters: {
        'sid': product.sellerId,
        'cid': product.categoryId,
        'name': product.name,
        'desc': product.description,
        'price': product.price,
        'wprice': product.wholesalePrice,
        'qty': product.quantity,
        'img': newPath
      }
    );
  }

  Future<void> updateProduct(Product product) async {
    final conn = await database;
    
    // Logic to delete old image if replaced is good, but for now just update path
    String? newPath = product.imagePath;
    if (product.imagePath != null && !product.imagePath!.contains(r'TelegramStoreBot\data\Images')) {
       newPath = await _saveImageLocally(product.imagePath);
    }

    await conn.execute(
      Sql.named('''
        UPDATE Products SET 
        Name=@name, Description=@desc, Price=@price, WholesalePrice=@wprice, 
        Quantity=@qty, ImagePath=@img, CategoryID=@cid 
        WHERE ProductID=@id
      '''),
      parameters: {
        'name': product.name,
        'desc': product.description,
        'price': product.price,
        'wprice': product.wholesalePrice,
        'qty': product.quantity,
        'img': newPath,
        'cid': product.categoryId,
        'id': product.productId
      }
    );
  }

  Future<void> deleteProduct(int productId) async {
    final conn = await database;
    await conn.execute(Sql.named('DELETE FROM Products WHERE ProductID=@id'), parameters: {'id': productId});
  }

  // --- Orders ---
  Future<List<Order>> getOrders(int sellerId) async {
    final conn = await database;
    final result = await conn.execute(
       Sql.named('SELECT * FROM Orders WHERE SellerID=@id ORDER BY CreatedAt DESC'),
       parameters: {'id': sellerId}
    );
    return result.map((e) => Order.fromMap(e.toColumnMap())).toList();
  }
  
  // Method to manually execute SQL (for SyncService)
  Future<Result> execute(String sql, {Map<String, dynamic>? parameters}) async {
    final conn = await database;
    if (parameters != null) {
       return await conn.execute(Sql.named(sql), parameters: parameters);
    }
    return await conn.execute(sql);
  }
  
  // Close
  Future<void> close() async {
    if (_connection != null) {
      await _connection!.close();
      _connection = null;
    }
  }

  // Add more methods as required for Carts, Credits, Messages...
  // Basic Setup for Migration Complete.
}
