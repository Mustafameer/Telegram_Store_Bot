import 'dart:io';
import 'package:flutter/material.dart';
import '../../database/database_helper.dart';
import '../../services/telegram_service.dart';

class CartScreen extends StatefulWidget {
  final int userId;
  const CartScreen({super.key, required this.userId});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  late Future<List<Map<String, dynamic>>> _cartFuture;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _refreshCart();
  }

  void _refreshCart() {
    setState(() {
      _cartFuture = DatabaseHelper.instance.getCartItems(widget.userId);
    });
  }

  Future<void> _placeOrder(List<Map<String, dynamic>> items) async {
    if (items.isEmpty) return;

    // Group items by Seller
    Map<int, List<Map<String, dynamic>>> bySeller = {};
    for (var item in items) {
      if (item['SellerID'] == null) {
         // Skip orphaned items, user should delete them manually or we auto-clean?
         // For now just skip to prevent crash.
         continue; 
      }
      final sellerId = item['SellerID'] as int;
      if (!bySeller.containsKey(sellerId)) bySeller[sellerId] = [];
      bySeller[sellerId]!.add(item);
    }

    final details = await _showDeliveryDialog();
    if (details == null) return;

    setState(() => _isLoading = true);

    try {
      for (var entry in bySeller.entries) {
        final sellerId = entry.key;
        final sellerItems = entry.value;
        final total = sellerItems.fold(0.0, (sum, item) => sum + (item['Price'] * item['Quantity']));

        final orderId = await DatabaseHelper.instance.createOrder(
          widget.userId,
          sellerId,
          total,
          details['address']!,
          details['notes']!,
          sellerItems
        );

        await DatabaseHelper.instance.addMessage(orderId, sellerId, 'new_order', 'طلب جديد #$orderId');
         // Here we would fetch actual Telegram ID of the seller to notify them
         // For now, it stays in DB as notification.
      }
      
      await DatabaseHelper.instance.clearCart(widget.userId);
      
        // Show Success Dialog
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Row(children: [Icon(Icons.check_circle, color: Colors.green), SizedBox(width: 8), Text("تم الارسال")]),
            content: const Text("تم استلام طلبك بنجاح وسيتم معالجته قريباً."),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx), 
                child: const Text("حسناً")
              )
            ],
          )
        );
        _refreshCart();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('حدث خطأ: $e')));
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<Map<String, String>?> _showDeliveryDialog() async {
    final addressController = TextEditingController();
    final notesController = TextEditingController();
    
    return showDialog<Map<String, String>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('إتمام الطلب'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: addressController,
              decoration: const InputDecoration(labelText: 'العنوان'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: notesController,
              decoration: const InputDecoration(labelText: 'ملاحظات'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () {
              if (addressController.text.isNotEmpty) {
                Navigator.pop(context, {
                  'address': addressController.text,
                  'notes': notesController.text
                });
              }
            },
            child: const Text('تأكيد'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('سلة المشتريات')),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _cartFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('السلة فارغة'));

          final items = snapshot.data!;
          final total = items.fold(0.0, (sum, item) => sum + (double.parse(item['Price'].toString()) * int.parse(item['Quantity'].toString())));
          
          Map<String, List<Map<String, dynamic>>> byStoreName = {};
          for (var item in items) {
             final storeName = (item['StoreName'] as String?) ?? 'متجر غير معروف';
             if (!byStoreName.containsKey(storeName)) byStoreName[storeName] = [];
             byStoreName[storeName]!.add(item);
          }

          return Column(
            children: [
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: byStoreName.keys.length,
                  itemBuilder: (context, index) {
                    final storeName = byStoreName.keys.elementAt(index);
                    final storeItems = byStoreName[storeName]!;
                    
                    return Card(
                      margin: const EdgeInsets.only(bottom: 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                           Container(
                             width: double.infinity,
                             padding: const EdgeInsets.all(12),
                             decoration: BoxDecoration(
                               color: Theme.of(context).primaryColor.withOpacity(0.1),
                               borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                             ),
                             child: Text(storeName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                           ),
                           ...storeItems.map((item) => ListTile(
                             title: Text(item['Name'] ?? 'منتج محذوف'),
                             subtitle: Text('السعر: ${item['Price']} د.ع'),
                             leading: item['ImagePath'] != null 
                              ? CircleAvatar(backgroundImage: FileImage(File(item['ImagePath']))) 
                              : const CircleAvatar(child: Icon(Icons.image)),
                             trailing: Row(
                               mainAxisSize: MainAxisSize.min,
                               children: [
                                 // Quantity Controls
                                 IconButton(
                                   icon: const Icon(Icons.remove_circle_outline),
                                   onPressed: () async {
                                     final currentQty = int.parse(item['Quantity'].toString());
                                     if (currentQty > 1) {
                                       await DatabaseHelper.instance.updateCartQuantity(item['CartID'], currentQty - 1);
                                       _refreshCart();
                                     }
                                   },
                                 ),
                                 Text('${item['Quantity']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                 IconButton(
                                   icon: const Icon(Icons.add_circle_outline),
                                   onPressed: () async {
                                      final currentQty = int.parse(item['Quantity'].toString());
                                      await DatabaseHelper.instance.updateCartQuantity(item['CartID'], currentQty + 1);
                                      _refreshCart();
                                   },
                                 ),
                                 const SizedBox(width: 8),
                                 // Total Price for Item
                                 Text('${(double.parse(item['Price'].toString()) * int.parse(item['Quantity'].toString()))} د.ع', style: const TextStyle(color: Colors.grey)),
                                 const SizedBox(width: 8),
                                 // Delete Button
                                 IconButton(
                                   icon: const Icon(Icons.delete, color: Colors.red),
                                   tooltip: 'حذف',
                                   onPressed: () async {
                                     await DatabaseHelper.instance.removeFromCart(item['CartID']);
                                     _refreshCart();
                                   },
                                 )
                               ],
                             ),
                           )).toList(),
                           // Subtotal per store could be here
                        ],
                      ),
                    );
                  },
                ),
              ),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [BoxShadow(blurRadius: 10, color: Colors.black.withValues(alpha: 0.1))],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('المجموع الكلي: $total د.ع', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                    FilledButton.icon(
                      icon: const Icon(Icons.check),
                      onPressed: _isLoading ? null : () => _placeOrder(items),
                      label: const Text('إتمام جميع الطلبات'),
                    ),
                  ],
                ),
              )
            ],
          );
        },
      ),
    );
  }
}
