import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:postgres/postgres.dart' as postgres;
import 'dart:typed_data';
import '../models/database_models.dart';

/// خدمة الاتصال ببقاعدة بيانات PostgreSQL السحابية
/// يستخدم مكتبة postgres للـ Dart
class PostgresService {
  static final PostgresService _instance = PostgresService._internal();
  
  postgres.Connection? _connection;
  bool _isConnected = false;
  
  String _host = 'switchback.proxy.rlwy.net';
  int _port = 20266;
  String _database = 'railway';
  String _username = 'postgres';
  String _password = '';
  bool _useSSL = true;

  factory PostgresService() {
    return _instance;
  }

  PostgresService._internal();

  /// Initialize the connection with Railway credentials
  Future<void> initialize() async {
    try {
      final databaseUrl = dotenv.env['DATABASE_URL'];
      
      if (databaseUrl != null && databaseUrl.isNotEmpty) {
        _parseConnectionString(databaseUrl);
      } else {
        _host = dotenv.env['DB_HOST'] ?? 'switchback.proxy.rlwy.net';
        _port = int.tryParse(dotenv.env['DB_PORT'] ?? '20266') ?? 20266;
        _database = dotenv.env['DB_NAME'] ?? 'railway';
        _username = dotenv.env['DB_USER'] ?? 'postgres';
        _password = dotenv.env['DB_PASSWORD'] ?? '';
        _useSSL = (dotenv.env['DB_SSL'] ?? 'true').toLowerCase() == 'true';
      }

      await _connect();
      print('✅ PostgreSQL connection initialized');
    } catch (e) {
      print('❌ Failed to initialize PostgreSQL: $e');
      rethrow;
    }
  }

  void _parseConnectionString(String connectionString) {
    try {
      Uri uri = Uri.parse(connectionString);
      
      _username = uri.userInfo.split(':')[0];
      _password = uri.userInfo.split(':')[1];
      _host = uri.host;
      _port = uri.port;
      _database = uri.path.replaceFirst('/', '');
      _useSSL = uri.queryParameters['sslmode'] == 'require';
      
      print('📡 Parsed PostgreSQL URL:');
      print('   Host: $_host');
      print('   Port: $_port');
      print('   Database: $_database');
      print('   User: $_username');
      print('   SSL: $_useSSL');
    } catch (e) {
      print('❌ Error parsing connection string: $e');
      throw Exception('Invalid DATABASE_URL format');
    }
  }

  Future<void> _connect() async {
    try {
      _connection = await postgres.Connection.open(
        postgres.Endpoint(
          host: _host,
          port: _port,
          database: _database,
          username: _username,
          password: _password,
        ),
        settings: postgres.ConnectionSettings(
          sslMode: _useSSL ? postgres.SslMode.require : postgres.SslMode.disable,
        ),
      );
      
      _isConnected = true;
      print('✅ Connected to PostgreSQL Cloud Database');
    } catch (e) {
      _isConnected = false;
      print('❌ Connection failed: $e');
      rethrow;
    }
  }

  bool get isConnected => _isConnected;

  Future<void> _ensureConnection() async {
    if (!_isConnected || _connection == null) {
      try {
        await _connect();
      } catch (e) {
        print('❌ Failed to reconnect: $e');
        rethrow;
      }
    }
  }

  // ==================== Seller Functions ====================

  Future<Seller?> getSellerByTelegram(int telegramId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM sellers WHERE "telegramid" = \$1',
        parameters: [telegramId],
      );
      
      if (results.isEmpty) return null;
      
      final row = results.first.toColumnMap();
      return Seller(
        sellerId: row['sellerid'] as int,
        telegramId: row['telegramid'] as int,
        userName: row['username'] as String?,
        storeName: row['storename'] as String?,
        status: row['status'] as String?,
        imagePath: row['imagepath'] as String?,
        requireCustomerRegistration: (row['requirecustomerregistration'] as int?) == 1,
      );
    } catch (e) {
      print('❌ Error getting seller: $e');
      return null;
    }
  }

  Future<int?> createSeller({
    required int telegramId,
    required String storeName,
    String? userName,
    String? imagePath,
    bool requireCustomerRegistration = false,
  }) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO sellers ("telegramid", "storename", "username", "imagepath", "requirecustomerregistration", "status")
           VALUES (\$1, \$2, \$3, \$4, \$5, \$6)
           RETURNING "sellerid"''',
        parameters: [
          telegramId,
          storeName,
          userName,
          imagePath,
          requireCustomerRegistration ? 1 : 0,
          'active',
        ],
      );
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        return map['sellerid'] as int;
      }
      return null;
    } catch (e) {
      print('❌ Error creating seller: $e');
      return null;
    }
  }

  // ==================== Category Functions ====================

  Future<List<Category>> getCategories(int sellerId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM categories WHERE "sellerid" = \$1 ORDER BY "orderindex"',
        parameters: [sellerId],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return Category(
          categoryId: map['categoryid'] as int,
          sellerId: map['sellerid'] as int,
          name: map['name'] as String,
          orderIndex: map['orderindex'] as int? ?? 0,
          imagePath: map['imagepath'] as String?,
        );
      }).toList();
    } catch (e) {
      print('❌ Error getting categories: $e');
      return [];
    }
  }

  Future<Category?> getCategoryById(int categoryId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM categories WHERE "categoryid" = \$1',
        parameters: [categoryId],
      );
      
      if (results.isEmpty) return null;
      
      final map = results.first.toColumnMap();
      return Category(
        categoryId: map['categoryid'] as int,
        sellerId: map['sellerid'] as int,
        name: map['name'] as String,
        orderIndex: map['orderindex'] as int? ?? 0,
        imagePath: map['imagepath'] as String?,
      );
    } catch (e) {
      print('❌ Error getting category: $e');
      return null;
    }
  }

  // ==================== Product Functions ====================

  Future<List<Product>> getProducts(int sellerId, [int? categoryId]) async {
    try {
      await _ensureConnection();
      
      late final List<postgres.ResultRow> results;
      
      if (categoryId != null) {
        results = await _connection!.execute(
          'SELECT * FROM products WHERE "sellerid" = \$1 AND "categoryid" = \$2 ORDER BY "productid"',
          parameters: [sellerId, categoryId],
        );
      } else {
        results = await _connection!.execute(
          'SELECT * FROM products WHERE "sellerid" = \$1 ORDER BY "productid"',
          parameters: [sellerId],
        );
      }
      
      return results.map((row) {
        final map = row.toColumnMap();
        return Product(
          productId: map['productid'] as int,
          sellerId: map['sellerid'] as int,
          categoryId: map['categoryid'] as int?,
          name: map['name'] as String,
          description: map['description'] as String?,
          price: (map['price'] as num).toDouble(),
          wholesalePrice: map['wholesaleprice'] != null ? (map['wholesaleprice'] as num).toDouble() : null,
          quantity: map['quantity'] as int,
          imagePath: map['imagepath'] as String?,
          status: map['status'] as String? ?? 'active',
        );
      }).toList();
    } catch (e) {
      print('❌ Error getting products: $e');
      return [];
    }
  }

  Future<Product?> getProductById(int productId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM products WHERE "productid" = \$1',
        parameters: [productId],
      );
      
      if (results.isEmpty) return null;
      
      final map = results.first.toColumnMap();
      return Product(
        productId: map['productid'] as int,
        sellerId: map['sellerid'] as int,
        categoryId: map['categoryid'] as int?,
        name: map['name'] as String,
        description: map['description'] as String?,
        price: (map['price'] as num).toDouble(),
        wholesalePrice: map['wholesaleprice'] != null ? (map['wholesaleprice'] as num).toDouble() : null,
        quantity: map['quantity'] as int,
        imagePath: map['imagepath'] as String?,
        status: map['status'] as String? ?? 'active',
      );
    } catch (e) {
      print('❌ Error getting product: $e');
      return null;
    }
  }

  // ==================== Product Images Functions ====================

  Future<List<Map<String, dynamic>>> getProductImages(int productId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT "imageid", "productid", "imagepath" FROM "productimages" WHERE "productid" = \$1 ORDER BY "imageid"',
        parameters: [productId],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return {
          'imageid': map['imageid'],
          'productid': map['productid'],
          'imagepath': map['imagepath'],
        };
      }).toList();
    } catch (e) {
      print('❌ Error getting product images: $e');
      return [];
    }
  }

  // جديد: تحميل بيانات الصور من ImageStorage
  Future<Uint8List?> getImageData(String fileName) async {
    try {
      await _ensureConnection();
      
      print('🔍 [DEBUG] Searching for image: $fileName');
      
      final results = await _connection!.execute(
        'SELECT "filedata" FROM "imagestorage" WHERE "filename" = \$1',
        parameters: [fileName],
      );
      
      print('🔍 [DEBUG] Query returned ${results.length} results');
      
      if (results.isEmpty) {
        print('⚠️ [DEBUG] No image found with name: $fileName');
        return null;
      }
      
      final row = results.first.toColumnMap();
      final fileData = row['filedata'];
      
      print('✅ [DEBUG] Found image data, type: ${fileData.runtimeType}, size: ${fileData.toString().length} bytes');

      if (fileData is Uint8List) {
        print('✅ [DEBUG] Data is Uint8List, returning directly');
        return fileData;
      } else if (fileData is List) {
        print('✅ [DEBUG] Data is List, converting to Uint8List');
        return Uint8List.fromList(List<int>.from(fileData));
      }
      print('❌ [DEBUG] Data is unknown type: ${fileData.runtimeType}');
      return null;
    } catch (e) {
      print('❌ Error getting image data: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> getProductImagesForOrder(int productId, int quantity) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT "imageid", "productid", "imagepath" FROM "productimages" WHERE "productid" = \$1 ORDER BY "imageid" LIMIT \$2',
        parameters: [productId, quantity],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return {
          'imageid': map['imageid'],
          'productid': map['productid'],
          'imagepath': map['imagepath'],
        };
      }).toList();
    } catch (e) {
      print('❌ Error getting product images for order: $e');
      return [];
    }
  }

  // ==================== Order Functions ====================

  Future<List<Order>> getUserOrders(int buyerId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM Orders WHERE "buyerid" = \$1 ORDER BY "createdat" DESC',
        parameters: [buyerId],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return Order(
          orderId: map['orderid'] as int,
          buyerId: map['buyerid'] as int?,
          sellerId: map['sellerid'] as int,
          total: (map['total'] as num).toDouble(),
          status: map['status'] as String,
          createdAt: map['createdat'] as String,
          deliveryAddress: map['deliveryaddress'] as String?,
          notes: map['notes'] as String?,
          paymentMethod: map['paymentmethod'] as String? ?? 'cash',
          fullyPaid: (map['fullypaid'] as int?) == 1,
        );
      }).toList();
    } catch (e) {
      print('❌ Error getting user orders: $e');
      return [];
    }
  }

  Future<Order?> getOrderById(int orderId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM Orders WHERE "orderid" = \$1',
        parameters: [orderId],
      );
      
      if (results.isEmpty) return null;
      
      final map = results.first.toColumnMap();
      return Order(
        orderId: map['orderid'] as int,
        buyerId: map['buyerid'] as int?,
        sellerId: map['sellerid'] as int,
        total: (map['total'] as num).toDouble(),
        status: map['status'] as String,
        createdAt: map['createdat'] as String,
        deliveryAddress: map['deliveryaddress'] as String?,
        notes: map['notes'] as String?,
        paymentMethod: map['paymentmethod'] as String? ?? 'cash',
        fullyPaid: (map['fullypaid'] as int?) == 1,
      );
    } catch (e) {
      print('❌ Error getting order: $e');
      return null;
    }
  }

  Future<int?> createOrder({
    required int? buyerId,
    required int sellerId,
    required double total,
    required String status,
    required String paymentMethod,
    String? deliveryAddress,
    String? notes,
    bool fullyPaid = false,
  }) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO Orders ("buyerid", "sellerid", "total", "status", "createdat", "paymentmethod", "deliveryaddress", "notes", "fullypaid")
           VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9)
           RETURNING "orderid"''',
        parameters: [
          buyerId,
          sellerId,
          total,
          status,
          DateTime.now().toIso8601String(),
          paymentMethod,
          deliveryAddress,
          notes,
          fullyPaid ? 1 : 0,
        ],
      );
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        return map['orderid'] as int;
      }
      return null;
    } catch (e) {
      print('❌ Error creating order: $e');
      return null;
    }
  }

  Future<bool> addOrderItem({
    required int orderId,
    required int productId,
    required int quantity,
    required double price,
  }) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        '''INSERT INTO OrderItems ("orderid", "productid", "quantity", "price")
           VALUES (\$1, \$2, \$3, \$4)''',
        parameters: [orderId, productId, quantity, price],
      );
      
      return true;
    } catch (e) {
      print('❌ Error adding order item: $e');
      return false;
    }
  }

  Future<int?> addProduct({
    required int sellerId,
    int? categoryId,
    required String name,
    String? description,
    required double price,
    double? wholesalePrice,
    required int quantity,
    String? imagePath,
    String status = 'active',
  }) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO products ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
           VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9)
           RETURNING "productid"''',
        parameters: [
          sellerId,
          categoryId,
          name,
          description,
          price,
          wholesalePrice,
          quantity,
          imagePath,
          status,
        ],
      );
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        return map['productid'] as int;
      }
      return null;
    } catch (e) {
      print('❌ Error adding product: $e');
      return null;
    }
  }

  Future<bool> updateProduct(Product product) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        '''UPDATE products SET "sellerid" = \$1, "categoryid" = \$2, "name" = \$3, "description" = \$4, 
           "price" = \$5, "wholesaleprice" = \$6, "quantity" = \$7, "imagepath" = \$8, "status" = \$9
           WHERE "productid" = \$10''',
        parameters: [
          product.sellerId,
          product.categoryId,
          product.name,
          product.description,
          product.price,
          product.wholesalePrice,
          product.quantity,
          product.imagePath,
          product.status,
          product.productId,
        ],
      );
      
      return true;
    } catch (e) {
      print('❌ Error updating product: $e');
      return false;
    }
  }

  Future<bool> deleteProduct(int productId) async {
    try {
      await _ensureConnection();
      
      // First delete related images
      await _connection!.execute(
        'DELETE FROM "productimages" WHERE "productid" = \$1',
        parameters: [productId],
      );
      
      // Then delete the product
      await _connection!.execute(
        'DELETE FROM products WHERE "productid" = \$1',
        parameters: [productId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error deleting product: $e');
      return false;
    }
  }

  Future<bool> updateProductQuantity(int productId, int decrementBy) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'UPDATE Products SET "quantity" = "quantity" - \$1 WHERE "productid" = \$2',
        parameters: [decrementBy, productId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error updating product quantity: $e');
      return false;
    }
  }

  // ==================== Cart Functions ====================

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM Carts WHERE "userid" = \$1',
        parameters: [userId],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return {
          'cartid': map['cartid'],
          'userid': map['userid'],
          'productid': map['productid'],
          'quantity': map['quantity'],
          'price': map['price'],
          'addedat': map['addedat'],
        };
      }).toList();
    } catch (e) {
      print('❌ Error getting cart items: $e');
      return [];
    }
  }

  Future<bool> addToCart({
    required int userId,
    required int productId,
    required int quantity,
    required double price,
  }) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        '''INSERT INTO Carts ("userid", "productid", "quantity", "price", "addedat")
           VALUES (\$1, \$2, \$3, \$4, \$5)
           ON CONFLICT ("userid", "productid") DO UPDATE SET "quantity" = Carts."quantity" + \$3''',
        parameters: [
          userId,
          productId,
          quantity,
          price,
          DateTime.now().toIso8601String(),
        ],
      );
      
      return true;
    } catch (e) {
      print('❌ Error adding to cart: $e');
      return false;
    }
  }

  Future<bool> removeFromCart(int cartId) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'DELETE FROM Carts WHERE "cartid" = \$1',
        parameters: [cartId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error removing from cart: $e');
      return false;
    }
  }

  Future<bool> clearCart(int userId) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'DELETE FROM Carts WHERE "userid" = \$1',
        parameters: [userId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error clearing cart: $e');
      return false;
    }
  }

  // ==================== User Functions ====================

  Future<User?> getUserByTelegram(int telegramId) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM Users WHERE "telegramid" = \$1',
        parameters: [telegramId],
      );
      
      if (results.isEmpty) return null;
      
      final map = results.first.toColumnMap();
      return User(
        userId: map['userid'] as int,
        telegramId: map['telegramid'] as int,
        userName: map['username'] as String?,
        userType: map['usertype'] as String?,
        phoneNumber: map['phonenumber'] as String?,
        fullName: map['fullname'] as String?,
      );
    } catch (e) {
      print('❌ Error getting user: $e');
      return null;
    }
  }

  Future<int?> createUser({
    required int telegramId,
    String? userName,
    String? userType,
    String? phoneNumber,
    String? fullName,
  }) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO Users ("telegramid", "username", "usertype", "phonenumber", "fullname", "createdat")
           VALUES (\$1, \$2, \$3, \$4, \$5, \$6)
           RETURNING "userid"''',
        parameters: [
          telegramId,
          userName,
          userType,
          phoneNumber,
          fullName,
          DateTime.now().toIso8601String(),
        ],
      );
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        return map['userid'] as int;
      }
      return null;
    } catch (e) {
      print('❌ Error creating user: $e');
      return null;
    }
  }

  // ==================== Seller List Functions ====================

  Future<List<Seller>> getAllSellers() async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT * FROM sellers ORDER BY "sellerid"',
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return Seller(
          sellerId: map['sellerid'] as int,
          telegramId: map['telegramid'] as int,
          userName: map['username'] as String?,
          storeName: map['storename'] as String?,
          status: map['status'] as String?,
          imagePath: map['imagepath'] as String?,
          requireCustomerRegistration: (map['requirecustomerregistration'] as int?) == 1,
        );
      }).toList();
    } catch (e) {
      print('❌ Error getting all sellers: $e');
      return [];
    }
  }

  Future<bool> updateSeller(Seller seller) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        '''UPDATE sellers SET "storename" = \$1, "username" = \$2, "imagepath" = \$3, "requirecustomerregistration" = \$4
           WHERE "sellerid" = \$5''',
        parameters: [
          seller.storeName,
          seller.userName,
          seller.imagePath,
          seller.requireCustomerRegistration ? 1 : 0,
          seller.sellerId,
        ],
      );
      
      return true;
    } catch (e) {
      print('❌ Error updating seller: $e');
      return false;
    }
  }

  Future<bool> updateSellerStatus(int sellerId, String status) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'UPDATE sellers SET "status" = \$1 WHERE "sellerid" = \$2',
        parameters: [status, sellerId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error updating seller status: $e');
      return false;
    }
  }

  Future<bool> deleteSeller(int sellerId) async {
    try {
      await _ensureConnection();
      
      // First delete related data
      await _connection!.execute(
        'DELETE FROM "productimages" WHERE "productid" IN (SELECT "productid" FROM products WHERE "sellerid" = \$1)',
        parameters: [sellerId],
      );
      
      await _connection!.execute(
        'DELETE FROM products WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      await _connection!.execute(
        'DELETE FROM categories WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      // Finally delete the seller
      await _connection!.execute(
        'DELETE FROM sellers WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error deleting seller: $e');
      return false;
    }
  }

  // ==================== Image Functions ====================

  Future<int> uploadImageToStorage(String fileName, List<int> fileBytes) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO "imagestorage" ("filename", "filedata", "uploadedat") 
           VALUES (\$1, \$2, NOW())
           ON CONFLICT ("filename") DO UPDATE SET "filedata" = \$2, "uploadedat" = NOW()
           RETURNING 1''',
        parameters: [fileName, fileBytes],
      );
      
      // Return 1 if successful (file was inserted/updated)
      return result.isNotEmpty ? 1 : 0;
    } catch (e) {
      print('❌ Error uploading image to storage: $e');
      return 0;
    }
  }

  Future<int?> addProductImage(int productId, String imagePath, [int imageOrder = 0]) async {
    try {
      await _ensureConnection();
      
      final result = await _connection!.execute(
        '''INSERT INTO "productimages" ("productid", "imagepath", "imageorder")
           VALUES (\$1, \$2, \$3)
           RETURNING "imageid"''',
        parameters: [productId, imagePath, imageOrder],
      );
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        return map['imageid'] as int?;
      }
      return null;
    } catch (e) {
      print('❌ Error adding product image: $e');
      return null;
    }
  }

  Future<bool> deleteProductImage(int imageId) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'DELETE FROM "productimages" WHERE "imageid" = \$1',
        parameters: [imageId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error deleting product image: $e');
      return false;
    }
  }

  // Close connection
  Future<void> close() async {
    if (_isConnected && _connection != null) {
      try {
        await _connection!.close();
        _isConnected = false;
        print('✅ PostgreSQL connection closed');
      } catch (e) {
        print('❌ Error closing connection: $e');
      }
    }
  }
}
