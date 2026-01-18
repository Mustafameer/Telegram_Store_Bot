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
        print('🔄 Attempting to reconnect to PostgreSQL...');
        await _connect();
        print('✅ Reconnection successful');
      } catch (e) {
        print('❌ Failed to reconnect: $e');
        _isConnected = false;
        _connection = null;
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
        'SELECT * FROM "Categories" WHERE "SellerID" = \$1 ORDER BY "OrderIndex"',
        parameters: [sellerId],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return Category(
          categoryId: map['CategoryID'] as int,
          sellerId: map['SellerID'] as int,
          name: map['Name'] as String,
          orderIndex: map['OrderIndex'] as int? ?? 0,
          imagePath: map['ImagePath'] as String?,
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
        'SELECT * FROM "Categories" WHERE "CategoryID" = \$1',
        parameters: [categoryId],
      );
      
      if (results.isEmpty) return null;
      
      final map = results.first.toColumnMap();
      return Category(
        categoryId: map['CategoryID'] as int,
        sellerId: map['SellerID'] as int,
        name: map['Name'] as String,
        orderIndex: map['OrderIndex'] as int? ?? 0,
        imagePath: map['ImagePath'] as String?,
      );
    } catch (e) {
      print('❌ Error getting category: $e');
      return null;
    }
  }

  Future<void> updateCategory(int categoryId, String name, int orderIndex) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'UPDATE "Categories" SET "Name" = \$1, "OrderIndex" = \$2 WHERE "CategoryID" = \$3',
        parameters: [name, orderIndex, categoryId],
      );
      
      print('✅ Category updated: ID=$categoryId');
    } catch (e) {
      print('❌ Error updating category: $e');
      rethrow;
    }
  }

  Future<void> addCategory(int sellerId, String name) async {
    try {
      print('📡 Ensuring PostgreSQL connection...');
      await _ensureConnection();
      print('✅ Connection verified');
      
      print('📁 Preparing INSERT query for category: "$name" (SellerID: $sellerId)');
      await _connection!.execute(
        'INSERT INTO "Categories" ("SellerID", "Name", "OrderIndex") VALUES (\$1, \$2, 0)',
        parameters: [sellerId, name],
      );
      
      print('✅ Category added successfully: $name');
    } catch (e) {
      print('❌ Error adding category: $e');
      print('   Error type: ${e.runtimeType}');
      rethrow;
    }
  }

  Future<void> deleteCategory(int categoryId) async {
    try {
      await _ensureConnection();
      
      await _connection!.execute(
        'DELETE FROM "Categories" WHERE "CategoryID" = \$1',
        parameters: [categoryId],
      );
      
      print('✅ Category deleted: ID=$categoryId');
    } catch (e) {
      print('❌ Error deleting category: $e');
      rethrow;
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
      
      print('🔍 جاري البحث عن صور المنتج: ID=$productId');
      
      // استعلام من جدول imagestorage (مع productid و imageorder)
      final results = await _connection!.execute(
        '''SELECT "imageid", "filename" as "imagepath", "imageorder", "productid"
           FROM "imagestorage" 
           WHERE "productid" = \$1 
           ORDER BY "imageorder", "imageid"''',
        parameters: [productId],
      );
      
      print('📸 تم العثور على ${results.length} صورة للمنتج $productId');
      
      if (results.isEmpty) {
        print('⚠️ لا توجد صور للمنتج $productId');
        return [];
      }
      
      final images = results.map((row) {
        final map = row.toColumnMap();
        final imagePath = map['imagepath']?.toString() ?? '';
        
        if (imagePath.isEmpty) {
          print('   - ⚠️ صورة بمسار فارغ! ID: ${map['imageid']}');
        } else {
          print('   - صورة: $imagePath');
        }
        
        return {
          'imageid': map['imageid'],
          'productid': map['productid'] ?? productId,
          'imagepath': imagePath,
          'imageorder': map['imageorder'] ?? 0,
        };
      }).toList();
      
      // تصفية الصور ذات imagepath الفارغ
      final validImages = images.where((img) => (img['imagepath'] as String).isNotEmpty).toList();
      print('📊 عدد الصور الصحيحة بعد التصفية: ${validImages.length} (تم حذف ${images.length - validImages.length} صور فارغة)');
      
      return validImages;
    } catch (e) {
      print('❌ خطأ في جلب صور المنتج: $e');
      return [];
    }
  }

  // جديد: تحميل بيانات الصور من ImageStorage
  Future<Uint8List?> getImageData(String fileName) async {
    try {
      if (fileName.isEmpty) {
        print('❌ اسم الملف فارغ');
        return null;
      }
      
      await _ensureConnection();
      
      print('🔍 جاري البحث عن الصورة: $fileName');
      
      // استرجاع البيانات بصيغة hex آمنة من PostgreSQL
      final results = await _connection!.execute(
        'SELECT encode(filedata, \'hex\') as filedata FROM imagestorage WHERE filename = \$1',
        parameters: [fileName],
      );
      
      print('🔍 تم استرجاع ${results.length} نتيجة');
      
      if (results.isEmpty) {
        print('⚠️ لم يتم العثور على الصورة: $fileName');
        return null;
      }
      
      final row = results.first.toColumnMap();
      final hexData = row['filedata'];
      
      if (hexData == null) {
        print('⚠️ بيانات الصورة فارغة: $fileName');
        return null;
      }
      
      print('✅ تم العثور على البيانات بصيغة hex (${hexData.toString().length} characters)');

      try {
        // تحويل hex string إلى bytes
        final hexString = hexData.toString();
        final bytes = <int>[];
        for (int i = 0; i < hexString.length; i += 2) {
          final hexByte = hexString.substring(i, i + 2);
          bytes.add(int.parse(hexByte, radix: 16));
        }
        
        final uint8Bytes = Uint8List.fromList(bytes);
        print('✅ تم تحويل hex إلى bytes بنجاح (${uint8Bytes.length} bytes)');
        return uint8Bytes;
      } catch (e) {
        print('❌ خطأ في تحويل hex: $e');
        return null;
      }
    } catch (e) {
      print('❌ خطأ في جلب بيانات الصورة: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> getProductImagesForOrder(int productId, int quantity) async {
    try {
      await _ensureConnection();
      
      final results = await _connection!.execute(
        'SELECT "imageid", "filename" as "imagepath", "imageorder" FROM "imagestorage" WHERE "productid" = \$1 ORDER BY "imageorder", "imageid" LIMIT \$2',
        parameters: [productId, quantity],
      );
      
      return results.map((row) {
        final map = row.toColumnMap();
        return {
          'imageid': map['imageid'],
          'productid': productId,
          'imagepath': map['imagepath'],
          'imageorder': map['imageorder'] ?? 0,
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
      
      // First delete related images from imagestorage (CASCADE should handle this, but be explicit)
      await _connection!.execute(
        'DELETE FROM "imagestorage" WHERE "productid" = \$1',
        parameters: [productId],
      );
      
      // Then delete the product
      await _connection!.execute(
        'DELETE FROM "products" WHERE "productid" = \$1',
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
        'UPDATE products SET "quantity" = "quantity" - \$1 WHERE "productid" = \$2',
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
        'DELETE FROM "imagestorage" WHERE "productid" IN (SELECT "productid" FROM "products" WHERE "sellerid" = \$1)',
        parameters: [sellerId],
      );
      
      await _connection!.execute(
        'DELETE FROM "products" WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      await _connection!.execute(
        'DELETE FROM "categories" WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      // Finally delete the seller
      await _connection!.execute(
        'DELETE FROM "sellers" WHERE "sellerid" = \$1',
        parameters: [sellerId],
      );
      
      return true;
    } catch (e) {
      print('❌ Error deleting seller: $e');
      return false;
    }
  }

  // ==================== Image Functions ====================

  // جديد: رفع بيانات الصور لـ ImageStorage
  Future<int> uploadImageToStorage(String fileName, List<int> fileBytes) async {
    try {
      await _ensureConnection();
      
      print('📤 جاري رفع الصورة: $fileName، الحجم: ${fileBytes.length} bytes');
      
      // تحويل البيانات إلى hex string لضمان الحفظ الآمن
      final hexData = fileBytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      print('📝 تم تحويل البيانات إلى hex (${hexData.length} characters)');
      
      final result = await _connection!.execute(
        '''INSERT INTO "imagestorage" ("filename", "filedata") 
           VALUES (\$1, decode(\$2, 'hex'))
           ON CONFLICT ("filename") DO UPDATE SET "filedata" = decode(\$2, 'hex')
           RETURNING 1''',
        parameters: [fileName, hexData],
      );
      
      if (result.isNotEmpty) {
        print('✅ تم رفع الصورة بنجاح: $fileName');
        return 1;
      } else {
        print('⚠️ فشل الرفع (النتيجة فارغة): $fileName');
        return 0;
      }
    } catch (e) {
      print('❌ خطأ في رفع الصورة: $e');
      return 0;
    }
  }

  Future<int?> addProductImage(int productId, String fileName, [int imageOrder = 0]) async {
    try {
      await _ensureConnection();
      
      print('🔗 جاري إضافة صورة للمنتج $productId: $fileName');
      
      // تحديث السجل الموجود في imagestorage بربطه بـ productid و imageorder
      final result = await _connection!.execute(
        '''UPDATE "imagestorage" 
           SET "productid" = \$1, "imageorder" = \$2
           WHERE "filename" = \$3
           RETURNING "imageid"''',
        parameters: [productId, imageOrder, fileName],
      );
      
      print('📊 عدد الصفوف المرجعة: ${result.length}');
      
      if (result.isNotEmpty) {
        final map = result.first.toColumnMap();
        print('📍 القيم المرجعة: $map');
        final imageId = map['imageid'] as int?;
        
        if (imageId != null && imageId > 0) {
          print('✅ تم إضافة الصورة بنجاح: $fileName (Image ID: $imageId، المنتج: $productId، الترتيب: $imageOrder)');
          return imageId;
        } else {
          print('⚠️ فشل الحصول على imageid - القيمة: $imageId');
          return null;
        }
      }
      
      print('⚠️ فشل التحديث (لم تعد أي صفوف محدثة)');
      return null;
    } catch (e, stackTrace) {
      print('❌ خطأ في إضافة الصورة: $e');
      print('📍 Stack Trace: $stackTrace');
      return null;
    }
  }

  Future<bool> deleteProductImage(int imageId) async {
    try {
      await _ensureConnection();
      
      print('🗑️ جاري حذف الصورة ID: $imageId');
      
      // حذف من جدول imagestorage
      await _connection!.execute(
        'DELETE FROM "imagestorage" WHERE "imageid" = \$1',
        parameters: [imageId],
      );
      
      print('✅ تم حذف الصورة بنجاح: $imageId');
      return true;
    } catch (e) {
      print('❌ خطأ في حذف الصورة: $e');
      return false;
    }
  }

  // Get messages for a seller
  Future<List<Map<String, dynamic>>> getMessages(int sellerId) async {
    try {
      await _ensureConnection();
      
      print('🔌 PostgreSQL: Querying messages for seller $sellerId');
      print('   Query: SELECT * FROM messages WHERE "sellerid" = \$1');
      
      final results = await _connection!.execute(
        'SELECT * FROM messages WHERE "sellerid" = \$1 ORDER BY "createdat" DESC',
        parameters: [sellerId],
      );
      
      print('📊 PostgreSQL: Returned ${results.length} messages');
      
      if (results.isEmpty) {
        print('⚠️ لا توجد رسائل في قاعدة البيانات لـ Seller ID: $sellerId');
      }
      
      return results.map((row) {
        final map = row.toColumnMap();
        print('   📬 Found message: ${map['messagetype']} (OrderID: ${map['orderid']})');
        return {
          'MessageID': map['messageid'],
          'OrderID': map['orderid'],
          'SellerID': map['sellerid'],
          'MessageType': map['messagetype'],
          'MessageText': map['messagetext'],
          'IsRead': (map['isread'] as int?) == 1,
          'CreatedAt': map['createdat'],
        };
      }).toList();
    } catch (e) {
      print('❌ Error getting messages: $e');
      print('❌ Stack: $e');
      return [];
    }
  }

  /// الحصول على الزبائن الآجلين لبائع معين
  Future<List<dynamic>> getCreditCustomers(int sellerId) async {
    try {
      await _ensureConnection();
      
      print('🔌 PostgreSQL: Querying credit customers for seller $sellerId');
      
      final results = await _connection!.execute(
        'SELECT * FROM creditcustomers WHERE "sellerid" = \$1 ORDER BY "fullname" ASC',
        parameters: [sellerId],
      );

      print('📊 PostgreSQL: Returned ${results.length} rows');
      
      return results.map((row) {
        final map = row.toColumnMap();
        print('🔍 Row data: $map');
        return {
          'CustomerID': map['customerid'],
          'SellerID': map['sellerid'],
          'FullName': map['fullname'],
          'PhoneNumber': map['phonenumber'],
          'TelegramID': map['telegramid'],
          'CreatedAt': map['createdat'],
        };
      }).toList();
    } catch (e) {
      print('❌ Error getting credit customers: $e');
      print('❌ Stack trace: ${StackTrace.current}');
      return [];
    }
  }

  // ==================== Credit Transaction Functions ====================

  Future<double?> getCustomerBalance(int customerId, int sellerId) async {
    try {
      await _ensureConnection();
      
      print('💰 جاري جلب رصيد الزبون $customerId للمتجر $sellerId');
      
      final results = await _connection!.execute(
        '''SELECT "balanceafter" 
           FROM "customercredit" 
           WHERE "customerid" = \$1 AND "sellerid" = \$2
           ORDER BY "transactiondate" DESC 
           LIMIT 1''',
        parameters: [customerId, sellerId],
      );
      
      if (results.isNotEmpty) {
        final map = results.first.toColumnMap();
        final balance = map['balanceafter'] as double?;
        print('✅ الرصيد الحالي: $balance');
        return balance ?? 0;
      }
      
      print('⚠️ لا توجد معاملات سابقة - الرصيد الحالي: 0');
      return 0;
    } catch (e) {
      print('❌ خطأ في جلب الرصيد: $e');
      return 0;
    }
  }

  Future<List<Map<String, dynamic>>> getCustomerTransactions(int customerId) async {
    try {
      await _ensureConnection();
      
      print('📊 جاري جلب معاملات الزبون $customerId');
      
      final results = await _connection!.execute(
        '''SELECT "creditid", "customerid", "sellerid", "transactiontype", "amount", 
                  "description", "balancebefore", "balanceafter", "transactiondate"
           FROM "customercredit" 
           WHERE "customerid" = \$1
           ORDER BY "transactiondate" DESC''',
        parameters: [customerId],
      );
      
      print('📊 تم جلب ${results.length} معاملة');
      
      return results.map((row) {
        final map = row.toColumnMap();
        return {
          'creditid': map['creditid'],
          'customerid': map['customerid'],
          'sellerid': map['sellerid'],
          'transactiontype': map['transactiontype'],
          'amount': map['amount'],
          'description': map['description'],
          'balancebefore': map['balancebefore'],
          'balanceafter': map['balanceafter'],
          'transactiondate': map['transactiondate'],
        };
      }).toList();
    } catch (e) {
      print('❌ خطأ في جلب المعاملات: $e');
      return [];
    }
  }

  Future<int> addCreditTransaction({
    required int customerId,
    required int sellerId,
    required String transactionType,
    required double amount,
    String? description,
    required double balanceBefore,
    required double balanceAfter,
  }) async {
    try {
      await _ensureConnection();
      
      print('💳 جاري إضافة معاملة ائتمانية...');
      
      final results = await _connection!.execute(
        '''INSERT INTO "customercredit" 
           ("customerid", "sellerid", "transactiontype", "amount", "description", 
            "balancebefore", "balanceafter", "transactiondate")
           VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, CURRENT_TIMESTAMP)
           RETURNING "creditid"''',
        parameters: [
          customerId,
          sellerId,
          transactionType,
          amount,
          description ?? '',
          balanceBefore,
          balanceAfter,
        ],
      );
      
      if (results.isNotEmpty) {
        final map = results.first.toColumnMap();
        final creditId = map['creditid'] as int? ?? 0;
        print('✅ تمت إضافة المعاملة بنجاح (ID: $creditId)');
        return creditId;
      }
      
      print('⚠️ فشل في الحصول على CreditID');
      return 0;
    } catch (e) {
      print('❌ خطأ في إضافة المعاملة: $e');
      print('Stack: $e');
      return 0;
    }
  }

  Future<bool> updateCreditTransaction({
    required int creditId,
    required String transactionType,
    required double amount,
    String? description,
    required double balanceBefore,
    required double balanceAfter,
  }) async {
    try {
      await _ensureConnection();
      
      print('✏️ جاري تعديل المعاملة $creditId...');
      
      await _connection!.execute(
        '''UPDATE "customercredit" 
           SET "transactiontype" = \$1, "amount" = \$2, "description" = \$3,
               "balancebefore" = \$4, "balanceafter" = \$5
           WHERE "creditid" = \$6''',
        parameters: [
          transactionType,
          amount,
          description ?? '',
          balanceBefore,
          balanceAfter,
          creditId,
        ],
      );
      
      print('✅ تم تعديل المعاملة بنجاح');
      return true;
    } catch (e) {
      print('❌ خطأ في تعديل المعاملة: $e');
      return false;
    }
  }

  Future<bool> deleteCreditTransaction(int creditId) async {
    try {
      await _ensureConnection();
      
      print('🗑️ جاري حذف المعاملة $creditId...');
      
      await _connection!.execute(
        'DELETE FROM "customercredit" WHERE "creditid" = \$1',
        parameters: [creditId],
      );
      
      print('✅ تم حذف المعاملة بنجاح');
      return true;
    } catch (e) {
      print('❌ خطأ في حذف المعاملة: $e');
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
