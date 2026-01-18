import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import 'dart:async';

class MessagesScreen extends StatefulWidget {
  final int sellerId;

  const MessagesScreen({super.key, required this.sellerId});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  late Future<List<Message>> _messagesFuture;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshMessages();
    
    // تحديث الرسائل كل 5 ثوانٍ
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted) {
        _refreshMessages();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _refreshMessages() {
    print('🔄 تحديث الرسائل...');
    setState(() {
      _messagesFuture = DatabaseHelper.instance.getMessages(widget.sellerId);
    });
  }

  Future<void> _deleteMessage(int messageId) async {
    await DatabaseHelper.instance.deleteMessage(messageId);
    _refreshMessages();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم حذف الرسالة')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الرسائل'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshMessages,
            tooltip: 'تحديث',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          _refreshMessages();
          await Future.delayed(const Duration(milliseconds: 500));
        },
        child: FutureBuilder<List<Message>>(
          future: _messagesFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Center(child: Text('خطأ: ${snapshot.error}'));
            }
            if (!snapshot.hasData || snapshot.data!.isEmpty) {
              return const Center(child: Text('لا توجد رسائل'));
            }

            final messages = snapshot.data!;
            if (messages.isEmpty) {
              return const Center(child: Text('لا توجد رسائل'));
            }
            return ListView.builder(
            itemCount: messages.length,
            itemBuilder: (context, index) {
              final msg = messages[index];
              // تحديد نوع الرسالة وعرضها بشكل مناسب
              String displayText = msg.messageText ?? 'رسالة فارغة';
              IconData iconData = Icons.message;
              Color iconColor = Colors.blue;
              String messageTypeLabel = 'رسالة';
              
              if (msg.messageType == 'new_order') {
                iconData = Icons.shopping_cart;
                iconColor = Colors.green;
                messageTypeLabel = 'طلب جديد';
              } else if (msg.messageType == 'order_confirmed') {
                iconData = Icons.check_circle;
                iconColor = Colors.orange;
                messageTypeLabel = 'طلب مؤكد';
              } else if (msg.messageType == 'order_shipped') {
                iconData = Icons.local_shipping;
                iconColor = Colors.blue;
                messageTypeLabel = 'الطلب مشحون';
              }
              
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: ExpansionTile(
                  leading: Icon(iconData, color: iconColor),
                  title: Text('$messageTypeLabel - الطلب #${msg.orderId ?? 'N/A'}'),
                  subtitle: Text(msg.createdAt ?? ''),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildMessageDetail('النوع', messageTypeLabel),
                          _buildMessageDetail('رقم الطلب', '${msg.orderId ?? 'N/A'}'),
                          _buildMessageDetail('التاريخ', msg.createdAt ?? 'N/A'),
                          _buildMessageDetail('الرسالة', displayText),
                          _buildMessageDetail('حالة القراءة', msg.isRead ? 'مقروءة' : 'لم تقرأ'),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              ElevatedButton.icon(
                                onPressed: () => _deleteMessage(msg.messageId),
                                icon: const Icon(Icons.delete),
                                label: const Text('حذف'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          );
          },
        ),
      ),
    );
  }

  Widget _buildMessageDetail(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }
}
