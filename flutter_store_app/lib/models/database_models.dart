
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
      userId: map['userid'],
      telegramId: map['telegramid'],
      userName: map['username'],
      userType: map['usertype'],
      phoneNumber: map['phonenumber'],
      fullName: map['fullname'],
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
      sellerId: map['sellerid'],
      telegramId: map['telegramid'],
      userName: map['username'],
      storeName: map['storename'],
      status: map['status'],
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
      categoryId: map['categoryid'],
      sellerId: map['sellerid'],
      name: map['name'],
      orderIndex: map['orderindex'] ?? 0,
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
      productId: map['productid'],
      sellerId: map['sellerid'],
      categoryId: map['categoryid'],
      name: map['name'],
      description: map['description'],
      price: (map['price'] as num).toDouble(),
      wholesalePrice: map['wholesaleprice'] != null ? (map['wholesaleprice'] as num).toDouble() : null,
      quantity: map['quantity'],
      imagePath: map['imagepath'],
      status: map['status'] ?? 'active',
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
      orderId: map['orderid'],
      buyerId: map['buyerid'],
      sellerId: map['sellerid'],
      total: (map['total'] as num).toDouble(),
      status: map['status'] ?? 'Pending',
      createdAt: map['createdat'],
      deliveryAddress: map['deliveryaddress'],
      notes: map['notes'],
      paymentMethod: map['paymentmethod'] ?? 'cash',
      fullyPaid: (map['fullypaid'] == 1 || map['fullypaid'] == true),
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
      orderItemId: map['orderitemid'],
      orderId: map['orderid'],
      productId: map['productid'],
      quantity: map['quantity'],
      price: (map['price'] as num).toDouble(),
    );
  }
}
