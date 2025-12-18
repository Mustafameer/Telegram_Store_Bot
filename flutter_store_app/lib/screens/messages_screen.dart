import 'package:flutter/material.dart';
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
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: messages.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final msg = messages[index];
              final isOrder = msg.messageType == 'order';
              
              return Card(
                elevation: msg.isRead ? 1 : 4,
                color: msg.isRead ? Colors.white : Colors.blue.shade50,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(color: msg.isRead ? Colors.grey.shade200 : Colors.blue.shade200),
                ),
                child: InkWell(
                  onTap: () => _markAsRead(msg),
                  borderRadius: BorderRadius.circular(12),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              isOrder ? Icons.shopping_cart : Icons.notifications, 
                              color: isOrder ? Colors.orange : Colors.blue
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                msg.messageType.toUpperCase(), 
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.grey)
                              ),
                            ),
                            if (!msg.isRead)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(color: Colors.red, borderRadius: BorderRadius.circular(8)),
                                child: const Text('جديد', style: TextStyle(color: Colors.white, fontSize: 10)),
                              ),
                             IconButton(
                                icon: const Icon(Icons.delete_outline, color: Colors.grey, size: 20),
                                onPressed: () => _deleteMessage(msg),
                             )
                          ],
                        ),
                        const Divider(),
                        Text(
                          msg.messageText ?? '',
                          style: TextStyle(
                            fontSize: 16, 
                            fontWeight: msg.isRead ? FontWeight.normal : FontWeight.bold
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            if (msg.orderId != null)
                              Chip(
                                label: Text('Order #${msg.orderId}'),
                                backgroundColor: Colors.grey.shade100,
                                visualDensity: VisualDensity.compact,
                              ),
                            Text(
                              msg.createdAt?.substring(0, 16).replaceFirst('T', ' ') ?? '',
                              style: const TextStyle(fontSize: 12, color: Colors.grey),
                            ),
                          ],
                        )
                      ],
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
