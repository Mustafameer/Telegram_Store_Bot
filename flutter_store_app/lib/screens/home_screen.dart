

import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import '../services/telegram_service.dart';
import 'store_detail_screen.dart';
import 'login_screen.dart';
import 'cart_screen.dart';

class HomeScreen extends StatefulWidget {
  final bool isAdmin;
  const HomeScreen({super.key, this.isAdmin = false});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
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
                  // Logout
                 Navigator.of(context).pushReplacement(
                    MaterialPageRoute(builder: (context) => const LoginScreen()),
                  );
                  return;
               }
               setState(() {
                _selectedIndex = index;
              });
            },
            leading: IconButton(
              icon: Icon(_isExtended ? Icons.menu_open : Icons.menu),
              onPressed: () {
                setState(() {
                  _isExtended = !_isExtended;
                });
              },
            ),
            labelType: _isExtended ? NavigationRailLabelType.none : NavigationRailLabelType.selected,
            destinations: [
              const NavigationRailDestination(
                icon: Icon(Icons.dashboard),
                label: Text('لوحة التحكم'),
              ),
              if (widget.isAdmin)
                const NavigationRailDestination(
                  icon: Icon(Icons.store),
                  label: Text('متجري'),
                ),
               const NavigationRailDestination(
                icon: Icon(Icons.shopping_cart),
                label: Text('سلة المشتريات'), // For demo/tracking
              ),
               const NavigationRailDestination(
                icon: Icon(Icons.logout, color: Colors.red),
                label: Text('خروج', style: TextStyle(color: Colors.red)),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_selectedIndex == 0) {
      return const DashboardView();
    } else if (_selectedIndex == 1 && widget.isAdmin) {
      // Show Admin's Store
      // We need to fetch Admin's seller profile.
      // For now, we assume Admin has a store or create one dynamically?
      // Let's look up seller by Admin ID.
      return const AdminStoreLoader();
    } else if (_selectedIndex == 2) {
      // Cart View (As User/Buyer mode)
      // Using Admin ID as User ID for demo
      return const CartScreen(userId: 1041977029); 
    }
    return const Center(child: Text('جاري العمل...'));
  }
}

class DashboardView extends StatefulWidget {
  const DashboardView({super.key});

  @override
  State<DashboardView> createState() => _DashboardViewState();
}

class _DashboardViewState extends State<DashboardView> {
  late Future<List<Seller>> _sellersFuture;

  @override
  void initState() {
    super.initState();
    _refreshSellers();
  }

  void _refreshSellers() {
    setState(() {
      _sellersFuture = DatabaseHelper.instance.getAllSellers();
    });
  }

  Future<void> _toggleSellerStatus(Seller seller) async {
    final newStatus = seller.status == 'active' ? 'suspended' : 'active';
    await DatabaseHelper.instance.updateSellerStatus(seller.sellerId, newStatus);
    
    // Notify Seller
    final message = newStatus == 'active' 
      ? '✅ تم تنشيط متجرك من قبل المسؤول'
      : '⛔ تم تعليق متجرك من قبل المسؤول';
    
    // Send Telegram Message
    await TelegramService.sendMessage(seller.telegramId, message);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('تم تغيير الحالة وإرسال إشعار')));
      _refreshSellers();
    }
  }
  
  Future<void> _showAddStoreDialog() async {
    final nameController = TextEditingController();
    final idController = TextEditingController();
    final userController = TextEditingController();
    
    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('إضافة متجر جديد'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'اسم المتجر'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: idController,
              decoration: const InputDecoration(labelText: 'معرف تليجرام البائع (ID)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: userController,
              decoration: const InputDecoration(labelText: 'اسم المستخدم (User)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
               if (nameController.text.isNotEmpty && idController.text.isNotEmpty) {
                 final telegramId = int.tryParse(idController.text);
                 if (telegramId != null) {
                   await DatabaseHelper.instance.addSeller(nameController.text, telegramId, userController.text);
                   if (mounted) {
                      Navigator.pop(context);
                      _refreshSellers();
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم إضافة المتجر بنجاح')));
                   }
                 }
               }
            },
            child: const Text('إضافة'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('إدارة المتاجر'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _refreshSellers)],
      ),
      body: FutureBuilder<List<Seller>>(
        future: _sellersFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('لا يوجد متاجر'));

          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 300,
              childAspectRatio: 1.1,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
            ),
            itemCount: snapshot.data!.length,
            itemBuilder: (context, index) {
              final seller = snapshot.data![index];
              return _buildSellerCard(context, seller);
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddStoreDialog,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildSellerCard(BuildContext context, Seller seller) {
    return Card(
      elevation: 4,
       child: Stack(
            children: [
              InkWell(
                onTap: () {
                   Navigator.push(context, MaterialPageRoute(builder: (_) => StoreDetailScreen(seller: seller, isSellerMode: false)));
                },
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircleAvatar(
                      radius: 30,
                      child: Text(seller.storeName?[0] ?? 'S', style: const TextStyle(fontSize: 24)),
                    ),
                    const SizedBox(height: 10),
                    Text(seller.storeName ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(seller.status ?? 'Unknown', style: TextStyle(color: seller.status == 'active' ? Colors.green : Colors.red)),
                  ],
                ),
              ),
              Positioned(
                top: 0,
                right: 0,
                child: PopupMenuButton<String>(
                  onSelected: (v) {
                    if (v == 'toggle') _toggleSellerStatus(seller);
                  },
                  itemBuilder: (c) => [
                    PopupMenuItem(value: 'toggle', child: Text(seller.status == 'active' ? 'تعليق' : 'تنشيط'))
                  ],
                ),
              )
            ]
       ),
    );
  }
}

class AdminStoreLoader extends StatelessWidget {
  const AdminStoreLoader({super.key});

  @override
  Widget build(BuildContext context) {
    // 1041977029 is Admin ID
    return FutureBuilder<Seller?>(
      future: DatabaseHelper.instance.getSellerByTelegramId(1041977029),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasData && snapshot.data != null) {
          return StoreDetailScreen(seller: snapshot.data!, isSellerMode: true);
        } else {
           // Admin doesn't have a store yet, maybe offer to create one?
           // For now just show message.
           return Center(
             child: Column(
               mainAxisAlignment: MainAxisAlignment.center,
               children: [
                 const Text('لم تقم بإنشاء متجر خاص بك بعد'),
                 const SizedBox(height: 16),
                 FilledButton(
                   onPressed: () {
                     // Create store logic would go here
                     ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('يرجى إنشاء متجر عبر البوت أولاً')));
                   },
                   child: const Text('إنشاء متجر'),
                 )
               ],
             ),
           );
        }
      },
    );
  }
}
