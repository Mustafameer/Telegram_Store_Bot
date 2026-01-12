
class User {
  final int? userId;
  final int telegramId;
  final String? userName;
  final String? userType;
  final String? phoneNumber;
  final String? fullName;

  User({
    this.userId,
    required this.telegramId,
    this.userName,
    this.userType,
    this.phoneNumber,
    this.fullName,
  });

  factory User.fromMap(Map<String, dynamic> map) {
    return User(
      userId: map['UserID'],
      telegramId: map['TelegramID'],
      userName: map['UserName'],
      userType: map['UserType'],
      phoneNumber: map['PhoneNumber'],
      fullName: map['FullName'],
    );
  }
}

class Seller {
  final int sellerId;
  final int telegramId;
  final String? userName;
  final String? storeName;
  final String? status;
  final String? imagePath;
  final bool requireCustomerRegistration;

  Seller({
    required this.sellerId,
    required this.telegramId,
    this.userName,
    this.storeName,
    this.status,
    this.imagePath,
    this.requireCustomerRegistration = false,
  });

  factory Seller.fromMap(Map<String, dynamic> map) {
    final requireCustomerRegistrationValue = map['RequireCustomerRegistration'];
    // Handle different possible values: 1, true, '1', or null/0/false
    final isLocked = requireCustomerRegistrationValue == 1 || 
                     requireCustomerRegistrationValue == true ||
                     requireCustomerRegistrationValue == '1' ||
                     requireCustomerRegistrationValue == 'true';
    
    print("📖 Seller.fromMap: SellerID=${map['SellerID']}, RequireCustomerRegistration=$requireCustomerRegistrationValue -> isLocked=$isLocked");
    
    return Seller(
      sellerId: map['SellerID'],
      telegramId: map['TelegramID'],
      userName: map['UserName'],
      storeName: map['StoreName'],
      status: map['Status'],
      imagePath: map['ImagePath'],
      requireCustomerRegistration: isLocked,
    );
  }

  Seller copyWith({
    int? sellerId,
    int? telegramId,
    String? userName,
    String? storeName,
    String? status,
    String? imagePath,
    bool? requireCustomerRegistration,
  }) {
    return Seller(
      sellerId: sellerId ?? this.sellerId,
      telegramId: telegramId ?? this.telegramId,
      userName: userName ?? this.userName,
      storeName: storeName ?? this.storeName,
      status: status ?? this.status,
      imagePath: imagePath ?? this.imagePath,
      // Use explicit check to allow false values
      requireCustomerRegistration: requireCustomerRegistration != null 
          ? requireCustomerRegistration 
          : this.requireCustomerRegistration,
    );
  }
}

class Category {
  final int categoryId;
  final int sellerId;
  final String name;
  final int orderIndex;
  final String? imagePath;

  Category({
    required this.categoryId,
    required this.sellerId,
    required this.name,
    this.orderIndex = 0,
    this.imagePath,
  });

  factory Category.fromMap(Map<String, dynamic> map) {
    return Category(
      categoryId: map['CategoryID'],
      sellerId: map['SellerID'],
      name: map['Name'],
      orderIndex: map['OrderIndex'] ?? 0,
      imagePath: map['ImagePath'],
    );
  }
}

class Product {
  final int productId;
  final int sellerId;
  final int? categoryId;
  final String name;
  final String? description;
  final double price;
  final double? wholesalePrice;
  final int quantity;
  final String? imagePath;
  final String status;

  Product({
    required this.productId,
    required this.sellerId,
    this.categoryId,
    required this.name,
    this.description,
    required this.price,
    this.wholesalePrice,
    required this.quantity,
    this.imagePath,
    this.status = 'active',
  });

  factory Product.fromMap(Map<String, dynamic> map) {
    return Product(
      productId: map['ProductID'],
      sellerId: map['SellerID'],
      categoryId: map['CategoryID'],
      name: map['Name'],
      description: map['Description'],
      price: (map['Price'] as num).toDouble(),
      wholesalePrice: map['WholesalePrice'] != null ? (map['WholesalePrice'] as num).toDouble() : null,
      quantity: map['Quantity'],
      imagePath: map['ImagePath'],
      status: map['Status'] ?? 'active',
    );
  }

  Product copyWith({
    int? productId,
    int? sellerId,
    int? categoryId,
    String? name,
    String? description,
    double? price,
    double? wholesalePrice,
    int? quantity,
    String? imagePath,
    String? status,
  }) {
    return Product(
      productId: productId ?? this.productId,
      sellerId: sellerId ?? this.sellerId,
      categoryId: categoryId ?? this.categoryId,
      name: name ?? this.name,
      description: description ?? this.description,
      price: price ?? this.price,
      wholesalePrice: wholesalePrice ?? this.wholesalePrice,
      quantity: quantity ?? this.quantity,
      imagePath: imagePath ?? this.imagePath,
      status: status ?? this.status,
    );
  }
}

class Order {
  final int orderId;
  final int? buyerId;
  final int sellerId;
  final double total;
  final String status;
  final String createdAt;
  final String? deliveryAddress;
  final String? notes;
  final String paymentMethod;
  final bool fullyPaid;

  Order({
    required this.orderId,
    this.buyerId,
    required this.sellerId,
    required this.total,
    this.status = 'Pending',
    required this.createdAt,
    this.deliveryAddress,
    this.notes,
    this.paymentMethod = 'cash',
    this.fullyPaid = false,
  });

  factory Order.fromMap(Map<String, dynamic> map) {
    return Order(
      orderId: map['OrderID'],
      buyerId: map['BuyerID'],
      sellerId: map['SellerID'],
      total: (map['Total'] as num?)?.toDouble() ?? 0.0,
      status: map['Status'] ?? 'Pending',
      createdAt: map['CreatedAt'] ?? '',
      deliveryAddress: map['DeliveryAddress'],
      notes: map['Notes'],
      paymentMethod: map['PaymentMethod'] ?? 'cash',
      fullyPaid: (map['FullyPaid'] == 1 || map['FullyPaid'] == true),
    );
  }
}

class OrderItem {
  final int orderItemId;
  final int orderId;
  final int productId;
  final int quantity;
  final double price;

  OrderItem({
    required this.orderItemId,
    required this.orderId,
    required this.productId,
    required this.quantity,
    required this.price,
  });

  factory OrderItem.fromMap(Map<String, dynamic> map) {
    return OrderItem(
      orderItemId: map['OrderItemID'],
      orderId: map['OrderID'],
      productId: map['ProductID'],
      quantity: map['Quantity'],
      price: (map['Price'] as num).toDouble(),
    );
  }
}

class CreditCustomer {
  final int customerId;
  final int sellerId;
  final String fullName;
  final String? phoneNumber;
  final int? telegramId;
  final String? createdAt;

  CreditCustomer({
    required this.customerId,
    required this.sellerId,
    required this.fullName,
    this.phoneNumber,
    this.telegramId,
    this.createdAt,
  });

  factory CreditCustomer.fromMap(Map<String, dynamic> map) {
    return CreditCustomer(
      customerId: map['CustomerID'],
      sellerId: map['SellerID'],
      fullName: map['FullName'],
      phoneNumber: map['PhoneNumber'],
      telegramId: map['TelegramID'],
      createdAt: map['CreatedAt'],
    );
  }
}

class CustomerCreditTransaction {
  final int creditId;
  final int customerId;
  final int sellerId;
  final String transactionType; // 'credit', 'payment'
  final double amount;
  final String? description;
  final double? balanceBefore;
  final double? balanceAfter;
  final String? transactionDate;

  CustomerCreditTransaction({
    required this.creditId,
    required this.customerId,
    required this.sellerId,
    required this.transactionType,
    required this.amount,
    this.description,
    this.balanceBefore,
    this.balanceAfter,
    this.transactionDate,
  });

  factory CustomerCreditTransaction.fromMap(Map<String, dynamic> map) {
    return CustomerCreditTransaction(
      creditId: map['CreditID'],
      customerId: map['CustomerID'],
      sellerId: map['SellerID'],
      transactionType: map['TransactionType'],
      amount: (map['Amount'] as num).toDouble(),
      description: map['Description'],
      balanceBefore: map['BalanceBefore'] != null ? (map['BalanceBefore'] as num).toDouble() : null,
      balanceAfter: map['BalanceAfter'] != null ? (map['BalanceAfter'] as num).toDouble() : null,
      transactionDate: map['TransactionDate'],
    );
  }
}

class Message {
  final int messageId;
  final int? orderId;
  final int sellerId;
  final String messageType;
  final String? messageText;
  final bool isRead;
  final String? createdAt;

  Message({
    required this.messageId,
    this.orderId,
    required this.sellerId,
    required this.messageType,
    this.messageText,
    this.isRead = false,
    this.createdAt,
  });

  factory Message.fromMap(Map<String, dynamic> map) {
    return Message(
      messageId: map['MessageID'],
      orderId: map['OrderID'],
      sellerId: map['SellerID'],
      messageType: map['MessageType'],
      messageText: map['MessageText'],
      isRead: (map['IsRead'] == 1 || map['IsRead'] == true),
      createdAt: map['CreatedAt'],
    );
  }
}

class ProductImage {
  final int imageId;
  final int productId;
  final String imagePath;
  final int imageOrder;
  final String? createdAt;

  ProductImage({
    required this.imageId,
    required this.productId,
    required this.imagePath,
    this.imageOrder = 0,
    this.createdAt,
  });

  factory ProductImage.fromMap(Map<String, dynamic> map) {
    return ProductImage(
      imageId: map['ImageID'],
      productId: map['ProductID'],
      imagePath: map['ImagePath'],
      imageOrder: map['ImageOrder'] ?? 0,
      createdAt: map['CreatedAt'],
    );
  }
}

