import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';

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
    _refreshMessages();
  }

  void _refreshMessages() {
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
      body: FutureBuilder<List<Message>>(
        future: _messagesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}'));
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
              
              if (msg.messageType == 'new_order') {
                iconData = Icons.shopping_cart;
                iconColor = Colors.green;
              } else if (msg.messageType == 'order_confirmed') {
                iconData = Icons.check_circle;
                iconColor = Colors.orange;
              }
              
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: ListTile(
                  leading: Icon(iconData, color: iconColor),
                  title: Text(displayText),
                  subtitle: Text(msg.createdAt ?? ''),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete, color: Colors.red),
                    onPressed: () => _deleteMessage(msg.messageId),
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
