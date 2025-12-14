
import 'package:flutter/material.dart';
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

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Order>>(
      future: _ordersFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Error: ${snapshot.error}'));
        }
        if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return const Center(child: Text('لا يوجد طلبات'));
        }

        final orders = snapshot.data!;
        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: orders.length,
          itemBuilder: (context, index) {
            final order = orders[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                title: Text('طلب #${order.orderId}'),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('التاريخ: ${order.createdAt}'),
                    Text('الحالة: ${order.status}'),
                  ],
                ),
                trailing: Text(
                  '${order.total} د.ع',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                onTap: () {
                  // Show Order Details
                },
              ),
            );
          },
        );
      },
    );
  }
}
