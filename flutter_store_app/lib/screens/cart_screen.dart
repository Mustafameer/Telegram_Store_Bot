import 'dart:io';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../database/database_helper.dart';
import '../../services/telegram_service.dart';

// دالة لتنسيق المبالغ مع فاصلة الآلاف وإزالة الكسور
String formatPrice(dynamic price) {
  if (price == null) return '0';
  final numValue = price is num ? price : double.tryParse(price.toString()) ?? 0;
  final rounded = numValue.round();
  final formatter = NumberFormat('#,###', 'ar');
  return formatter.format(rounded);
}

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

    // 🔍 Check if all stores are closed (RequireCustomerRegistration = 1) 
    // and user is registered in all of them
    bool allStoresClosed = true;
    bool userRegisteredInAll = true;
    
    for (var sellerId in bySeller.keys) {
      try {
        // Get seller info
        final sellers = await DatabaseHelper.instance.getAllSellers(forceRefresh: true);
        final seller = sellers.firstWhere((s) => s.sellerId == sellerId, orElse: () => null as dynamic);
        
        if (seller == null || !seller.requireCustomerRegistration) {
          allStoresClosed = false;
          break;
        }
        
        // Check if user is registered as a credit customer
        final creditCustomers = await DatabaseHelper.instance.getCreditCustomers(sellerId);
        final isRegistered = creditCustomers.any((cc) => cc.telegramId == widget.userId);
        
        if (!isRegistered) {
          userRegisteredInAll = false;
          break;
        }
      } catch (e) {
        print('⚠️ Error checking store status: $e');
        allStoresClosed = false;
        break;
      }
    }

    // 🚀 If all stores are closed and user is registered in all, create order immediately
    if (allStoresClosed && userRegisteredInAll) {
      print('✅ جميع المتاجر مغلقة - إنشاء طلب مؤكد مباشرة');
      setState(() => _isLoading = true);

      try {
        var totalAllOrders = 0.0;
        
        for (var entry in bySeller.entries) {
          final sellerId = entry.key;
          final sellerItems = entry.value;
          final total = sellerItems.fold(0.0, (sum, item) => sum + (item['Price'] * item['Quantity']));

          final orderId = await DatabaseHelper.instance.createOrder(
            widget.userId,
            sellerId,
            total,
            '', // No address needed for closed stores
            'طلب مؤكد من زبون آجل', // Automatic notes
            sellerItems,
            status: 'Confirmed', // 🆕 Set status to Confirmed
            paymentMethod: 'credit', // 🆕 Payment method is credit
            fullyPaid: false // 🆕 Not fully paid
          );

          totalAllOrders += total;
          await DatabaseHelper.instance.addMessage(orderId, sellerId, 'new_order', 'طلب جديد #$orderId - مؤكد');
        }
        
        await DatabaseHelper.instance.clearCart(widget.userId);
        
        // Show Success Dialog
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Row(children: [Icon(Icons.check_circle, color: Colors.green), SizedBox(width: 8), Text("✅ تم إنزال طلبك")]),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text("تم إنزال طلبك بنجاح!"),
                const SizedBox(height: 16),
                Text("المبلغ المخصوم: ${formatPrice(totalAllOrders)} د.ع", style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                const Text("سيتم معالجة الطلب من قبل صاحب المتجر", style: TextStyle(color: Colors.grey, fontSize: 12)),
              ],
            ),
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
      return;
    }

    // ❌ Otherwise, use regular checkout with delivery dialog
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
      appBar: AppBar(title: const Text('سلة المشتريات 🛒')),
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
                             title: Text(item['Name'] ?? 'منتج محذوف', 
                               style: const TextStyle(
                                 fontWeight: FontWeight.w900,
                                 color: Color(0xFF0D47A1), // أزرق غامق جداً
                                 fontSize: 18
                               )),
                             subtitle: Text('السعر: ${formatPrice(item['Price'])} د.ع'),
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
                                 Text('${formatPrice(double.parse(item['Price'].toString()) * int.parse(item['Quantity'].toString()))} د.ع', style: const TextStyle(color: Colors.grey)),
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
                    Text('المجموع الكلي: ${formatPrice(total)} د.ع', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
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
