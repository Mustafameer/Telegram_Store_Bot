import 'package:flutter/material.dart';
import '../models/notification_model.dart';
import '../services/notification_service.dart';
import 'package:intl/intl.dart';

class NotificationsScreen extends StatefulWidget {
  final int customerId;
  
  const NotificationsScreen({
    Key? key,
    required this.customerId,
  }) : super(key: key);
  
  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<AppNotification>> _notificationsFuture;
  bool _showUnreadOnly = true;
  
  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }
  
  void _loadNotifications() {
    setState(() {
      _notificationsFuture = NotificationService.getNotifications(
        customerId: widget.customerId,
        unreadOnly: _showUnreadOnly,
      );
    });
  }
  
  Future<void> _handleMarkAsRead(AppNotification notification) async {
    final success = await NotificationService.markAsRead(notification.notificationId);
    
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم وضع علامة على الإشعار')),
      );
      _loadNotifications();
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('فشل تحديث الإشعار')),
      );
    }
  }
  
  Future<void> _handleRefresh() async {
    _loadNotifications();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإشعارات 📬'),
        backgroundColor: Colors.blue[700],
        elevation: 2,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _handleRefresh,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter tabs
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: FilterChip(
                    label: const Text('غير مقروءة فقط'),
                    selected: _showUnreadOnly,
                    onSelected: (selected) {
                      setState(() {
                        _showUnreadOnly = selected;
                      });
                      _loadNotifications();
                    },
                    backgroundColor: Colors.grey[200],
                    selectedColor: Colors.blue,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilterChip(
                    label: const Text('كل الإشعارات'),
                    selected: !_showUnreadOnly,
                    onSelected: (selected) {
                      if (selected) {
                        setState(() {
                          _showUnreadOnly = false;
                        });
                        _loadNotifications();
                      }
                    },
                    backgroundColor: Colors.grey[200],
                    selectedColor: Colors.blue,
                  ),
                ),
              ],
            ),
          ),
          // Notifications list
          Expanded(
            child: FutureBuilder<List<AppNotification>>(
              future: _notificationsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: CircularProgressIndicator(),
                  );
                }
                
                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.error_outline,
                          size: 48,
                          color: Colors.red,
                        ),
                        const SizedBox(height: 16),
                        Text('خطأ: ${snapshot.error}'),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _handleRefresh,
                          child: const Text('حاول مجدداً'),
                        ),
                      ],
                    ),
                  );
                }
                
                final notifications = snapshot.data ?? [];
                
                if (notifications.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.inbox,
                          size: 64,
                          color: Colors.grey,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _showUnreadOnly 
                            ? 'لا توجد إشعارات غير مقروءة'
                            : 'لا توجد إشعارات',
                          style: const TextStyle(
                            fontSize: 16,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  );
                }
                
                return ListView.builder(
                  itemCount: notifications.length,
                  itemBuilder: (context, index) {
                    final notification = notifications[index];
                    return _NotificationCard(
                      notification: notification,
                      onMarkAsRead: _handleMarkAsRead,
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  final AppNotification notification;
  final Function(AppNotification) onMarkAsRead;
  
  const _NotificationCard({
    Key? key,
    required this.notification,
    required this.onMarkAsRead,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        if (!notification.isRead) {
          onMarkAsRead(notification);
        }
        _showNotificationDetails(context);
      },
      child: Card(
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        elevation: notification.isRead ? 0 : 2,
        color: notification.isRead ? Colors.grey[100] : Colors.white,
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Icon
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _getColorForType(),
                    ),
                    child: Text(
                      notification.getIcon(),
                      style: const TextStyle(fontSize: 20),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Title and metadata
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                notification.title,
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: notification.isRead 
                                    ? FontWeight.normal
                                    : FontWeight.bold,
                                ),
                              ),
                            ),
                            if (!notification.isRead)
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: Colors.blue,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          notification.message,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[700],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(
                              Icons.access_time,
                              size: 12,
                              color: Colors.grey[600],
                            ),
                            const SizedBox(width: 4),
                            Text(
                              notification.getFormattedTime(),
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[600],
                              ),
                            ),
                            if (notification.totalAmount != null) ...[
                              const SizedBox(width: 16),
                              Icon(
                                Icons.attach_money,
                                size: 12,
                                color: Colors.green[700],
                              ),
                              const SizedBox(width: 4),
                              Text(
                                '${notification.totalAmount?.toStringAsFixed(2)} SAR',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.green[700],
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              // Products list if available
              if (notification.productNames != null && 
                  notification.productNames!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Padding(
                  padding: const EdgeInsets.only(left: 44.0),
                  child: Text(
                    'المنتجات: ${notification.productNames}',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey[700],
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
  
  Color _getColorForType() {
    switch (notification.type) {
      case 'closed_store_purchase':
        return Colors.green[100]!;
      case 'refund':
        return Colors.blue[100]!;
      case 'new_product':
        return Colors.orange[100]!;
      case 'promotion':
        return Colors.pink[100]!;
      default:
        return Colors.grey[100]!;
    }
  }
  
  void _showNotificationDetails(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              notification.title,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              notification.message,
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 16),
            if (notification.productNames != null) ...[
              const Text(
                'المنتجات:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 8),
              Text(notification.productNames!),
              const SizedBox(height: 16),
            ],
            if (notification.totalAmount != null) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'المبلغ الإجمالي:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(
                    '${notification.totalAmount?.toStringAsFixed(2)} SAR',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],
            Text(
              'الوقت: ${DateFormat('dd/MM/yyyy HH:mm').format(notification.createdAt ?? DateTime.now())}',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                },
                child: const Text('إغلاق'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
