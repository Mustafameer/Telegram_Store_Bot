/// Database Helper using Cloud PostgreSQL (replaces SQLite)
/// يستخدم نفس البيانات والمنطق المركزي من البوت Python
import '../services/postgres_service.dart';
import '../models/database_models.dart';
import 'dart:io';
import 'dart:typed_data';
import 'package:path/path.dart' as p;
import 'package:image/image.dart' as img;
import 'package:uuid/uuid.dart';
import 'package:path_provider/path_provider.dart';

class DatabaseHelperCloud {
  final postgresService = PostgresService();

  /// Initialize cloud database connection
  Future<void> initialize() async {
    await postgresService.initialize();
  }

  String _getExecutableDirectory() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      final executablePath = Platform.resolvedExecutable;
      return p.dirname(executablePath);
    }
    return Directory.current.path;
  }

  /// حفظ الصورة محلياً (ملفات الصور فقط - البيانات من السحابة)
  Future<String?> _saveImageLocally(String? sourcePath) async {
    if (sourcePath == null || sourcePath.isEmpty) return null;
    try {
      final sourceFile = File(sourcePath);
      if (!await sourceFile.exists()) return null;

      Directory directory;
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
        final exeDir = _getExecutableDirectory();
        final parentImg = Directory(p.join(p.dirname(exeDir), 'data', 'Images'));
        if (await parentImg.exists()) {
          directory = parentImg;
        } else {
          directory = Directory(p.join(exeDir, 'data', 'Images'));
        }
      } else {
        final docs = await getApplicationDocumentsDirectory();
        directory = Directory(p.join(docs.path, 'Images'));
      }

      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }

      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final uuidHex = const Uuid().v4().replaceAll('-', '');
      final fileName = '${timestamp}_$uuidHex.jpg';
      final newPath = p.join(directory.path, fileName);

      print("🔄 Processing Image: $sourcePath -> $newPath");

      final bytes = await sourceFile.readAsBytes();
      img.Image? image = img.decodeImage(bytes);

      if (image == null) {
        print("⚠️ Image decoding failed, falling back to simple copy.");
        await sourceFile.copy(newPath);
        return newPath;
      }

      if (image.width > 1280) {
        image = img.copyResize(image, width: 1280);
      }

      final jpgBytes = img.encodeJpg(image, quality: 85);
      final newFile = File(newPath);
      await newFile.writeAsBytes(jpgBytes);

      print("✅ Saved Processed Image to: $newPath");
      return newPath;
    } catch (e) {
      print("❌ Failed to save image: $e");
      try {
        final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
        final uuidHex = const Uuid().v4().replaceAll('-', '');
        final fileName = '${timestamp}_$uuidHex.jpg';
        final exeDir = _getExecutableDirectory();
        final newPath = p.join(exeDir, 'data', 'Images', fileName);

        final dir = Directory(p.dirname(newPath));
        if (!await dir.exists()) await dir.create(recursive: true);

        await File(sourcePath).copy(newPath);
        return newPath;
      } catch (ex) {
        return sourcePath;
      }
    }
  }

  // ==================== Seller Functions ====================

  Future<List<Seller>> getAllSellers({bool forceRefresh = false}) async {
    try {
      return await postgresService.getAllSellers();
    } catch (e) {
      print('❌ Error getting all sellers: $e');
      return [];
    }
  }

  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    try {
      return await postgresService.getSellerByTelegram(telegramId);
    } catch (e) {
      print('❌ Error getting seller: $e');
      return null;
    }
  }

  Future<Seller?> getSellerById(int sellerId) async {
    try {
      // Note: postgresService doesn't have getSellerById, we'd need to add it
      // For now, we can query products which includes seller info
      final products = await postgresService.getProducts(sellerId);
      if (products.isNotEmpty) {
        // Reconstruct seller from product info
        return Seller(
          sellerId: sellerId,
          telegramId: products.first.sellerId,
          storeName: '',
          userName: '',
        );
      }
      return null;
    } catch (e) {
      print('❌ Error getting seller: $e');
      return null;
    }
  }

  Future<User?> getUserByTelegramId(int telegramId) async {
    try {
      return await postgresService.getUserByTelegram(telegramId);
    } catch (e) {
      print('❌ Error getting user: $e');
      return null;
    }
  }

  Future<void> addSeller(String storeName, int telegramId, String userName,
      {String? imagePath}) async {
    try {
      final sellerId = await postgresService.createSeller(
        telegramId: telegramId,
        storeName: storeName,
        userName: userName,
        imagePath: imagePath,
        requireCustomerRegistration: false,
      );
      
      if (sellerId != null) {
        print('✅ Seller added successfully: ID=$sellerId');
      } else {
        throw Exception('Failed to create seller - no ID returned');
      }
    } catch (e) {
      print('❌ Error adding seller: $e');
      rethrow;
    }
  }

  Future<void> updateSeller(Seller seller) async {
    try {
      final success = await postgresService.updateSeller(seller);
      if (success) {
        print('✅ Seller updated successfully');
      } else {
        throw Exception('Failed to update seller');
      }
    } catch (e) {
      print('❌ Error updating seller: $e');
      rethrow;
    }
  }

  Future<void> updateSellerStatus(int sellerId, String status) async {
    try {
      final success = await postgresService.updateSellerStatus(sellerId, status);
      if (success) {
        print('✅ Seller status updated successfully');
      } else {
        throw Exception('Failed to update seller status');
      }
    } catch (e) {
      print('❌ Error updating seller status: $e');
      rethrow;
    }
  }

  Future<void> deleteSeller(int sellerId) async {
    try {
      final success = await postgresService.deleteSeller(sellerId);
      if (success) {
        print('✅ Seller deleted successfully');
      } else {
        throw Exception('Failed to delete seller');
      }
    } catch (e) {
      print('❌ Error deleting seller: $e');
      rethrow;
    }
  }

  // ==================== Category Functions ====================

  Future<List<Category>> getCategories(int sellerId,
      {bool forceRefresh = false}) async {
    try {
      print('🔄 جاري جلب الأقسام للمتجر $sellerId...');
      final categories = await postgresService.getCategories(sellerId).timeout(
        const Duration(seconds: 15),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب الأقسام');
          return [];
        }
      );
      print('✅ تم جلب ${categories.length} قسم');
      return categories;
    } catch (e) {
      print('❌ خطأ في جلب الأقسام: $e');
      return [];
    }
  }

  Future<void> ensureCategorySchema() async {
    // No-op for cloud database
  }

  Future<int?> addCategory(Category category) async {
    try {
      print('🔹 [DatabaseHelper] Adding category: ${category.name}');
      print('   SellerID: ${category.sellerId}');
      print('   Calling postgresService.addCategory()...');
      
      final categoryId = await postgresService.addCategory(category.sellerId, category.name);
      
      print('✅ [DatabaseHelper] Category added successfully to PostgreSQL: ${category.name} (ID: $categoryId)');
      return categoryId;
    } catch (e) {
      print('❌ [DatabaseHelper] Error adding category: $e');
      print('   Error type: ${e.runtimeType}');
      rethrow;
    }
  }

  Future<void> updateCategory(Category category) async {
    try {
      await postgresService.updateCategory(category.categoryId, category.name, category.orderIndex);
    } catch (e) {
      print('❌ Error updating category: $e');
      rethrow;
    }
  }

  Future<void> deleteCategory(int categoryId) async {
    try {
      await postgresService.deleteCategory(categoryId);
    } catch (e) {
      print('❌ Error deleting category: $e');
      rethrow;
    }
  }

  // ==================== Product Functions ====================

  Future<List<Product>> getProducts(int sellerId, {int? categoryId, bool forceRefresh = false}) async {
    try {
      print('🔄 جاري جلب المنتجات للمتجر $sellerId...');
      print('   Category Filter: $categoryId');
      
      final products = await postgresService.getProducts(sellerId, categoryId).timeout(
        const Duration(seconds: 20),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب المنتجات');
          return [];
        }
      );
      print('✅ تم جلب ${products.length} منتج');
      
      if (products.isNotEmpty) {
        print('   أول منتج: ${products.first.name}');
      } else {
        print('   ❌ لم يتم جلب أي منتجات!');
      }
      
      return products;
    } catch (e) {
      print('❌ خطأ في جلب المنتجات: $e');
      return [];
    }
  }

  Future<void> addProduct(Product product) async {
    try {
      final result = await postgresService.addProduct(
        sellerId: product.sellerId,
        categoryId: product.categoryId,
        name: product.name,
        description: product.description,
        price: product.price,
        wholesalePrice: product.wholesalePrice,
        quantity: product.quantity,
        imagePath: product.imagePath,
        status: product.status,
      );
      if (result != null) {
        print('✅ Product added successfully: ID=$result');
      } else {
        throw Exception('Failed to add product');
      }
    } catch (e) {
      print('❌ Error adding product: $e');
      rethrow;
    }
  }

  Future<void> updateProduct(Product product) async {
    try {
      final success = await postgresService.updateProduct(product);
      if (success) {
        print('✅ Product updated successfully');
      } else {
        throw Exception('Failed to update product');
      }
    } catch (e) {
      print('❌ Error updating product: $e');
      rethrow;
    }
  }

  Future<void> deleteProduct(int productId) async {
    try {
      final success = await postgresService.deleteProduct(productId);
      if (success) {
        print('✅ Product deleted successfully');
      } else {
        throw Exception('Failed to delete product');
      }
    } catch (e) {
      print('❌ Error deleting product: $e');
      rethrow;
    }
  }

  // ==================== Product Images Functions ====================

  Future<List<ProductImage>> getProductImages(int productId) async {
    try {
      print('🖼️ جاري جلب صور المنتج $productId...');
      final images = await postgresService.getProductImages(productId).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب صور المنتج');
          return [];
        }
      );
      
      print('📊 تم استقبال ${images.length} صورة');
      
      return images
          .map((img) => ProductImage(
                imageId: img['imageid'],
                productId: img['productid'] ?? productId,
                imagePath: img['imagepath'],
                imageOrder: img['imageorder'] ?? 0,
              ))
          .toList();
    } catch (e) {
      print('❌ Error getting product images: $e');
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
      // أضيف timeout لمنع التأخير الطويل
      return await postgresService.getImageData(fileName).timeout(
        const Duration(seconds: 60),
        onTimeout: () {
          print('⏱️ انتهت مهلة تحميل الصورة: $fileName');
          return null;
        }
      );
    } catch (e) {
      print('❌ Error getting image data: $e');
      return null;
    }
  }

  Future<String?> getImageUrl(String fileName) async {
    try {
      if (fileName.isEmpty) {
        print('❌ اسم الملف فارغ');
        return null;
      }
      return await postgresService.getImageUrl(fileName).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          print('⏱️ انتهت مهلة تحميل رابط الصورة: $fileName');
          return null;
        }
      );
    } catch (e) {
      print('❌ Error getting image URL: $e');
      return null;
    }
  }

  Future<int> addProductImage(int productId, String imagePath,
      {int imageOrder = 0}) async {
    try {
      // Upload image file to ImageStorage table
      final file = File(imagePath);
      if (!file.existsSync()) {
        print('❌ صورة غير موجودة: $imagePath');
        return 0;
      }
      
      print('📁 جاري قراءة الملف: $imagePath');
      
      // Read file bytes
      final fileBytes = await file.readAsBytes();
      print('✅ تم قراءة ${fileBytes.length} بايت');
      
      // Generate timestamped filename to match bot's naming convention
      // Format: {timestamp}_{uuid}{ext}
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000; // Unix timestamp
      final uuid = const Uuid().v4().replaceAll('-', '').substring(0, 32); // 32-char hex
      final ext = p.extension(imagePath); // Get file extension
      final fileName = '${timestamp}_$uuid$ext';
      
      print('📤 جاري تحميل الصورة: $fileName (${fileBytes.length} bytes)');
      
      // Upload to ImageStorage table via PostgreSQL with timeout
      final uploadResult = await postgresService
          .uploadImageToStorage(fileName, fileBytes)
          .timeout(
            const Duration(seconds: 30),
            onTimeout: () {
              print('⏱️ انتهت مهلة تحميل الصورة');
              return 0;
            },
          );
      
      if (uploadResult <= 0) {
        print('❌ فشل تحميل الصورة إلى قاعدة البيانات');
        return 0;
      }
      
      print('✅ تم تحميل الصورة بنجاح: $fileName');
      
      // Insert ProductImage entry with the generated filename
      final imageId = await postgresService
          .addProductImage(productId, fileName, imageOrder)
          .timeout(
            const Duration(seconds: 30),
            onTimeout: () {
              print('⏱️ انتهت مهلة ربط الصورة بالمنتج');
              return null;
            },
          );
      
      if (imageId == null || imageId <= 0) {
        print('❌ فشل ربط الصورة بالمنتج - imageId: $imageId');
        return 0;
      }
      
      print('✅ تم ربط الصورة بالمنتج: ID=$imageId');
      return imageId;
    } catch (e, stackTrace) {
      print('❌ خطأ في إضافة الصورة: $e');
      print('📍 Stack Trace: $stackTrace');
      return 0;
    }
  }

  Future<void> deleteProductImage(int imageId) async {
    try {
      await postgresService.deleteProductImage(imageId);
      print('✅ Product image deleted successfully');
    } catch (e) {
      print('❌ Error deleting product image: $e');
      rethrow;
    }
  }

  // ==================== Cart Functions ====================

  Future<void> addToCart(int userId, int productId, int quantity,
      double price) async {
    try {
      await postgresService.addToCart(
        userId: userId,
        productId: productId,
        quantity: quantity,
        price: price,
      );
    } catch (e) {
      print('❌ Error adding to cart: $e');
      rethrow;
    }
  }

  Future<void> addToCartWithImages(int userId, int productId, int quantity,
      double price, List<int> imageIds) async {
    try {
      // Add to cart first
      await postgresService.addToCart(
        userId: userId,
        productId: productId,
        quantity: quantity,
        price: price,
      );
      // Note: CartImages are managed through the postgresService
    } catch (e) {
      print('❌ Error adding to cart with images: $e');
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    try {
      final items = await postgresService.getCartItems(userId);
      return items
          .map((item) => {
                'CartID': item['CartID'],
                'UserID': item['UserID'],
                'ProductID': item['ProductID'],
                'Quantity': item['Quantity'],
                'Price': item['Price'],
                'AddedAt': item['AddedAt'],
              })
          .toList();
    } catch (e) {
      print('❌ Error getting cart items: $e');
      return [];
    }
  }

  Future<List<ProductImage>> getCartImages(int cartId) async {
    // Cart images are managed via postgresService CartImages table
    return [];
  }

  Future<void> updateCartQuantity(int cartId, int quantity) async {
    try {
      if (quantity <= 0) {
        await removeFromCart(cartId);
      } else {
        // Update via postgresService
        print('⚠️ updateCartQuantity: Cart updates via postgresService');
      }
    } catch (e) {
      print('❌ Error updating cart quantity: $e');
      rethrow;
    }
  }

  Future<void> removeFromCart(int cartId) async {
    try {
      await postgresService.removeFromCart(cartId);
    } catch (e) {
      print('❌ Error removing from cart: $e');
      rethrow;
    }
  }

  Future<void> clearCart(int userId) async {
    try {
      await postgresService.clearCart(userId);
    } catch (e) {
      print('❌ Error clearing cart: $e');
      rethrow;
    }
  }

  // ==================== Order Functions ====================

  Future<List<Order>> getOrders(int sellerId) async {
    try {
      print('🔄 جاري جلب الطلبات للمتجر $sellerId...');
      final orders = await postgresService.getUserOrders(sellerId).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب الطلبات');
          return [];
        }
      );
      print('✅ تم جلب ${orders.length} طلب');
      return orders;
    } catch (e) {
      print('❌ خطأ في جلب الطلبات: $e');
      return [];
    }
  }

  Future<void> updateOrderStatus(int orderId, String status) async {
    try {
      // Order status updates via Bot
      print('⚠️ updateOrderStatus: Status updates managed via Bot');
    } catch (e) {
      print('❌ Error updating order status: $e');
      rethrow;
    }
  }

  Future<int> createOrder(int buyerId, int sellerId, double total,
      String address, String notes, List<Map<String, dynamic>> items, {
      String status = 'pending',
      String paymentMethod = 'cash',
      bool fullyPaid = false
    }) async {
    try {
      final orderId = await postgresService.createOrder(
        buyerId: buyerId,
        sellerId: sellerId,
        total: total,
        status: status,  // 🆕 Use provided status
        paymentMethod: paymentMethod,  // 🆕 Use provided payment method
        deliveryAddress: address,
        notes: notes,
        fullyPaid: fullyPaid,  // 🆕 Use provided fullyPaid flag
      );

      if (orderId != null) {
        // Add items to order
        for (var item in items) {
          await postgresService.addOrderItem(
            orderId: orderId,
            productId: item['ProductID'],
            quantity: item['Quantity'],
            price: item['Price'],
          );
          // Deduct stock
          await postgresService.updateProductQuantity(
            item['ProductID'],
            item['Quantity'],
          );
        }
      }

      return orderId ?? 0;
    } catch (e) {
      print('❌ Error creating order: $e');
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getItemsForOrder(int orderId) async {
    try {
      // Get order items from postgresService
      final order = await postgresService.getOrderById(orderId);
      if (order != null) {
        // Note: We'd need to implement getOrderItems in PostgresService
        return [];
      }
      return [];
    } catch (e) {
      print('❌ Error getting order items: $e');
      return [];
    }
  }

  Future<List<ProductImage>> getOrderItemImages(int orderItemId) async {
    return [];
  }

  Future<void> deleteOrder(int orderId) async {
    try {
      // Order deletion via Bot
      print('⚠️ deleteOrder: Order deletion managed via Bot');
    } catch (e) {
      print('❌ Error deleting order: $e');
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getDeletedItems() async {
    return [];
  }

  Future<void> clearDeletedItems(List<int> ids) async {
    // Sync operations for deleted items
  }

  Future<void> deductStockForOrder(int orderId) async {
    try {
      // Stock deduction handled during order creation
      print('⚠️ deductStockForOrder: Stock managed via PostgreSQL');
    } catch (e) {
      print('❌ Error deducting stock: $e');
      rethrow;
    }
  }

  // ==================== Counting Functions ====================

  Future<int> getProductsCount(int sellerId) async {
    try {
      final products = await getProducts(sellerId);
      return products.length;
    } catch (e) {
      print('❌ Error getting products count: $e');
      return 0;
    }
  }

  Future<int> getMessagesCount(int sellerId) async {
    return 0; // Messages not counted from desktop
  }

  Future<int> getUnreadMessagesCount(int sellerId) async {
    return 0;
  }

  Future<int> getCartCount(int userId) async {
    try {
      final items = await getCartItems(userId);
      return items.length;
    } catch (e) {
      print('❌ Error getting cart count: $e');
      return 0;
    }
  }

  Future<int> getOrdersCount(int sellerId) async {
    try {
      final orders = await getOrders(sellerId);
      return orders.length;
    } catch (e) {
      print('❌ Error getting orders count: $e');
      return 0;
    }
  }

  Future<int> getCategoriesCount(int sellerId) async {
    try {
      final categories = await getCategories(sellerId);
      return categories.length;
    } catch (e) {
      print('❌ Error getting categories count: $e');
      return 0;
    }
  }

  Future<int> getCustomersCount(int sellerId) async {
    try {
      final customers = await getCreditCustomers(sellerId);
      return customers.length;
    } catch (e) {
      print('❌ Error getting customers count: $e');
      return 0;
    }
  }

  // ==================== Credit Customer Functions ====================

  Future<List<CreditCustomer>> getCreditCustomers(int sellerId) async {
    try {
      print('📥 Fetching credit customers for seller: $sellerId');
      final results = await postgresService.getCreditCustomers(sellerId).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب الزبائن الآجلين');
          return [];
        }
      );
      
      print('📊 Received ${results.length} credit customers from database');
      
      final customers = results.map((row) {
        print('🔍 Processing customer: ${row['FullName']}');
        
        // Handle CreatedAt - convert DateTime to String if needed
        String? createdAt = row['CreatedAt'] != null 
          ? (row['CreatedAt'] is DateTime 
              ? (row['CreatedAt'] as DateTime).toString() 
              : row['CreatedAt'] as String?)
          : null;
        
        return CreditCustomer(
          customerId: row['CustomerID'] ?? 0,
          sellerId: row['SellerID'] ?? sellerId,
          fullName: row['FullName'] ?? '',
          phoneNumber: row['PhoneNumber'],
          telegramId: row['TelegramID'],
          createdAt: createdAt,
        );
      }).toList();
      
      print('✅ Successfully mapped ${customers.length} credit customers');
      return customers;
    } catch (e) {
      print('❌ Error fetching credit customers: $e');
      print('❌ Stack trace: $e');
      return [];
    }
  }

  Future<int?> addCreditCustomer(int sellerId, String fullName,
      String phoneNumber,
      {int? telegramId}) async {
    return null; // Managed via Bot
  }

  Future<bool> updateCreditCustomer(int customerId, int sellerId,
      String fullName, String? phoneNumber) async {
    return false; // Managed via Bot
  }

  Future<bool> deleteCreditCustomer(int customerId, int sellerId) async {
    return false; // Managed via Bot
  }

  Future<List<CustomerCreditTransaction>> getCustomerTransactions(
      int customerId) async {
    try {
      print('═══════════════════════════════════════════');
      print('📊 جاري جلب معاملات الزبون $customerId...');
      print('═══════════════════════════════════════════');
      
      final transactions = await postgresService.getCustomerTransactions(customerId).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب المعاملات');
          return [];
        }
      );
      
      print('📊 تم جلب ${transactions.length} معاملة');
      
      final result = transactions.map((row) {
        print('🔍 معالجة المعاملة:');
        print('   نوع: ${row['transactiontype']}');
        print('   المبلغ: ${row['amount']}');
        print('   التاريخ: ${row['transactiondate']}');
        
        // تحويل transactiondate إلى String
        String? transactionDateStr;
        final dateValue = row['transactiondate'];
        if (dateValue is DateTime) {
          transactionDateStr = dateValue.toIso8601String();
        } else if (dateValue is String) {
          transactionDateStr = dateValue;
        }
        
        return CustomerCreditTransaction(
          creditId: row['creditid'] as int? ?? 0,
          customerId: row['customerid'] as int? ?? customerId,
          sellerId: row['sellerid'] as int? ?? 0,
          transactionType: row['transactiontype'] as String? ?? '',
          amount: (row['amount'] as num?)?.toDouble() ?? 0,
          description: row['description'] as String?,
          balanceBefore: (row['balancebefore'] as num?)?.toDouble(),
          balanceAfter: (row['balanceafter'] as num?)?.toDouble(),
          transactionDate: transactionDateStr,
        );
      }).toList();
      
      print('✅ تم جلب المعاملات بنجاح');
      print('═══════════════════════════════════════════');
      return result;
    } catch (e) {
      print('❌ خطأ في جلب معاملات الزبون: $e');
      print('Stack: $e');
      return [];
    }
  }

  Future<void> addCreditTransaction({
    required int customerId,
    required int sellerId,
    required String transactionType,
    required double amount,
    String? description,
  }) async {
    try {
      print('═══════════════════════════════════════════');
      print('💳 جاري إضافة معاملة ائتمانية...');
      print('   الزبون: $customerId');
      print('   المتجر: $sellerId');
      print('   النوع: $transactionType');
      print('   المبلغ: $amount');
      print('═══════════════════════════════════════════');
      
      // الحصول على الرصيد الحالي
      final currentBalance = await postgresService.getCustomerBalance(customerId, sellerId);
      
      double balanceBefore = currentBalance ?? 0;
      double balanceAfter = balanceBefore;
      
      // حساب الرصيد بعد المعاملة
      if (transactionType == 'credit') {
        balanceAfter = balanceBefore + amount; // دين جديد (شراء آجل)
      } else if (transactionType == 'payment') {
        balanceAfter = balanceBefore - amount; // دفع (تسديد)
      }
      
      print('💰 الرصيد قبل: $balanceBefore');
      print('💰 الرصيد بعد: $balanceAfter');
      
      // إضافة المعاملة إلى قاعدة البيانات
      final result = await postgresService.addCreditTransaction(
        customerId: customerId,
        sellerId: sellerId,
        transactionType: transactionType,
        amount: amount,
        description: description ?? (transactionType == 'payment' ? 'تسديد نقدي' : 'شراء آجل'),
        balanceBefore: balanceBefore,
        balanceAfter: balanceAfter,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة إضافة المعاملة');
          return 0;
        }
      );
      
      if (result > 0) {
        print('✅ تمت إضافة المعاملة بنجاح (CreditID: $result)');
      } else {
        print('⚠️ فشل إضافة المعاملة');
      }
      print('═══════════════════════════════════════════');
    } catch (e) {
      print('❌ خطأ في إضافة المعاملة الائتمانية: $e');
      print('Stack: $e');
      rethrow;
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
      print('═══════════════════════════════════════════');
      print('✏️ جاري تعديل المعاملة $creditId...');
      print('   النوع: $transactionType');
      print('   المبلغ: $amount');
      print('═══════════════════════════════════════════');
      
      final result = await postgresService.updateCreditTransaction(
        creditId: creditId,
        transactionType: transactionType,
        amount: amount,
        description: description,
        balanceBefore: balanceBefore,
        balanceAfter: balanceAfter,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة تعديل المعاملة');
          return false;
        }
      );
      
      if (result) {
        print('✅ تم تعديل المعاملة بنجاح');
      } else {
        print('⚠️ فشل تعديل المعاملة');
      }
      print('═══════════════════════════════════════════');
      return result;
    } catch (e) {
      print('❌ خطأ في تعديل المعاملة: $e');
      print('Stack: $e');
      return false;
    }
  }

  Future<bool> deleteCreditTransaction(int creditId) async {
    try {
      print('═══════════════════════════════════════════');
      print('🗑️ جاري حذف المعاملة $creditId...');
      print('═══════════════════════════════════════════');
      
      final result = await postgresService.deleteCreditTransaction(creditId).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة حذف المعاملة');
          return false;
        }
      );
      
      if (result) {
        print('✅ تم حذف المعاملة بنجاح');
      } else {
        print('⚠️ فشل حذف المعاملة');
      }
      print('═══════════════════════════════════════════');
      return result;
    } catch (e) {
      print('❌ خطأ في حذف المعاملة: $e');
      print('Stack: $e');
      return false;
    }
  }

  Future<CreditCustomer?> getCreditCustomerByPhone(
      int sellerId, String phoneNumber) async {
    return null;
  }

  Future<bool> isCustomerRegisteredForStore(
      int sellerId, String phoneNumber) async {
    return false;
  }

  Future<bool> isCustomerRegisteredForStoreByTelegramId(
      int sellerId, int telegramId) async {
    return false;
  }

  // ==================== Message Functions ====================

  Future<void> addMessage(int orderId, int sellerId, String messageType,
      String messageText) async {
    // Messages managed via Bot
  }

  Future<List<Message>> getMessages(int sellerId) async {
    try {
      print('═══════════════════════════════════════════');
      print('📬 جاري جلب الرسائل للمتجر $sellerId...');
      print('═══════════════════════════════════════════');
      
      final result = await postgresService.getMessages(sellerId).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          print('⏱️ انتهت مهلة جلب الرسائل');
          return [];
        }
      );
      
      print('📊 تم استقبال ${result.length} رسالة من قاعدة البيانات');
      print('═══════════════════════════════════════════');
      
      if (result.isEmpty) {
        print('⚠️ لا توجد رسائل لـ Seller ID: $sellerId');
        return [];
      }
      
      final messages = result.map((row) {
        print('🔍 معالجة الرسالة:');
        print('   Type: ${row['MessageType']}');
        print('   Order: ${row['OrderID']}');
        print('   Text: ${row['MessageText']?.toString().substring(0, 30)}...');
        print('   Created: ${row['CreatedAt']}');
        
        return Message.fromMap({
          'MessageID': row['MessageID'],
          'OrderID': row['OrderID'],
          'SellerID': row['SellerID'],
          'MessageType': row['MessageType'],
          'MessageText': row['MessageText'],
          'IsRead': row['IsRead'] ?? false,
          'CreatedAt': row['CreatedAt'],
        });
      }).toList();
      
      print('✅ تم جلب ${messages.length} رسالة بنجاح');
      print('═══════════════════════════════════════════');
      return messages;
    } catch (e) {
      print('❌ Error fetching messages: $e');
      print('Stack: $e');
      return [];
    }
  }

  Future<void> markMessageAsRead(int messageId) async {
    // Managed via Bot
  }

  Future<void> deleteMessage(int messageId) async {
    // Managed via Bot
  }

  Future<void> deleteMessageByOrderId(int orderId) async {
    // Managed via Bot
  }

  Future<void> addSystemMessage(int orderId, int buyerId, String text) async {
    // Managed via Bot
  }

  // ==================== Cleanup ====================

  Future<void> close() async {
    await postgresService.close();
    print("🔒 Database Closed");
  }
}
