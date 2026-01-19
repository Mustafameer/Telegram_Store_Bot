import 'package:intl/intl.dart';

class AppNotification {
  final int notificationId;
  final int customerTelegramId;
  final int? sellerId;
  final String type;
  final String title;
  final String message;
  final String? productNames;
  final double? totalAmount;
  final bool isRead;
  final DateTime? createdAt;
  final DateTime? readAt;
  final Map<String, dynamic>? data;
  
  AppNotification({
    required this.notificationId,
    required this.customerTelegramId,
    this.sellerId,
    required this.type,
    required this.title,
    required this.message,
    this.productNames,
    this.totalAmount,
    required this.isRead,
    this.createdAt,
    this.readAt,
    this.data,
  });
  
  /// إنشء AppNotification من JSON
  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      notificationId: json['notificationId'] ?? 0,
      customerTelegramId: json['customerTelegramId'] ?? 0,
      sellerId: json['sellerId'],
      type: json['type'] ?? '',
      title: json['title'] ?? '',
      message: json['message'] ?? '',
      productNames: json['productNames'],
      totalAmount: json['totalAmount'] is num 
        ? (json['totalAmount'] as num).toDouble()
        : null,
      isRead: json['isRead'] ?? false,
      createdAt: json['createdAt'] != null 
        ? DateTime.tryParse(json['createdAt'])
        : null,
      readAt: json['readAt'] != null 
        ? DateTime.tryParse(json['readAt'])
        : null,
      data: json['data'] as Map<String, dynamic>?,
    );
  }
  
  /// تحويل إلى JSON
  Map<String, dynamic> toJson() {
    return {
      'notificationId': notificationId,
      'customerTelegramId': customerTelegramId,
      'sellerId': sellerId,
      'type': type,
      'title': title,
      'message': message,
      'productNames': productNames,
      'totalAmount': totalAmount,
      'isRead': isRead,
      'createdAt': createdAt?.toIso8601String(),
      'readAt': readAt?.toIso8601String(),
      'data': data,
    };
  }
  
  /// الحصول على وقت الإشعار بصيغة قابلة للقراءة
  String getFormattedTime() {
    if (createdAt == null) return '';
    
    final now = DateTime.now();
    final difference = now.difference(createdAt!);
    
    if (difference.inSeconds < 60) {
      return 'الآن';
    } else if (difference.inMinutes < 60) {
      return 'قبل ${difference.inMinutes} دقيقة';
    } else if (difference.inHours < 24) {
      return 'قبل ${difference.inHours} ساعة';
    } else if (difference.inDays < 7) {
      return 'قبل ${difference.inDays} أيام';
    } else {
      return DateFormat('dd/MM/yyyy HH:mm').format(createdAt!);
    }
  }
  
  /// الحصول على أيقونة الإشعار بناء على النوع
  String getIcon() {
    switch (type) {
      case 'closed_store_purchase':
        return '✅';
      case 'refund':
        return '💰';
      case 'new_product':
        return '🆕';
      case 'promotion':
        return '🎉';
      default:
        return 'ℹ️';
    }
  }
  
  /// الحصول على اللون بناء على نوع الإشعار
  String getColor() {
    switch (type) {
      case 'closed_store_purchase':
        return '#4CAF50'; // أخضر
      case 'refund':
        return '#2196F3'; // أزرق
      case 'new_product':
        return '#FF9800'; // برتقالي
      case 'promotion':
        return '#E91E63'; // وردي
      default:
        return '#9E9E9E'; // رمادي
    }
  }
  
  /// نسخ الإشعار مع تعديلات اختيارية
  AppNotification copyWith({
    int? notificationId,
    int? customerTelegramId,
    int? sellerId,
    String? type,
    String? title,
    String? message,
    String? productNames,
    double? totalAmount,
    bool? isRead,
    DateTime? createdAt,
    DateTime? readAt,
    Map<String, dynamic>? data,
  }) {
    return AppNotification(
      notificationId: notificationId ?? this.notificationId,
      customerTelegramId: customerTelegramId ?? this.customerTelegramId,
      sellerId: sellerId ?? this.sellerId,
      type: type ?? this.type,
      title: title ?? this.title,
      message: message ?? this.message,
      productNames: productNames ?? this.productNames,
      totalAmount: totalAmount ?? this.totalAmount,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt ?? this.createdAt,
      readAt: readAt ?? this.readAt,
      data: data ?? this.data,
    );
  }
  
  @override
  String toString() => 'AppNotification(id: $notificationId, type: $type, title: $title)';
}
