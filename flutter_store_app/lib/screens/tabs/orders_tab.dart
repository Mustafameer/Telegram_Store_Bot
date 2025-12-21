

import 'package:flutter/material.dart';
import 'dart:io';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';

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

              return GridView.builder(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 250, 
                  childAspectRatio: 0.62, // Taller for list
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                ),
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
    // Determine status color and icon
    Color statusColor = Colors.grey;
    IconData statusIcon = Icons.help_outline;
    String statusText = order.status;

    switch (order.status.toLowerCase()) {
      case 'pending':
        statusColor = Colors.orange;
        statusIcon = Icons.hourglass_top;
        statusText = 'قيد الانتظار';
        break;
      case 'confirmed':
      case 'accepted':
        statusColor = Colors.blue;
        statusIcon = Icons.check_circle_outline;
        statusText = 'تم التأكيد (تجهيز)';
        break;
      case 'shipped':
        statusColor = Colors.teal;
        statusIcon = Icons.local_shipping;
        statusText = 'تم الشحن';
        break;
      case 'delivered':
        statusColor = Colors.green;
        statusIcon = Icons.card_giftcard;
        statusText = 'تم التسليم';
        break;
      case 'rejected':
      case 'cancelled':
        statusColor = Colors.red;
        statusIcon = Icons.cancel_outlined;
        statusText = 'ملغي / مرفوض';
        break;
    }

    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 4,
      shadowColor: Colors.black26,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        onTap: () {
          // Show Details
          _showOrderDetails(order);
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
             // Status Header
             Container(
               padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
               color: statusColor.withOpacity(0.15),
               child: Row(
                 children: [
                   Icon(statusIcon, size: 20, color: statusColor),
                   const SizedBox(width: 8),
                   Expanded(
                     child: Text(
                       statusText,
                       style: TextStyle(
                         color: statusColor,
                         fontWeight: FontWeight.bold,
                         fontSize: 14
                       ),
                       overflow: TextOverflow.ellipsis,
                     ),
                   ),
                   Text(
                     '#${order.orderId}',
                     style: TextStyle(
                       color: statusColor,
                       fontWeight: FontWeight.w900,
                     ),
                   )
                 ],
               ),
             ),

            // Content Section
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Date & Price
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildParsedDateRow(order.createdAt, order.notes),
                            ],
                          ),
                        ),
                        
                        Container(
                          margin: const EdgeInsets.only(right: 8), 
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.blue.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.blue.shade100)
                          ),
                          child: Text(
                            '${order.total.toStringAsFixed(0)} د.ع',
                            style: TextStyle(
                              color: Colors.blue.shade900,
                              fontWeight: FontWeight.w900,
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    
                    // Address / Notes
                    if (order.deliveryAddress != null && order.deliveryAddress!.isNotEmpty)
                       _buildInfoRow(Icons.location_on, order.deliveryAddress!, color: Colors.white),

                    const Divider(color: Colors.grey),
                    
                    // Order Content Check
                    FutureBuilder<List<Map<String, dynamic>>>(
                      future: DatabaseHelper.instance.getItemsForOrder(order.orderId),
                      builder: (context, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return const LinearProgressIndicator(minHeight: 2);
                        }
                        
                        if (snapshot.hasError) {
                           return Text('Error: ${snapshot.error}', style: const TextStyle(color: Colors.red, fontSize: 10));
                        }

                        if (!snapshot.hasData || snapshot.data!.isEmpty) {
                          return const Padding(
                             padding: EdgeInsets.symmetric(vertical: 8),
                             child: Center(child: Text('لا توجد منتجات (Empty List)', style: TextStyle(color: Colors.grey, fontSize: 12))),
                          );
                        }
                        
                        // Show first 2 items + "and X more"
                        final items = snapshot.data!;
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ...items.take(2).map((item) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4.0),
                              child: Row(
                                children: [
                                  // Product Thumbnail
                                  Container(
                                    width: 40, height: 40,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(8),
                                      color: Colors.grey[800],
                                      image: item['ImagePath'] != null && File(item['ImagePath']).existsSync()
                                          ? DecorationImage(
                                              image: FileImage(File(item['ImagePath'])),
                                              fit: BoxFit.cover
                                            )
                                          : null,
                                    ),
                                    child: item['ImagePath'] == null || !File(item['ImagePath']).existsSync()
                                        ? const Icon(Icons.shopping_bag_outlined, size: 20, color: Colors.white54)
                                        : null,
                                  ),
                                  const SizedBox(width: 10),
                                  // Details
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item['Name'] ?? 'Unknown', 
                                          style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                                          maxLines: 1, 
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        Text(
                                          "${item['Quantity']} x ${item['Price']} د.ع",
                                          style: const TextStyle(color: Colors.grey, fontSize: 11),
                                        ),
                                      ],
                                    ),
                                  ),
                                  // Total Price for Item
                                  Text(
                                    "${(item['Price'] * item['Quantity']).toStringAsFixed(0)}", 
                                    style: const TextStyle(color: Colors.blueAccent, fontSize: 14, fontWeight: FontWeight.bold), 
                                  ),
                                ],
                              ),
                            )),
                            if (items.length > 2)
                              Padding(
                                padding: const EdgeInsets.only(top: 4.0),
                                child: Text(
                                  "+ ${items.length - 2} منتجات أخرى...",
                                  style: const TextStyle(color: Colors.grey, fontSize: 11, fontStyle: FontStyle.italic),
                                ),
                              )
                          ],
                        );
                      }
                    ),
                    
                    const Spacer(),

                    // Actions
                    if (widget.isEditable)
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                           // Confirm Button (Only if Pending)
                           if (order.status.toLowerCase() == 'pending')
                             Expanded(
                               child: ElevatedButton.icon(
                                 onPressed: () => _updateStatus(order, 'Confirmed'),
                                 icon: const Icon(Icons.check, size: 18),
                                 label: const Text('تأكيد'),
                                 style: ElevatedButton.styleFrom(
                                   backgroundColor: Colors.blue,
                                   foregroundColor: Colors.white,
                                   padding: const EdgeInsets.symmetric(vertical: 0)
                                 ),
                               ),
                             ),
                           
                           // Ship Button (Only if Confirmed)
                           if (order.status.toLowerCase() == 'confirmed' || order.status.toLowerCase() == 'accepted')
                             Expanded(
                               child: ElevatedButton.icon(
                                 onPressed: () => _updateStatus(order, 'Shipped'),
                                 icon: const Icon(Icons.local_shipping, size: 18),
                                 label: const Text('شحن'),
                                 style: ElevatedButton.styleFrom(
                                   backgroundColor: Colors.teal,
                                   foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(vertical: 0)
                                 ),
                               ),
                             ),
                             
                           const SizedBox(width: 8),
                           
                           // Delete/Reject Button
                           IconButton(
                             onPressed: () => _deleteOrder(order.orderId),
                             icon: const Icon(Icons.delete_outline, color: Colors.red),
                             tooltip: 'حذف (إرجاع)',
                           ),
                        ],
                      )
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _updateStatus(Order order, String status) async {
    // 1. Update Status in DB
    await DatabaseHelper.instance.updateOrderStatus(order.orderId, status);
    
    // 2. Business Logic
    String messageToBuyer = '';
    
    if (status == 'Shipped') {
       // Deduct Stock
       await DatabaseHelper.instance.deductStockForOrder(order.orderId);
       // Remove from Messages Inbox (Processed)
       await DatabaseHelper.instance.deleteMessageByOrderId(order.orderId);
       
       messageToBuyer = '📦 طلبك قيد الشحن رقم #${order.orderId}. شكراً لتسوقك معنا!';
    } else if (status == 'Confirmed') {
       messageToBuyer = '✅ تم تأكيد طلبك رقم #${order.orderId} وهو قيد التجهيز.';
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
                        subtitle: Text('${item['Price']} د.ع  x  ${item['Quantity']}', style: const TextStyle(color: Colors.white70)),
                        trailing: Text('${(item['Price'] * item['Quantity']).toStringAsFixed(0)} د.ع', style: const TextStyle(color: Colors.greenAccent)),
                     )),
                     
                     const Divider(color: Colors.white24),
                     Align(
                       alignment: Alignment.centerLeft,
                       child: Text(
                         'المجموع: ${order.total.toStringAsFixed(0)} د.ع',
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

