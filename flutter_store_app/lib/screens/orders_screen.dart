import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';

class OrdersScreen extends StatefulWidget {
  final int sellerId;

  const OrdersScreen({super.key, required this.sellerId});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<List<Order>> _ordersFuture;

  @override
  void initState() {
    super.initState();
    _refreshOrders();
  }

  void _refreshOrders() {
    setState(() {
      _ordersFuture = DatabaseHelper.instance.getOrders(widget.sellerId);
    });
  }

  Future<void> _updateOrderStatus(int orderId, String newStatus) async {
    await DatabaseHelper.instance.updateOrderStatus(orderId, newStatus);
    _refreshOrders();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تم تحديث الحالة إلى: $newStatus')),
      );
    }
  }

  String _getStatusText(String status) {
    final statusMap = {
      'Pending': 'قيد الانتظار',
      'Shipped': 'مشحون',
      'Confirmed': 'مؤكد (مغلق)',
      'Cancelled': 'ملغى',
    };
    return statusMap[status] ?? status;
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'Pending':
        return Colors.orange;
      case 'Shipped':
        return Colors.blue;
      case 'Confirmed':
        return Colors.green;
      case 'Cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<List<Order>>(
        future: _ordersFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('خطأ: ${snapshot.error}'));
          }
          if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return const Center(child: Text('لا توجد طلبات'));
          }

          final orders = snapshot.data!;
          // Filter to show only Pending and Shipped (not Confirmed)
          final filteredOrders = orders.where((o) => o.status == 'Pending' || o.status == 'Shipped').toList();
          
          if (filteredOrders.isEmpty) {
            return const Center(child: Text('لا توجد طلبات معلقة'));
          }

          return ListView.builder(
            itemCount: filteredOrders.length,
            itemBuilder: (context, index) {
              final order = filteredOrders[index];
              
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: ExpansionTile(
                  leading: Icon(Icons.shopping_bag, color: _getStatusColor(order.status)),
                  title: Text('الطلب #${order.orderId}'),
                  subtitle: Text('${order.total.toStringAsFixed(2)} د.ا • ${_getStatusText(order.status)}'),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildOrderDetail('التاريخ', order.createdAt),
                          _buildOrderDetail('المبلغ', '${order.total.toStringAsFixed(2)} د.ا'),
                          _buildOrderDetail('الحالة', _getStatusText(order.status)),
                          _buildOrderDetail('طريقة الدفع', order.paymentMethod),
                          _buildOrderDetail('مدفوع بالكامل', order.fullyPaid ? 'نعم' : 'لا'),
                          if (order.deliveryAddress != null)
                            _buildOrderDetail('عنوان التسليم', order.deliveryAddress!),
                          if (order.notes != null)
                            _buildOrderDetail('ملاحظات', order.notes!),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              if (order.status == 'Pending')
                                ElevatedButton.icon(
                                  onPressed: () => _updateOrderStatus(order.orderId, 'Shipped'),
                                  icon: const Icon(Icons.local_shipping),
                                  label: const Text('شحن'),
                                )
                              else if (order.status == 'Shipped')
                                ElevatedButton.icon(
                                  onPressed: () => _updateOrderStatus(order.orderId, 'Confirmed'),
                                  icon: const Icon(Icons.check_circle),
                                  label: const Text('تأكيد'),
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
    );
  }

  Widget _buildOrderDetail(String label, String value) {
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
