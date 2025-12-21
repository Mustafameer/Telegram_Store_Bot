import 'package:flutter/material.dart';
import 'dart:io';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import 'package:intl/intl.dart' as intl;

class MessagesScreen extends StatefulWidget {
  final int sellerId;
  const MessagesScreen({super.key, required this.sellerId});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  late Future<List<Message>> _messagesFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _messagesFuture = DatabaseHelper.instance.getMessages(widget.sellerId);
    });
  }

  Future<void> _markAsRead(Message message) async {
    if (!message.isRead) {
      await DatabaseHelper.instance.markMessageAsRead(message.messageId);
      _refresh();
    }
  }

  Future<void> _updateOrderStatus(int orderId, String status) async {
    await DatabaseHelper.instance.updateOrderStatus(orderId, status);
    
    // Deduct stock if shipping
    if (status == 'Shipped') {
       await DatabaseHelper.instance.deductStockForOrder(orderId);
    }

    setState(() {
      // Force rebuild
    });
    _refresh();
    
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('تم تحديث حالة الطلب إلى: ${status == 'Accepted' ? 'قيد التحضير' : 'تم الشحن'}')));
  }

  Future<void> _deleteMessage(Message message) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('حذف الرسالة'),
        content: const Text('هل أنت متأكد من حذف هذه الرسالة؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await DatabaseHelper.instance.deleteMessage(message.messageId);
      _refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الرسائل')),
      body: FutureBuilder<List<Message>>(
        future: _messagesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.message_outlined, size: 60, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('لا توجد رسائل', style: TextStyle(color: Colors.grey, fontSize: 18)),
                ],
              ),
            );
          }
          
          final messages = snapshot.data!;
          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 240, // Slightly wider than products for readability
              childAspectRatio: 0.55, // Taller card to fit info + image
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: messages.length,
            itemBuilder: (context, index) {
              final msg = messages[index];
              
              if (msg.orderId == null) {
                  // Standard Text Message Card (Small)
                  return Card(
                    clipBehavior: Clip.antiAlias,
                    elevation: 2,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.mail_outline, color: Colors.blue, size: 20),
                              SizedBox(width: 8),
                              Expanded(child: Text("رسالة", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13))),
                            ],
                          ),
                          const Divider(height: 12),
                          Expanded(
                            child: SingleChildScrollView(
                               child: Text(msg.messageText ?? '', style: const TextStyle(fontSize: 12))
                            )
                          ),

                        ],
                      ),
                    ),
                  );
              }

              // Order Card
              return FutureBuilder<List<Map<String, dynamic>>>(
                future: DatabaseHelper.instance.getItemsForOrder(msg.orderId!),
                builder: (context, snapshot) {
                  // Handle errors
                  if (snapshot.hasError) {
                      return Card(child: Center(child: Text("Error: ${snapshot.error}", style: const TextStyle(color: Colors.red))));
                  }

                  // Handle Loading
                  if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Card(child: Center(child: CircularProgressIndicator()));
                  }
                  
                  // Handle Empty
                  if (!snapshot.hasData || snapshot.data!.isEmpty) {
                      return const Card(child: Center(child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.error_outline, color: Colors.orange),
                          Text("لا توجد تفاصيل", style: TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      )));
                  }
                  
                  final items = snapshot.data!;
                  final firstItem = items.first;
                  final status = firstItem['Status'] as String? ?? 'Pending';
                  final imagePath = firstItem['ImagePath'] as String?;
                  final total = items.fold(0.0, (sum, i) => sum + ((i['Price'] ?? 0) * (i['Quantity'] ?? 0)));

                  return Card(
                    clipBehavior: Clip.antiAlias,
                    elevation: 4,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // 1. Image Area (Flexible)
                        Expanded(
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                               imagePath != null && File(imagePath).existsSync()
                                  ? Image.file(File(imagePath), fit: BoxFit.cover)
                                  : Container(
                                      color: Colors.grey[200],
                                      child: const Icon(Icons.image_not_supported, size: 40, color: Colors.grey),
                                    ),
                               // Pending Status Overlay
                               if (status == 'Pending')
                                 Positioned(
                                    top: 8, right: 8,
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(color: Colors.orange, borderRadius: BorderRadius.circular(4)),
                                      child: const Text('جديد', style: TextStyle(color: Colors.white, fontSize: 10)),
                                    ),
                                 )
                            ]
                          ),
                        ),
                        
                        // 2. Dark Info Area
                        Container(
                          color: const Color(0xFF1A1A1A), // Dark Grey
                          padding: const EdgeInsets.all(10), // Reduced padding
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                firstItem['Name'] ?? 'منتج',
                                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                                maxLines: 1, overflow: TextOverflow.ellipsis
                              ),
                              const SizedBox(height: 4),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    '${firstItem['Price']} د.ع',
                                    style: const TextStyle(color: Colors.blueAccent, fontSize: 13, fontWeight: FontWeight.bold),
                                  ),
                                  Text(
                                    'x${items.length > 1 ? items.length : firstItem['Quantity']}',
                                    style: const TextStyle(color: Colors.grey, fontSize: 12),
                                  ),
                                ],
                              ),
                              if (items.length > 1)
                                Text(
                                   '+ ${items.length - 1} آخرين',
                                   style: const TextStyle(color: Colors.grey, fontSize: 10),
                                ),
                            ],
                          ),
                        ),

                        // 3. Action Buttons Area
                        Container(
                          color: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                             mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                             children: [
                               // Action: Status
                               if (status == 'Pending')
                                 IconButton(
                                   onPressed: () => _updateOrderStatus(msg.orderId!, 'Accepted'),
                                   icon: const Icon(Icons.check_circle, color: Colors.green, size: 24), // Smaller
                                   tooltip: 'تأكيد',
                                   padding: EdgeInsets.zero,
                                 ),
                               if (status == 'Accepted')
                                 IconButton(
                                   onPressed: () => _updateOrderStatus(msg.orderId!, 'Shipped'),
                                   icon: const Icon(Icons.local_shipping, color: Colors.blue, size: 24),
                                   tooltip: 'شحن',
                                   padding: EdgeInsets.zero,
                                 ),
                             ],
                          ),
                        )
                      ],
                    ),
                  );
                }
              );
            },
          );
        },
      ),
    );
  }
}
