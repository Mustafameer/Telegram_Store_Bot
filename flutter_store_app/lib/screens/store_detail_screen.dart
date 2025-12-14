

import 'package:flutter/material.dart';
import '../models/database_models.dart';
import 'tabs/products_tab.dart';
import 'tabs/orders_tab.dart';
import 'tabs/categories_tab.dart';
import 'login_screen.dart';

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
  bool _isExtended = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: _isExtended,
            selectedIndex: _selectedIndex,
            onDestinationSelected: (int index) {
              if (index == 3) {
                // Logout logic if Seller Mode, or Back if Viewer
                if (widget.isSellerMode) {
                   Navigator.of(context).pushReplacement(
                      MaterialPageRoute(builder: (context) => const LoginScreen()),
                   );
                } else {
                   Navigator.of(context).pop();
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
                if (!widget.isSellerMode)
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
              NavigationRailDestination(
                icon: Icon(
                  widget.isSellerMode ? Icons.logout : Icons.arrow_back, 
                  color: widget.isSellerMode ? Colors.red : null
                ),
                label: Text(
                  widget.isSellerMode ? 'خروج' : 'رجوع', 
                  style: TextStyle(color: widget.isSellerMode ? Colors.red : null)
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
      default:
        return const Center(child: Text('غير موجود'));
    }
  }
}
