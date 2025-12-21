

import 'package:flutter/material.dart';
import 'dart:io';
import 'dart:async'; // Added for StreamSubscription
import '../models/database_models.dart';
import '../services/sync_service.dart'; // Added for SyncService
import 'tabs/products_tab.dart';
import 'tabs/orders_tab.dart';
import 'tabs/categories_tab.dart';
import 'credit_customers_screen.dart';
import 'credit_customers_screen.dart';
import 'messages_screen.dart';
import 'login_screen.dart';
import 'cart_screen.dart';
import 'components/store_form_dialog.dart';
import '../database/database_helper.dart';
import 'home_screen.dart';

class StoreDetailScreen extends StatefulWidget {
  final Seller seller;
  final bool isSellerMode;
  final int? currentUserId; // Can be null if not passed, but we should pass it for Buyer Mode

  const StoreDetailScreen({
    super.key, 
    required this.seller,
    this.isSellerMode = false,
    this.currentUserId,
  });

  @override
  State<StoreDetailScreen> createState() => _StoreDetailScreenState();
}

class _StoreDetailScreenState extends State<StoreDetailScreen> {
  int _selectedIndex = 0;
  bool _isExtended = true;

  Map<String, int> _counts = {
    'products': 0, 
    'orders': 0, 
    'categories': 0, 
    'customers': 0, 
    'messages': 0,
    'cart': 0
  };

  StreamSubscription? _syncSub;

  @override
  void initState() {
    super.initState();
    _refreshCounts();
    
    // Listen for Sync Success to auto-refresh badges
    _syncSub = SyncService.instance.statusStream.listen((status) {
       if (status.contains('Completed') || status.contains('Success')) {
          _refreshCounts();
       }
    });
  }

  @override
  void dispose() {
    _syncSub?.cancel();
    super.dispose();
  }

  Future<void> _refreshCounts() async {
    // Refresh for both Seller (stats) and Buyer (cart/products)
    // if (!widget.isSellerMode) return;  <-- REMOVED limitation
    
    final sellerId = widget.seller.sellerId;
    final products = await DatabaseHelper.instance.getProductsCount(sellerId);
    final categories = await DatabaseHelper.instance.getCategoriesCount(sellerId);
    
    int orders = 0;
    int customers = 0;
    int messages = 0;
    int cart = 0;

    if (widget.isSellerMode) {
       orders = await DatabaseHelper.instance.getOrdersCount(sellerId);
       customers = await DatabaseHelper.instance.getCustomersCount(sellerId);
       messages = await DatabaseHelper.instance.getMessagesCount(sellerId);
    } else {
       // Buyer Mode
       if (widget.currentUserId != null) {
          cart = await DatabaseHelper.instance.getCartCount(widget.currentUserId!);
       }
    }
    
    if (mounted) {
      setState(() {
        _counts = {
          'products': products,
          'orders': orders,
          'categories': categories,
          'customers': customers,
          'messages': messages,
          'cart': cart
        };
      });
    }
  }

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
           }
        },
      ),
    );
  }

  List<Map<String, dynamic>> _getDestinations(bool canPop) {
    return [
      {'icon': Icons.shopping_bag, 'label': 'المنتجات', 'count': _counts['products']},
      {'icon': Icons.category, 'label': 'الفئات', 'count': _counts['categories']},
      if (!widget.isSellerMode) {'icon': Icons.shopping_cart, 'label': 'السلة', 'count': _counts['cart']},
      if (widget.isSellerMode) {'icon': Icons.list_alt, 'label': 'الطلبات', 'count': _counts['orders']},
      if (widget.isSellerMode) {'icon': Icons.people, 'label': 'ادارة الزبائن', 'count': _counts['customers']},
      if (widget.isSellerMode) {'icon': Icons.description, 'label': 'كشف حساب', 'count': 0}, 
      if (widget.isSellerMode) {'icon': Icons.message, 'label': 'الرسائل', 'count': _counts['messages']},
      {'icon': canPop ? Icons.arrow_back : Icons.logout, 'label': canPop ? 'رجوع' : 'خروج', 'isExit': true},
    ];
  }

  void _onDestinationSelected(int index, bool canPop) {
    
    // Determine the index of the "Exit" button dynamically based on modes
    final destinations = _getDestinations(canPop);
    final isExit = destinations[index]['isExit'] == true;

    if (isExit) {
      if (canPop) {
        Navigator.of(context).pop();
      } else {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const LoginScreen()),
        );
      }
      return;
    }
    setState(() {
      _selectedIndex = index;
    });
    _refreshCounts(); 
  }

  @override
  Widget build(BuildContext context) {
    final bool canPop = Navigator.canPop(context);
    final width = MediaQuery.of(context).size.width;
    final bool isMobile = width < 900;
    final destinations = _getDestinations(canPop);

    // Mobile Layout (Drawer)
    if (isMobile) {
      return Scaffold(
        appBar: AppBar(
          title: Text('${widget.seller.storeName ?? 'تفاصيل المتجر'} ${widget.isSellerMode ? '(Admin)' : '(Buyer)'}'),
          actions: [
            if (widget.isSellerMode)
              IconButton(
                icon: const Icon(Icons.visibility),
                tooltip: 'وضع المشتري',
                onPressed: () {
                  // User expects "Buyer Mode" to mean "Go to Marketplace"
                  Navigator.of(context).pushReplacement(
                     MaterialPageRoute(builder: (context) => HomeScreen(
                       isAdmin: false, 
                       // Keep isSeller true so they see "My Store" tab if they want to come back
                       isSeller: true, 
                       currentUserId: widget.currentUserId ?? widget.seller.telegramId
                     ))
                  );
                },
              ),
            if (widget.isSellerMode)
              IconButton(
                icon: const Icon(Icons.edit),
                tooltip: 'تعديل المتجر',
                onPressed: () => _showEditStoreDialog(context),
              )
          ],
        ),
        drawer: Drawer(
          child: Column(
            children: [
              UserAccountsDrawerHeader(
                decoration: const BoxDecoration(color: Colors.blue),
                accountName: Text(widget.seller.storeName ?? 'Store'),
                accountEmail: Text(widget.seller.userName ?? ''),
                currentAccountPicture: CircleAvatar(
                   backgroundImage: widget.seller.imagePath != null ? FileImage(File(widget.seller.imagePath!)) : null,
                   child: widget.seller.imagePath == null ? const Icon(Icons.store) : null,
                ),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: destinations.length,
                  itemBuilder: (context, index) {
                    final item = destinations[index];
                    final isExit = item['isExit'] == true && !canPop; 
                  return ListTile(
                      leading: Badge(
                        isLabelVisible: (item['count'] as int? ?? 0) > 0,
                        label: Text('${item['count']}'),
                        child: Icon(item['icon'], color: isExit ? Colors.red : null)
                      ),
                      title: Text(item['label'], style: TextStyle(color: isExit ? Colors.red : null)),
                      selected: _selectedIndex == index,
                      onTap: () {
                        if (!isExit) {
                          Navigator.pop(context); // Close drawer only for internal nav
                        }
                        _onDestinationSelected(index, canPop);
                      },
                    );
                  },
                ),
              )
            ],
          ),
        ),
        body: _buildContent(),
      );
    }

    // Desktop Layout (Row + NavigationRail)
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: _isExtended,
            selectedIndex: _selectedIndex,
            onDestinationSelected: (index) => _onDestinationSelected(index, canPop),
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
                if (canPop && !widget.isSellerMode)
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => Navigator.of(context).pop(),
                    tooltip: 'رجوع',
                  ),
              ],
            ),
            labelType: _isExtended ? NavigationRailLabelType.none : NavigationRailLabelType.selected,
            destinations: destinations.map((item) {
              final isExit = item['isExit'] == true && !canPop;
              final count = item['count'] as int? ?? 0;
              return NavigationRailDestination(
                icon: Badge(
                  isLabelVisible: count > 0,
                  label: Text('$count'),
                  child: Icon(item['icon'], color: isExit ? Colors.red : null)
                ),
                label: Text(item['label'], style: TextStyle(color: isExit ? Colors.red : null)),
              );
            }).toList(),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Column(
              children: [
                AppBar(
                  title: Text('${widget.seller.storeName ?? 'تفاصيل المتجر'} ${widget.isSellerMode ? '(Admin)' : '(Buyer)'}'),
                  centerTitle: false,
                  automaticallyImplyLeading: false,
                  actions: [
                     if (widget.isSellerMode)
                       IconButton(
                         icon: const Icon(Icons.visibility),
                         tooltip: 'وضع المشتري',
                          onPressed: () {
                           // User expects "Buyer Mode" to mean "Go to Marketplace"
                           Navigator.of(context).pushReplacement(
                              MaterialPageRoute(builder: (context) => HomeScreen(
                                isAdmin: false, 
                                isSeller: true, 
                                currentUserId: widget.currentUserId ?? widget.seller.telegramId
                              ))
                           );
                         },
                       ),
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
    // Determine content based on Index and Mode
    // 0: Products
    // 1: Categories
    // 2: Cart (Buyer) OR Orders (Seller)
    // 3+: Seller Tabs
    
    // Simpler mapping approach:
    final destinations = _getDestinations(Navigator.canPop(context));
    // Index is safe if updated correctly
    
    if (_selectedIndex == 0) {
       return ProductsTab(
          sellerId: widget.seller.sellerId, 
          isEditable: widget.isSellerMode,
          onCartChanged: _refreshCounts,
          currentUserId: widget.currentUserId,
        );
    } 
    else if (_selectedIndex == 1) {
       return CategoriesTab(sellerId: widget.seller.sellerId, isEditable: widget.isSellerMode);
    }
    
    // Dynamic Tabs
    final label = destinations[_selectedIndex]['label'];
    
    if (label == 'السلة') return CartScreen(userId: widget.currentUserId ?? 0); 
    if (label == 'الطلبات') return OrdersTab(sellerId: widget.seller.sellerId, isEditable: widget.isSellerMode);
    if (label == 'ادارة الزبائن') return CreditCustomersScreen(sellerId: widget.seller.sellerId);
    if (label == 'كشف حساب') return CreditCustomersScreen(sellerId: widget.seller.sellerId);
    if (label == 'الرسائل') return MessagesScreen(sellerId: widget.seller.sellerId);
    
    return const Center(child: Text('جاري العمل...'));
  }
}
