

import 'package:flutter/material.dart';
import 'dart:io';
import 'package:intl/intl.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';
import '../../services/telegram_service.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';

// دالة لتنسيق المبالغ مع فاصلة الآلاف وإزالة الكسور
String formatPrice(dynamic price) {
  if (price == null) return '0';
  final numValue = price is num ? price : double.tryParse(price.toString()) ?? 0;
  final rounded = numValue.round();
  final formatter = NumberFormat('#,###', 'ar');
  return formatter.format(rounded);
}

class OrdersTab extends StatefulWidget {
  final int sellerId;
  final bool isEditable;

  const OrdersTab({
    super.key, 
    required this.sellerId, 
    this.isEditable = false,
  });

  @override
  State<OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<OrdersTab> {
  late Future<List<Order>> _ordersFuture;
  TextEditingController _searchController = TextEditingController();
  List<Order> _allOrders = [];
  List<Order> _filteredOrders = [];

  @override
  void initState() {
    super.initState();
    _refreshOrders();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      if (query.isEmpty) {
        _filteredOrders = _allOrders;
      } else {
        _filteredOrders = _allOrders.where((order) {
          return order.orderId.toString().contains(query) || 
                 order.status.toLowerCase().contains(query) ||
                 order.total.toString().contains(query);
        }).toList();
      }
    });
  }

  void _refreshOrders() {
    setState(() {
      _ordersFuture = DatabaseHelper.instance.getOrders(widget.sellerId).then((orders) {
          _allOrders = orders;
          _filteredOrders = orders;
          // Re-apply search if exists
          if (_searchController.text.isNotEmpty) {
             _onSearchChanged();
          }
          return orders;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Search Bar
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'بحث عن طلب (رقم، حالة، مبلغ)...',
              prefixIcon: const Icon(Icons.search),
              filled: true,
              fillColor: Theme.of(context).cardColor,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0)
            ),
          ),
        ),

        // Orders Grid
        Expanded(
          child: FutureBuilder<List<Order>>(
            future: _ordersFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(child: Text('Error: ${snapshot.error}'));
              }
              if (!snapshot.hasData || _filteredOrders.isEmpty) {
                return const Center(child: Text('لا يوجد طلبات مطابقة'));
              }

              // Use a Masonry grid so each order card can grow vertically
              // to fit its content and avoid overflow. We compute a max
              // cross-axis extent (card width) and let heights be intrinsic.
              final double baseMaxExtent = 250;
              // Add 2 cm to card width when height is variable so content has room.
              // 1 cm ≈ 38 logical pixels, so 2 cm ≈ 76 logical pixels.
              final double extraWidthFor2cm = 76.0; // ~2 cm
              final double newMaxExtent = baseMaxExtent + extraWidthFor2cm;

              return MasonryGridView.extent(
                maxCrossAxisExtent: newMaxExtent,
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                itemCount: _filteredOrders.length,
                itemBuilder: (context, index) {
                  final order = _filteredOrders[index];
                  return _buildOrderCard(context, order);
                },
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildOrderCard(BuildContext context, Order order) {
    bool isPending = order.status.toLowerCase() == 'pending';
    
    // Colors based on Mockup (Dark Theme aesthetics)
    Color cardBg = const Color(0xFF1E1E1E); // Dark Grey/Black
    Color headerBg;
    Color statusTextColor;
    IconData statusIcon;

    switch (order.status.toLowerCase()) {
      case 'pending':
        headerBg = const Color(0xFF3E3014); // Dark Brown/Goldish
        statusTextColor = const Color(0xFFFFA000); // Amber
        statusIcon = Icons.hourglass_top;
        break;
      case 'confirmed':
      case 'accepted':
        headerBg = const Color(0xFF0D2536); // Dark Blue
        statusTextColor = Colors.lightBlueAccent;
        statusIcon = Icons.check_circle_outline;
        break;
      case 'shipped':
        headerBg = const Color(0xFF0F2E22); // Dark Teal
        statusTextColor = Colors.tealAccent;
        statusIcon = Icons.local_shipping;
        break;
      case 'delivered':
        headerBg = const Color(0xFF1B331B); // Dark Green
        statusTextColor = Colors.greenAccent;
        statusIcon = Icons.card_giftcard;
        break;
      default:
        headerBg = const Color(0xFF2C1B1B); // Dark Red
        statusTextColor = Colors.redAccent;
        statusIcon = Icons.cancel_outlined;
    }

    return Card(
      color: cardBg,
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _showOrderDetails(order),
        child: Column(
          children: [
            // 1. Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: headerBg,
              child: Row(
                children: [
                   // RTL: Start from Right
                   // Status Icon (Rightmost)
                   Icon(statusIcon, color: statusTextColor, size: 20),
                   const SizedBox(width: 8),
                   // Status Text
                   Expanded(
                     child: Text(
                       _translateStatus(order.status),
                       style: TextStyle(
                         color: statusTextColor,
                         fontWeight: FontWeight.bold,
                         fontSize: 16,
                         fontFamily: 'Cairo'
                       ),
                       overflow: TextOverflow.ellipsis,
                     ),
                   ),
                   // Order ID (Leftmost)
                   Text(
                     '#${order.orderId}',
                     style: TextStyle(
                       color: statusTextColor,
                       fontWeight: FontWeight.bold,
                       fontSize: 18,
                       fontFamily: 'Cairo'
                     ),
                   ),
                ],
              ),
            ),

            // 2. Info Body
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  // Row: Info (Right) vs Price (Left)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start, 
                    children: [
                      // Info Column (Rightmost in RTL) - make flexible to avoid overflow
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildMockupRow(Icons.calendar_today, order.createdAt.split(' ').first),
                            const SizedBox(height: 4),
                            _buildMockupRow(Icons.phone_android, order.notes?.isNotEmpty == true ? order.notes! : '----------'),
                            const SizedBox(height: 4),
                            _buildMockupRow(Icons.location_on, order.deliveryAddress ?? '---'),
                          ],
                        ),
                      ),

                      // Total Price Pill (Leftmost in RTL)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE1F0FF), // Light Blue
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${formatPrice(order.total)} د.ع', // d.a currency
                          style: const TextStyle(
                            color: Color(0xFF1565C0), // Dark Blue Text
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            fontFamily: 'Cairo'
                          ),
                          textAlign: TextAlign.right,
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 16),
                  const Divider(color: Colors.white24, height: 1),
                  const SizedBox(height: 16),

                  // 3. Products List (Preview first 2)
                  FutureBuilder<List<Map<String, dynamic>>>(
                      future: DatabaseHelper.instance.getItemsForOrder(order.orderId),
                      builder: (context, snapshot) {
                        if (!snapshot.hasData || snapshot.data!.isEmpty) return const SizedBox.shrink();
                        final items = snapshot.data!;
                        
                        return Column(
                          children: [
                             ...items.take(2).map((item) => Padding(
                               padding: const EdgeInsets.only(bottom: 12.0),
                               child: Row(
                                 children: [
                                   // Total Item Price (Left)
                                   Text(
                                     formatPrice(item['Price'] * item['Quantity']),
                                     style: const TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'Cairo'),
                                   ),
                                   
                                   const Spacer(),

                                   // Name & Qty (Right)
                                   Column(
                                     crossAxisAlignment: CrossAxisAlignment.end,
                                     children: [
                                       Text(
                                         item['Name'] ?? '',
                                         style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14, fontFamily: 'Cairo'),
                                         maxLines: 1, overflow: TextOverflow.ellipsis,
                                       ),
                                       Text(
                                         '${formatPrice(item['Price'])} x ${item['Quantity']} د.ع', // Mockup format
                                         style: const TextStyle(color: Colors.grey, fontSize: 12, fontFamily: 'Cairo'),
                                       ),
                                     ],
                                   ),
                                   
                                   const SizedBox(width: 12),

                                   // Image (Rightmost)
                                   Container(
                                     width: 48, height: 48,
                                     decoration: BoxDecoration(
                                       borderRadius: BorderRadius.circular(8),
                                       border: Border.all(color: Colors.white12),
                                       image: item['ImagePath'] != null && File(item['ImagePath']).existsSync()
                                           ? DecorationImage(
                                               image: FileImage(File(item['ImagePath'])),
                                               fit: BoxFit.cover
                                             )
                                           : null,
                                       color: Colors.grey[800]
                                     ),
                                     child: item['ImagePath'] == null ? const Icon(Icons.image, size: 20, color: Colors.white24) : null,
                                   ),
                                 ],
                              ),
                                           )),
                             
                                           if (items.length > 2)
                               Align(
                                 alignment: Alignment.centerRight,
                                 child: Text(
                                   '+ ${items.length - 2} المزيد...',
                                   style: const TextStyle(color: Colors.grey, fontSize: 11, fontFamily: 'Cairo'),
                                 ),
                               ),
                          ],
                        );
                      }
                  ),
                ],
              ),
            ),
            
            // Removed `Spacer()` to allow the card to size itself based on content
            const SizedBox(height: 8),

            // 4. Buttons (Footer)
            // Only if Editable
            if (widget.isEditable)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: Row(
                  children: [
                    // Delete Icon (Left)
                    Container(
                      decoration: BoxDecoration(
                         borderRadius: BorderRadius.circular(8),
                         // border: Border.all(color: Colors.red.withOpacity(0.5)),
                      ),
                      child: IconButton(
                        onPressed: () => _deleteOrder(order.orderId),
                        icon: const Icon(Icons.delete_outline, color: Colors.red, size: 28),
                        tooltip: 'حذف',
                      ),
                    ),
                    
                    const SizedBox(width: 12),
                    
                    // Confirm / Action Button (Expanded)
                    if (isPending)
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () => _updateStatus(order, 'Confirmed'),
                          style: ElevatedButton.styleFrom(
                             backgroundColor: const Color(0xFF2196F3), // Blue
                             foregroundColor: Colors.white,
                             shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)), // Pill shape
                             padding: const EdgeInsets.symmetric(vertical: 12),
                             elevation: 0,
                          ),
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                               Text('تأكيد', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, fontFamily: 'Cairo')), 
                               SizedBox(width: 8),
                               Icon(Icons.check, size: 22),
                            ],
                          ),
                        ),
                      )
                    else if (order.status.toLowerCase() == 'confirmed')
                       Expanded(
                        child: ElevatedButton(
                          onPressed: () => _updateStatus(order, 'Shipped'),
                          style: ElevatedButton.styleFrom(
                             backgroundColor: Colors.teal, 
                             foregroundColor: Colors.white,
                             shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                             padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                               Text('شحن', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, fontFamily: 'Cairo')), 
                               SizedBox(width: 8),
                               Icon(Icons.local_shipping, size: 20),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildMockupRow(IconData icon, String text) {
    return Row(
      children: [
        Flexible(
          child: Text(
            text,
            style: const TextStyle(color: Colors.white, fontSize: 13, fontFamily: 'Cairo'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        Icon(icon, size: 16, color: Colors.grey),
      ],
    );
  }

  String _translateStatus(String status) {
     switch (status.toLowerCase()) {
       case 'pending': return 'قيد الانتظار';
       case 'confirmed': return 'تم التأكيد';
       case 'shipped': return 'تم الشحن';
       case 'delivered': return 'تم التسليم';
       case 'rejected': return 'مرفوض';
       default: return status;
     }
  }

  Future<void> _updateStatus(Order order, String status) async {
    // 1. Update Status in DB
    await DatabaseHelper.instance.updateOrderStatus(order.orderId, status);
    
    // 2. Business Logic
    String messageToBuyer = '';
    
    // التحقق من أن المتجر مقفول
    final seller = await DatabaseHelper.instance.getSellerById(order.sellerId);
    final isRestrictedStore = seller?.requireCustomerRegistration ?? false;
    
    if (status == 'Shipped') {
       // Deduct Stock
       await DatabaseHelper.instance.deductStockForOrder(order.orderId);
       // Remove from Messages Inbox (Processed)
       await DatabaseHelper.instance.deleteMessageByOrderId(order.orderId);
       
       messageToBuyer = '📦 طلبك قيد الشحن رقم #${order.orderId}. شكراً لتسوقك معنا!';
       
       // إذا كان المتجر مقفول، إرسال الصور المختارة للزبون
       if (isRestrictedStore && order.buyerId != null) {
         try {
           final orderItems = await DatabaseHelper.instance.getItemsForOrder(order.orderId);
           for (var item in orderItems) {
             final orderItemId = item['OrderItemID'] as int;
             final images = await DatabaseHelper.instance.getOrderItemImages(orderItemId);
             
             if (images.isNotEmpty) {
               final imagePaths = images.map((img) => img.imagePath).whereType<String>().toList();
               if (imagePaths.isNotEmpty) {
                 final productName = item['Name'] as String? ?? 'منتج';
                 final caption = '📦 **${productName}**\n✅ تم تأكيد طلبك رقم #${order.orderId}';
                 
                 // إرسال الصور كمجموعة
                 await TelegramService.sendMediaGroup(order.buyerId!, imagePaths, caption: caption);
                 print("📸 Sent ${imagePaths.length} images to buyer ${order.buyerId} for order ${order.orderId}");
               }
             }
           }
         } catch (e) {
           print("❌ Error sending images to buyer: $e");
         }
       }
    } else if (status == 'Confirmed') {
       messageToBuyer = '✅ تم تأكيد طلبك رقم #${order.orderId} وهو قيد التجهيز.';
       
       // إرسال رسالة لصاحب المتجر بأن المشتري قد أكد الطلب
       try {
         final buyer = await DatabaseHelper.instance.getUserByTelegramId(order.buyerId ?? 0);
         final buyerName = buyer?.fullName ?? 'مشتري';
         await DatabaseHelper.instance.addMessage(
           order.orderId, 
           order.sellerId, 
           'order_confirmed', 
           '✅ المشتري "$buyerName" قد أكد الطلب رقم #${order.orderId}'
         );
         print("📨 Sent confirmation message to seller ${order.sellerId} for order ${order.orderId}");
       } catch (e) {
         print("❌ Error sending confirmation message to seller: $e");
       }
    }

    // 3. Send System Message to Buyer
    if (messageToBuyer.isNotEmpty) {
       await DatabaseHelper.instance.addSystemMessage(order.orderId, order.buyerId ?? 0, messageToBuyer);
    }
    
    // 4. Feedback to Seller
    if (mounted) {
       // ignore: use_build_context_synchronously
       ScaffoldMessenger.of(context).showSnackBar(SnackBar(
         content: Text('تم تغيير الحالة إلى: $status ${status == 'Shipped' ? '(وخصم الكمية)' : ''}'),
         backgroundColor: Colors.green,
       ));
    }

    _refreshOrders();
  }

  Future<void> _deleteOrder(int orderId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف (الإرجاع)'),
        content: const Text('هل أنت متأكد من حذف هذا الطلب؟\nسيتم استرجاع الكميات للمخزون تلقائياً.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('حذف واسترجاع', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm == true) {
      await DatabaseHelper.instance.deleteOrder(orderId); // Handles restore stock
      _refreshOrders();
       if (mounted) {
         // ignore: use_build_context_synchronously
         ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
           content: Text('تم حذف الطلب واسترجاع المخزون.'),
           backgroundColor: Colors.orange,
         ));
      }
    }
  }

  Widget _buildParsedDateRow(String createdAt, String? notes) {
      String datePart = createdAt;
      
      try {
        final DateTime dt = DateTime.parse(createdAt);
        datePart = "${dt.year}-${dt.month.toString().padLeft(2,'0')}-${dt.day.toString().padLeft(2,'0')}";
      } catch (e) {
        if (createdAt.contains(' ')) {
           datePart = createdAt.split(' ').first;
        }
      }

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
           _buildInfoRow(Icons.calendar_today, datePart, color: Colors.white70),
           if (notes != null && notes.isNotEmpty) ...[
              const SizedBox(height: 4), // Restored original spacing
              // Replaced Time with Notes (Phone), kept similar style but distinct icon
              _buildInfoRow(Icons.phone_android, notes, color: Colors.white), 
           ]
        ],
      );
  }

  Widget _buildInfoRow(IconData icon, String text, {Color color = Colors.black87}) {
    return Row(
      children: [
        Icon(icon, size: 16, color: color.withOpacity(0.7)),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 14, color: color), 
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  // Dialog showing full details
  void _showOrderDetails(Order order) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E1E), // Dark background for white text
        title: Text('تفاصيل الطلب #${order.orderId}', style: const TextStyle(color: Colors.white)),
        content: SizedBox(
          width: 400,
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: DatabaseHelper.instance.getItemsForOrder(order.orderId),
            builder: (context, snapshot) {
               if (snapshot.connectionState == ConnectionState.waiting) return const LinearProgressIndicator();
               if (!snapshot.hasData || snapshot.data!.isEmpty) return const Text('لا توجد عناصر', style: TextStyle(color: Colors.white54));
               
               final items = snapshot.data!;
               return SingleChildScrollView(
                 child: Column(
                   mainAxisSize: MainAxisSize.min,
                   crossAxisAlignment: CrossAxisAlignment.start,
                   children: [
                     // Header Info
                     _buildDetailRow('الحالة:', order.status),
                     _buildDetailRow('التاريخ:', order.createdAt),
                     if (order.deliveryAddress != null) _buildDetailRow('العنوان:', order.deliveryAddress!),
                     if (order.notes != null) _buildDetailRow('ملاحظات:', order.notes!),
                     
                     const Divider(color: Colors.white24),
                     const Text('المنتجات:', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                     const SizedBox(height: 8),
                     
                     // Items List
                     ...items.map((item) => ListTile(
                        leading: item['ImagePath'] != null 
                            ? Image.file(
                                File(item['ImagePath']), 
                                width: 40, height: 40, fit: BoxFit.cover,
                                errorBuilder: (_,__,___) => const Icon(Icons.broken_image, color: Colors.white54),
                              )
                            : const Icon(Icons.image, color: Colors.white54),
                        title: Text(item['Name'] ?? 'Unknown', style: const TextStyle(color: Colors.white)),
                        subtitle: Text('${formatPrice(item['Price'])} د.ع  x  ${item['Quantity']}', style: const TextStyle(color: Colors.white70)),
                        trailing: Text('${formatPrice(item['Price'] * item['Quantity'])} د.ع', style: const TextStyle(color: Colors.greenAccent)),
                     )),
                     
                     const Divider(color: Colors.white24),
                     Align(
                       alignment: Alignment.centerLeft,
                       child: Text(
                         'المجموع: ${formatPrice(order.total)} د.ع',
                         style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.blueAccent),
                       ),
                     )
                   ],
                 ),
               );
            }
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إغلاق', style: TextStyle(color: Colors.white70))),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: RichText(
        text: TextSpan(
          style: const TextStyle(color: Colors.white, fontSize: 14),
          children: [
            TextSpan(text: '$label ', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.blueAccent)),
            TextSpan(text: value),
          ]
        )
      ),
    );
  }
}

