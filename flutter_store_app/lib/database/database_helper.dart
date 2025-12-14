import 'package:postgres/postgres.dart';
import '../models/database_models.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  Connection? _connection;

  // Railway Database Credentials
  final String _dbHost = 'switchback.proxy.rlwy.net';
  final int _dbPort = 20266;
  final String _dbName = 'railway';
  final String _dbUser = 'postgres';
  final String _dbPass = 'bqcTJxNXLgwOftDoarrtmjmjYWurEIEh';

  DatabaseHelper._init();

  Future<Connection> get database async {
    if (_connection != null && _connection!.isOpen) return _connection!;
    _connection = await _initDB();
    return _connection!;
  }

  Future<Connection> _initDB() async {
    print("Connecting to PostgreSQL...");
    return await Connection.open(
      Endpoint(
        host: _dbHost,
        port: _dbPort,
        database: _dbName,
        username: _dbUser,
        password: _dbPass,
      ),
      settings: ConnectionSettings(sslMode: SslMode.disable),
    );
  }

  // --- Helpers to mimic sqflite behavior but with Postgres ---
  
  Future<List<Map<String, dynamic>>> _query(String sql, [Map<String, dynamic>? params]) async {
    final conn = await database;
    try {
      final result = await conn.execute(Sql.named(sql), parameters: params);
      
      // Convert Result to List<Map<String, dynamic>>
      // Result is an iterable of ResultRow. ResultRow is indexable but also has column metadata.
      // We need to map it to Key-Value pairs.
      return result.map((row) => row.toColumnMap()).toList();
    } catch (e) {
      print("Query Error: $e\nSQL: $sql");
      rethrow;
    }
  }

  Future<int> _execute(String sql, [Map<String, dynamic>? params]) async {
    final conn = await database;
    try {
      final result = await conn.execute(Sql.named(sql), parameters: params);
      return result.affectedRows;
    } catch (e) {
      print("Execute Error: $e\nSQL: $sql");
      rethrow;
    }
  }
  
  Future<dynamic> _insertReturningId(String table, Map<String, dynamic> values, String pkName) async {
    final columns = values.keys.join(', ');
    final placeholders = values.keys.map((k) => '@$k').join(', ');
    
    final sql = 'INSERT INTO "$table" ($columns) VALUES ($placeholders) RETURNING "$pkName"';
    
    // Ensure all values are mapped correctly for Postgres
    // Dates might need to be DateTime objects or ISO strings.
    
    final result = await _query(sql, values);
    if (result.isNotEmpty) {
      return result.first[pkName];
    }
    return null;
  }
  
  Future<void> _insert(String table, Map<String, dynamic> values) async {
    final columns = values.keys.join(', ');
    final placeholders = values.keys.map((k) => '@$k').join(', ');
    
    final sql = 'INSERT INTO "$table" ($columns) VALUES ($placeholders)';
    await _execute(sql, values);
  }

  Future<void> _update(String table, Map<String, dynamic> values, String where, Map<String, dynamic> whereArgs) async {
    final updates = values.keys.map((k) => '$k = @$k').join(', ');
    
    // Merge values and whereArgs
    final params = {...values, ...whereArgs};
    
    final sql = 'UPDATE "$table" SET $updates WHERE $where';
    await _execute(sql, params);
  }
  
  Future<void> _delete(String table, String where, Map<String, dynamic> whereArgs) async {
    final sql = 'DELETE FROM "$table" WHERE $where';
    await _execute(sql, whereArgs);
  }

  // --- Users ---
  Future<List<User>> getAllUsers() async {
    final result = await _query('SELECT * FROM Users');
    return result.map((json) => User.fromMap(json)).toList();
  }

  // --- Sellers ---
  Future<List<Seller>> getAllSellers() async {
    final result = await _query('SELECT * FROM Sellers');
    return result.map((json) => Seller.fromMap(json)).toList();
  }

  // --- Categories ---
  Future<List<Category>> getCategories(int sellerId) async {
    final result = await _query(
      'SELECT * FROM Categories WHERE SellerID = @id ORDER BY OrderIndex',
      {'id': sellerId}
    );
    return result.map((json) => Category.fromMap(json)).toList();
  }

  // --- Login Helpers ---
  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    final result = await _query(
      'SELECT * FROM Sellers WHERE TelegramID = @id',
      {'id': telegramId}
    );
    if (result.isNotEmpty) {
      return Seller.fromMap(result.first);
    }
    return null;
  }

  // --- Seller Management ---
  Future<void> updateSellerStatus(int sellerId, String status) async {
    await _update(
      'Sellers', 
      {'Status': status}, 
      'SellerID = @id', 
      {'id': sellerId}
    );
  }

  Future<void> addSeller(String storeName, int telegramId, String userName) async {
    await _insert('Sellers', {
      'TelegramID': telegramId,
      'StoreName': storeName,
      'UserName': userName,
      'Status': 'active',
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }

  // --- Products ---
  Future<List<Product>> getProducts(int sellerId, {int? categoryId}) async {
    String sql = 'SELECT * FROM Products WHERE SellerID = @sid';
    Map<String, dynamic> params = {'sid': sellerId};

    if (categoryId != null) {
      sql += ' AND CategoryID = @cid';
      params['cid'] = categoryId;
    }

    final result = await _query(sql, params);
    return result.map((json) => Product.fromMap(json)).toList();
  }

  Future<void> addProduct(Product product) async {
    // Note: conflictAlgorithm replace is not simple in Postgres (ON CONFLICT). 
    // Assuming INSERT is enough or we check existence. 
    // For now, standard INSERT.
    await _insert('Products', {
        'SellerID': product.sellerId,
        'CategoryID': product.categoryId,
        'Name': product.name,
        'Description': product.description,
        'Price': product.price,
        'WholesalePrice': product.wholesalePrice,
        'Quantity': product.quantity,
        'ImagePath': product.imagePath,
        'Status': product.status,
    });
  }
  
  Future<void> updateProduct(Product product) async {
    await _update('Products',
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
      'ProductID = @id',
      {'id': product.productId}
    );
  }

  Future<void> deleteProduct(int productId) async {
    await _delete('Products', 'ProductID = @id', {'id': productId});
  }

  // --- Categories Management ---
  Future<void> addCategory(Category category) async {
    await _insert('Categories', {
      'SellerID': category.sellerId,
      'Name': category.name,
      'OrderIndex': category.orderIndex
    });
  }

  Future<void> updateCategory(Category category) async {
    await _update(
      'Categories',
      {'Name': category.name},
      'CategoryID = @id',
      {'id': category.categoryId}
    );
  }

  Future<void> deleteCategory(int categoryId) async {
    await _delete('Categories', 'CategoryID = @id', {'id': categoryId});
  }

  // --- Orders ---
  Future<List<Order>> getOrders(int sellerId) async {
    final result = await _query(
      'SELECT * FROM Orders WHERE SellerID = @id ORDER BY CreatedAt DESC',
      {'id': sellerId}
    );
    return result.map((json) => Order.fromMap(json)).toList();
  }

  Future<void> updateOrderStatus(int orderId, String status) async {
    await _update(
      'Orders',
      {'Status': status},
      'OrderID = @id',
      {'id': orderId}
    );
  }
  
  // --- Messages ---
  Future<void> addMessage(int orderId, int sellerId, String messageType, String messageText) async {
    await _insert('Messages', {
      'OrderID': orderId,
      'SellerID': sellerId,
      'MessageType': messageType,
      'MessageText': messageText,
      'IsRead': 0,
      'CreatedAt': DateTime.now().toIso8601String(),
    });
  }

  // --- Cart ---
  Future<void> addToCart(int userId, int productId, int quantity, double price) async {
    // Upsert logic for Carts (UNIQUE UserID, ProductID)
    // Postgres: ON CONFLICT (UserID, ProductID) DO UPDATE...
    
    final sql = '''
      INSERT INTO Carts (UserID, ProductID, Quantity, Price, AddedAt)
      VALUES (@uid, @pid, @qty, @price, @date)
      ON CONFLICT (UserID, ProductID) 
      DO UPDATE SET Quantity = Carts.Quantity + @qty, Price = @price
    ''';
    
    await _execute(sql, {
      'uid': userId,
      'pid': productId,
      'qty': quantity,
      'price': price,
      'date': DateTime.now().toIso8601String()
    });
  }

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    final sql = '''
      SELECT c.*, p.Name, p.ImagePath, p.SellerID, s.StoreName
      FROM Carts c
      JOIN Products p ON c.ProductID = p.ProductID
      JOIN Sellers s ON p.SellerID = s.SellerID
      WHERE c.UserID = @uid
    ''';
    
    return await _query(sql, {'uid': userId});
  }

  Future<void> updateCartQuantity(int cartId, int quantity) async {
    if (quantity <= 0) {
      await removeFromCart(cartId);
    } else {
      await _update(
        'Carts',
        {'Quantity': quantity},
        'CartID = @id',
        {'id': cartId}
      );
    }
  }

  Future<void> removeFromCart(int cartId) async {
    await _delete('Carts', 'CartID = @id', {'id': cartId});
  }

  Future<void> clearCart(int userId) async {
    await _delete('Carts', 'UserID = @id', {'id': userId});
  }

  // --- Create Order ---
  Future<int> createOrder(int buyerId, int sellerId, double total, String address, String notes, List<Map<String, dynamic>> items) async {
    final conn = await database;
    
    // Transaction
    return await conn.runTx((ctx) async {
       // Insert Order
       // Return ID
       // Note: Helper methods usually use global _execute which calls conn.execute.
       // Inside transaction, we must use ctx.execute.
       // So we can't easily use the helpers here unless we refactor helpers to accept connection context.
       // I'll write raw SQL for transaction safety.
       
       final orderSql = '''
         INSERT INTO Orders 
         (BuyerID, SellerID, Total, Status, CreatedAt, DeliveryAddress, Notes, PaymentMethod, FullyPaid)
         VALUES (@bid, @sid, @total, 'Pending', @date, @addr, @notes, 'cash', 0)
         RETURNING OrderID
       ''';
       
       final orderParams = {
         'bid': buyerId,
         'sid': sellerId,
         'total': total,
         'date': DateTime.now().toString(),
         'addr': address,
         'notes': notes
       };
       
       final result = await ctx.execute(Sql.named(orderSql), parameters: orderParams);
       final orderId = result.first[0] as int;

       // Insert Items
       for (var item in items) {
         await ctx.execute(
           Sql.named('''
             INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price)
             VALUES (@oid, @pid, @qty, @price)
           '''),
           parameters: {
             'oid': orderId,
             'pid': item['ProductID'],
             'qty': item['Quantity'],
             'price': item['Price']
           }
         );
       }
       
       return orderId;
    });
  }
}
