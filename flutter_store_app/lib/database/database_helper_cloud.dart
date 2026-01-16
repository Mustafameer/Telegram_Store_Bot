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
      return await postgresService.getCategories(sellerId);
    } catch (e) {
      print('❌ Error getting categories: $e');
      return [];
    }
  }

  Future<void> ensureCategorySchema() async {
    // No-op for cloud database
  }

  Future<void> addCategory(Category category) async {
    try {
      // Categories are managed via Bot
      print('⚠️ addCategory: Categories managed via Bot');
    } catch (e) {
      print('❌ Error adding category: $e');
      rethrow;
    }
  }

  Future<void> updateCategory(Category category) async {
    try {
      // Categories are managed via Bot
      print('⚠️ updateCategory: Categories managed via Bot');
    } catch (e) {
      print('❌ Error updating category: $e');
      rethrow;
    }
  }

  Future<void> deleteCategory(int categoryId) async {
    try {
      // Categories are managed via Bot
      print('⚠️ deleteCategory: Categories managed via Bot');
    } catch (e) {
      print('❌ Error deleting category: $e');
      rethrow;
    }
  }

  // ==================== Product Functions ====================

  Future<List<Product>> getProducts(int sellerId, {int? categoryId, bool forceRefresh = false}) async {
    try {
      return await postgresService.getProducts(sellerId, categoryId);
    } catch (e) {
      print('❌ Error getting products: $e');
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
      final images = await postgresService.getProductImages(productId);
      return images
          .map((img) => ProductImage(
                imageId: img['imageid'],
                productId: img['productid'],
                imagePath: img['imagepath'],
                imageOrder: 0,
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
      return await postgresService.getImageData(fileName);
    } catch (e) {
      print('❌ Error getting image data: $e');
      return null;
    }
  }

  Future<int> addProductImage(int productId, String imagePath,
      {int imageOrder = 0}) async {
    try {
      // Upload image file to ImageStorage table
      final file = File(imagePath);
      if (!file.existsSync()) {
        throw Exception('Image file not found: $imagePath');
      }
      
      // Read file bytes
      final fileBytes = await file.readAsBytes();
      
      // Generate timestamped filename to match bot's naming convention
      // Format: {timestamp}_{uuid}{ext}
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000; // Unix timestamp
      final uuid = const Uuid().v4().replaceAll('-', '').substring(0, 32); // 32-char hex
      final ext = p.extension(imagePath); // Get file extension
      final fileName = '${timestamp}_$uuid$ext';
      
      print('📤 Uploading image to cloud: $fileName (${fileBytes.length} bytes)');
      
      // Upload to ImageStorage table via PostgreSQL
      final result = await postgresService.uploadImageToStorage(fileName, fileBytes);
      
      if (result > 0) {
        print('✅ Image uploaded successfully: $fileName');
        
        // Insert ProductImage entry with the generated filename
        final imageId = await postgresService.addProductImage(productId, fileName, imageOrder);
        return imageId ?? 0;
      } else {
        throw Exception('Failed to upload image to storage');
      }
    } catch (e) {
      print('❌ Error adding product image: $e');
      rethrow;
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
      return await postgresService.getUserOrders(sellerId);
    } catch (e) {
      print('❌ Error getting orders: $e');
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
      String address, String notes, List<Map<String, dynamic>> items) async {
    try {
      final orderId = await postgresService.createOrder(
        buyerId: buyerId,
        sellerId: sellerId,
        total: total,
        status: 'pending',
        paymentMethod: 'cash',
        deliveryAddress: address,
        notes: notes,
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
    return 0; // Credit customers managed via Bot
  }

  // ==================== Credit Customer Functions ====================

  Future<List<CreditCustomer>> getCreditCustomers(int sellerId) async {
    return []; // Managed via Bot
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
    return [];
  }

  Future<void> addCreditTransaction({
    required int customerId,
    required int sellerId,
    required String transactionType,
    required double amount,
    String? description,
  }) async {
    // Managed via Bot
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
    return [];
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
