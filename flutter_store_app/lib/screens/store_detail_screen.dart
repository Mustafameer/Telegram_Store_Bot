

import 'package:flutter/material.dart';
import '../models/database_models.dart';
import 'tabs/products_tab.dart';
import 'tabs/orders_tab.dart';
import 'tabs/categories_tab.dart';
import 'credit_customers_screen.dart';
import 'credit_customers_screen.dart';
import 'login_screen.dart';
import 'components/store_form_dialog.dart';
import '../database/database_helper.dart';

class StoreDetailScreen extends StatefulWidget {
  final Seller seller;
  final bool isSellerMode;

  const StoreDetailScreen({
    super.key, 
    required this.seller,
    this.isSellerMode = false,
  });

  @override
  State<StoreDetailScreen> createState() => _StoreDetailScreenState();
}

class _StoreDetailScreenState extends State<StoreDetailScreen> {
  int _selectedIndex = 0;
  bool _isExtended = true;

  Future<void> _showEditStoreDialog(BuildContext context) async {
    await showDialog(
      context: context,
      builder: (context) => StoreFormDialog(
        initialName: widget.seller.storeName,
        initialTelegramId: widget.seller.telegramId.toString(),
        initialUserName: widget.seller.userName,
        initialImagePath: widget.seller.imagePath,
        isEdit: true,
        onSave: (name, telegramId, userName, imagePath) async {
           // Update
           await DatabaseHelper.instance.updateSeller(Seller(
             sellerId: widget.seller.sellerId,
             telegramId: telegramId,
             storeName: name,
             userName: userName,
             status: widget.seller.status, 
             imagePath: imagePath
           ));
           
           if (mounted) {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم تحديث بيانات المتجر. يرجى إعادة التشغيل لتحديث الواجهة.')));
              // We might need to refresh "widget.seller". 
              // Since it's a StatefulWidget, we can't easily update `widget.seller`.
              // But global cache is invalid.
              // Best is to trigger a parent rebuild or just show message.
           }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool canPop = Navigator.canPop(context);

    // Calculate Exit Tab Index
    // Tabs: Products(0), Orders(1), Categories(2)
    // If SellerMode: CreditCustomers(3)
    // Exit is last.
    final int exitIndex = widget.isSellerMode ? 4 : 3;

    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: _isExtended,
            selectedIndex: _selectedIndex,
              onDestinationSelected: (int index) {
              
              if (index == exitIndex) {
                if (canPop) {
                   Navigator.of(context).pop();
                } else {
                   // Logout
                   Navigator.of(context).pushReplacement(
                      MaterialPageRoute(builder: (context) => const LoginScreen()),
                   );
                }
                return;
              }
              setState(() {
                _selectedIndex = index;
              });
            },
            leading: Column(
              children: [
                IconButton(
                  icon: Icon(_isExtended ? Icons.menu_open : Icons.menu),
                  onPressed: () {
                    setState(() {
                      _isExtended = !_isExtended;
                    });
                  },
                ),
                // Hide top back button if we have sidebar back button?
                // Or keep it for redundancy? The user asked for "Back Button" behavior.
                // If I have sidebar back, I might not need duplicates, but rail leading is nice.
                // Keeping existing logic: Show leading back if !widget.isSellerMode.
                // Actually, if canPop, maybe show it?
                if (canPop && !widget.isSellerMode) 
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => Navigator.of(context).pop(),
                    tooltip: 'رجوع',
                  ),
              ],
            ),
            labelType: _isExtended ? NavigationRailLabelType.none : NavigationRailLabelType.selected,
            destinations: [
              const NavigationRailDestination(
                icon: Icon(Icons.shopping_bag),
                label: Text('المنتجات'),
              ),
              const NavigationRailDestination(
                icon: Icon(Icons.list_alt),
                label: Text('الطلبات'),
              ),
              const NavigationRailDestination(
                icon: Icon(Icons.category),
                label: Text('الفئات'),
              ),
              if (widget.isSellerMode)
                const NavigationRailDestination(
                  icon: Icon(Icons.people),
                  label: Text('الزبائن الآجل'),
                ),
              NavigationRailDestination(
                icon: Icon(
                  canPop ? Icons.arrow_back : Icons.logout, 
                  color: canPop ? null : Colors.red
                ),
                label: Text(
                  canPop ? 'رجوع' : 'خروج', 
                  style: TextStyle(color: canPop ? null : Colors.red)
                ),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Column(
              children: [
                AppBar(
                  title: Text(widget.seller.storeName ?? 'تفاصيل المتجر'),
                  centerTitle: false,
                  automaticallyImplyLeading: false, // Handled by Rail
                  actions: [
                     if (widget.isSellerMode)
                       IconButton(
                         icon: const Icon(Icons.edit),
                         tooltip: 'تعديل المتجر',
                         onPressed: () => _showEditStoreDialog(context),
                       )
                  ],
                ),
                Expanded(
                  child: _buildContent(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    switch (_selectedIndex) {
      case 0:
        return ProductsTab(sellerId: widget.seller.sellerId, isEditable: widget.isSellerMode);
      case 1:
        return OrdersTab(sellerId: widget.seller.sellerId, isEditable: widget.isSellerMode);
      case 2:
        return CategoriesTab(sellerId: widget.seller.sellerId, isEditable: widget.isSellerMode);
      case 3:
        if (widget.isSellerMode) {
          return CreditCustomersScreen(sellerId: widget.seller.sellerId);
        }
        return const Center(child: Text('غير مصرح'));
      default:
        return const Center(child: Text('غير موجود'));
    }
  }
}
