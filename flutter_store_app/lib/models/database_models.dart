
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

  Seller({
    required this.sellerId,
    required this.telegramId,
    this.userName,
    this.storeName,
    this.status,
  });

  factory Seller.fromMap(Map<String, dynamic> map) {
    return Seller(
      sellerId: map['SellerID'],
      telegramId: map['TelegramID'],
      userName: map['UserName'],
      storeName: map['StoreName'],
      status: map['Status'],
    );
  }
}

class Category {
  final int categoryId;
  final int sellerId;
  final String name;
  final int orderIndex;

  Category({
    required this.categoryId,
    required this.sellerId,
    required this.name,
    this.orderIndex = 0,
  });

  factory Category.fromMap(Map<String, dynamic> map) {
    return Category(
      categoryId: map['CategoryID'],
      sellerId: map['SellerID'],
      name: map['Name'],
      orderIndex: map['OrderIndex'] ?? 0,
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
      total: (map['Total'] as num).toDouble(),
      status: map['Status'] ?? 'Pending',
      createdAt: map['CreatedAt'],
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
