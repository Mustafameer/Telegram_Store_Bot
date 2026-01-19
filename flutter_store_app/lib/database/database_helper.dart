import 'dart:io';
import 'dart:typed_data';
import 'package:path/path.dart' as p;
import '../models/database_models.dart';
import 'database_helper_cloud.dart';

// ============================================================
// This file now delegates to Cloud PostgreSQL Backend
// All database operations use PostgreSQL via PostgresService
// ============================================================

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  late DatabaseHelperCloud _cloudHelper;

  DatabaseHelper._init() {
    _cloudHelper = DatabaseHelperCloud();
  }

  factory DatabaseHelper() => instance;

  /// Initialize cloud database connection
  Future<void> initialize() async {
    await _cloudHelper.initialize();
  }

  // ==================== Seller Functions ====================

  Future<List<Seller>> getAllSellers({bool forceRefresh = false}) async {
    return await _cloudHelper.getAllSellers(forceRefresh: forceRefresh);
  }

  Future<Seller?> getSellerByTelegramId(int telegramId) async {
    return await _cloudHelper.getSellerByTelegramId(telegramId);
  }

  Future<Seller?> getSellerById(int sellerId) async {
    return await _cloudHelper.getSellerById(sellerId);
  }

  Future<User?> getUserByTelegramId(int telegramId) async {
    return await _cloudHelper.getUserByTelegramId(telegramId);
  }

  Future<void> addSeller(String storeName, int telegramId, String userName,
      {String? imagePath}) async {
    return await _cloudHelper.addSeller(storeName, telegramId, userName,
        imagePath: imagePath);
  }

  Future<void> updateSeller(Seller seller) async {
    return await _cloudHelper.updateSeller(seller);
  }

  Future<void> updateSellerStatus(int sellerId, String status) async {
    return await _cloudHelper.updateSellerStatus(sellerId, status);
  }

  Future<void> deleteSeller(int sellerId) async {
    return await _cloudHelper.deleteSeller(sellerId);
  }

  // ==================== Category Functions ====================

  Future<List<Category>> getCategories(int sellerId,
      {bool forceRefresh = false}) async {
    return await _cloudHelper.getCategories(sellerId,
        forceRefresh: forceRefresh);
  }
  Future<void> ensureCategorySchema() async {
    return await _cloudHelper.ensureCategorySchema();
  }

  Future<int?> addCategory(Category category) async {
    return await _cloudHelper.addCategory(category);
  }

  Future<void> updateCategory(Category category) async {
    return await _cloudHelper.updateCategory(category);
  }

  Future<void> deleteCategory(int categoryId) async {
    return await _cloudHelper.deleteCategory(categoryId);
  }

  // ==================== Product Functions ====================

  Future<List<Product>> getProducts(int sellerId,
      {int? categoryId, bool forceRefresh = false}) async {
    return await _cloudHelper.getProducts(sellerId,
        categoryId: categoryId, forceRefresh: forceRefresh);
  }

  Future<void> addProduct(Product product) async {
    return await _cloudHelper.addProduct(product);
  }

  Future<void> updateProduct(Product product) async {
    return await _cloudHelper.updateProduct(product);
  }

  Future<void> deleteProduct(int productId) async {
    return await _cloudHelper.deleteProduct(productId);
  }

  // ==================== Product Images Functions ====================

  Future<List<ProductImage>> getProductImages(int productId) async {
    return await _cloudHelper.getProductImages(productId);
  }

  Future<int> addProductImage(int productId, String imagePath,
      {int imageOrder = 0}) async {
    return await _cloudHelper.addProductImage(productId, imagePath,
        imageOrder: imageOrder);
  }

  Future<void> deleteProductImage(int imageId) async {
    return await _cloudHelper.deleteProductImage(imageId);
  }

  // ==================== Cart Functions ====================

  Future<void> addToCart(int userId, int productId, int quantity,
      double price) async {
    return await _cloudHelper.addToCart(userId, productId, quantity, price);
  }

  Future<void> addToCartWithImages(int userId, int productId, int quantity,
      double price, List<int> imageIds) async {
    return await _cloudHelper.addToCartWithImages(
        userId, productId, quantity, price, imageIds);
  }

  Future<List<Map<String, dynamic>>> getCartItems(int userId) async {
    return await _cloudHelper.getCartItems(userId);
  }

  Future<List<ProductImage>> getCartImages(int cartId) async {
    return await _cloudHelper.getCartImages(cartId);
  }

  Future<void> updateCartQuantity(int cartId, int quantity) async {
    return await _cloudHelper.updateCartQuantity(cartId, quantity);
  }

  Future<void> removeFromCart(int cartId) async {
    return await _cloudHelper.removeFromCart(cartId);
  }

  Future<void> clearCart(int userId) async {
    return await _cloudHelper.clearCart(userId);
  }

  // ==================== Order Functions ====================

  Future<List<Order>> getOrders(int sellerId) async {
    return await _cloudHelper.getOrders(sellerId);
  }

  Future<void> updateOrderStatus(int orderId, String status) async {
    return await _cloudHelper.updateOrderStatus(orderId, status);
  }

  Future<int> createOrder(int buyerId, int sellerId, double total,
      String address, String notes, List<Map<String, dynamic>> items, {
      String status = 'pending',
      String paymentMethod = 'cash',
      bool fullyPaid = false
    }) async {
    return await _cloudHelper.createOrder(
        buyerId, sellerId, total, address, notes, items,
        status: status,
        paymentMethod: paymentMethod,
        fullyPaid: fullyPaid);
  }

  Future<List<Map<String, dynamic>>> getItemsForOrder(int orderId) async {
    return await _cloudHelper.getItemsForOrder(orderId);
  }

  Future<List<ProductImage>> getOrderItemImages(int orderItemId) async {
    return await _cloudHelper.getOrderItemImages(orderItemId);
  }

  Future<void> deleteOrder(int orderId) async {
    return await _cloudHelper.deleteOrder(orderId);
  }

  Future<List<Map<String, dynamic>>> getDeletedItems() async {
    return await _cloudHelper.getDeletedItems();
  }

  Future<void> clearDeletedItems(List<int> ids) async {
    return await _cloudHelper.clearDeletedItems(ids);
  }

  Future<void> deductStockForOrder(int orderId) async {
    return await _cloudHelper.deductStockForOrder(orderId);
  }

  // ==================== Counting Functions ====================

  Future<int> getProductsCount(int sellerId) async {
    return await _cloudHelper.getProductsCount(sellerId);
  }

  Future<int> getMessagesCount(int sellerId) async {
    return await _cloudHelper.getMessagesCount(sellerId);
  }

  Future<int> getUnreadMessagesCount(int sellerId) async {
    return await _cloudHelper.getUnreadMessagesCount(sellerId);
  }

  Future<int> getCartCount(int userId) async {
    return await _cloudHelper.getCartCount(userId);
  }

  Future<int> getOrdersCount(int sellerId) async {
    return await _cloudHelper.getOrdersCount(sellerId);
  }

  Future<int> getCategoriesCount(int sellerId) async {
    return await _cloudHelper.getCategoriesCount(sellerId);
  }

  Future<int> getCustomersCount(int sellerId) async {
    return await _cloudHelper.getCustomersCount(sellerId);
  }

  // ==================== Credit Customer Functions ====================

  Future<List<CreditCustomer>> getCreditCustomers(int sellerId) async {
    return await _cloudHelper.getCreditCustomers(sellerId);
  }

  Future<int?> addCreditCustomer(int sellerId, String fullName,
      String phoneNumber,
      {int? telegramId}) async {
    return await _cloudHelper.addCreditCustomer(sellerId, fullName,
        phoneNumber,
        telegramId: telegramId);
  }

  Future<bool> updateCreditCustomer(int customerId, int sellerId,
      String fullName, String? phoneNumber) async {
    return await _cloudHelper.updateCreditCustomer(
        customerId, sellerId, fullName, phoneNumber);
  }

  Future<bool> deleteCreditCustomer(int customerId, int sellerId) async {
    return await _cloudHelper.deleteCreditCustomer(customerId, sellerId);
  }

  Future<List<CustomerCreditTransaction>> getCustomerTransactions(
      int customerId) async {
    return await _cloudHelper.getCustomerTransactions(customerId);
  }

  Future<void> addCreditTransaction({
    required int customerId,
    required int sellerId,
    required String transactionType,
    required double amount,
    String? description,
  }) async {
    return await _cloudHelper.addCreditTransaction(
      customerId: customerId,
      sellerId: sellerId,
      transactionType: transactionType,
      amount: amount,
      description: description,
    );
  }

  Future<bool> updateCreditTransaction({
    required int creditId,
    required String transactionType,
    required double amount,
    String? description,
    required double balanceBefore,
    required double balanceAfter,
  }) async {
    return await _cloudHelper.updateCreditTransaction(
      creditId: creditId,
      transactionType: transactionType,
      amount: amount,
      description: description,
      balanceBefore: balanceBefore,
      balanceAfter: balanceAfter,
    );
  }

  Future<bool> deleteCreditTransaction(int creditId) async {
    return await _cloudHelper.deleteCreditTransaction(creditId);
  }

  Future<CreditCustomer?> getCreditCustomerByPhone(
      int sellerId, String phoneNumber) async {
    return await _cloudHelper.getCreditCustomerByPhone(
        sellerId, phoneNumber);
  }

  Future<bool> isCustomerRegisteredForStore(
      int sellerId, String phoneNumber) async {
    return await _cloudHelper.isCustomerRegisteredForStore(
        sellerId, phoneNumber);
  }

  Future<bool> isCustomerRegisteredForStoreByTelegramId(
      int sellerId, int telegramId) async {
    return await _cloudHelper.isCustomerRegisteredForStoreByTelegramId(
        sellerId, telegramId);
  }

  // ==================== Message Functions ====================

  Future<void> addMessage(int orderId, int sellerId, String messageType,
      String messageText) async {
    return await _cloudHelper.addMessage(
        orderId, sellerId, messageType, messageText);
  }

  Future<List<Message>> getMessages(int sellerId) async {
    return await _cloudHelper.getMessages(sellerId);
  }

  Future<void> markMessageAsRead(int messageId) async {
    return await _cloudHelper.markMessageAsRead(messageId);
  }

  Future<void> deleteMessage(int messageId) async {
    return await _cloudHelper.deleteMessage(messageId);
  }

  Future<void> deleteMessageByOrderId(int orderId) async {
    return await _cloudHelper.deleteMessageByOrderId(orderId);
  }

  Future<void> addSystemMessage(int orderId, int buyerId, String text) async {
    return await _cloudHelper.addSystemMessage(orderId, buyerId, text);
  }

  // ==================== Cleanup ====================

  Future<void> close() async {
    return await _cloudHelper.close();
  }

  // ==================== Image Functions ====================

  Future<Uint8List?> getImageData(String fileName) async {
    return await _cloudHelper.getImageData(fileName);
  }

  Future<String?> getImageUrl(String fileName) async {
    return await _cloudHelper.getImageUrl(fileName);
  }

  // ==================== Compatibility Methods (Legacy SQLite) ====================
  // These methods are kept for backward compatibility with old code
  // that still references DatabaseHelper.database or getDbPath()

  /// Legacy getter for SQLite database - returns null as we now use PostgreSQL
  /// Kept for backward compatibility with old sync_service.dart
  Future<dynamic> get database async {
    // This is a compatibility shim - returning null as we use PostgreSQL now
    print('⚠️ Warning: Accessing database getter is deprecated. Use PostgresService instead.');
    return null;
  }

  /// Get database file path - kept for backward compatibility
  /// Returns a dummy path as we now use cloud PostgreSQL
  Future<String> getDbPath() async {
    print('⚠️ Warning: getDbPath() is deprecated. Using PostgreSQL cloud database.');
    return '/dev/null'; // Dummy path since we use PostgreSQL
  }
}
