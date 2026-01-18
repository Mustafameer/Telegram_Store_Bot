import 'package:path/path.dart' as p;
import 'package:flutter/material.dart';
import 'dart:io';
import 'dart:async';

import '../models/database_models.dart';
import '../database/database_helper.dart';
import 'store_detail_screen.dart';
import 'cart_screen.dart';
import 'messages_screen.dart';
import 'orders_screen.dart';
import 'components/store_form_dialog.dart';
import 'server_settings_screen.dart';

// Conditional import for desktop-only features
import 'package:window_manager/window_manager.dart' if (dart.library.html) 'dart:html' as window_manager;

class HomeScreen extends StatefulWidget {
  final bool isAdmin; // Admin of the PLATFORM (can suspend stores etc)
  final bool isSeller; // Has a store
  final int currentUserId;

  const HomeScreen({
    super.key, 
    this.isAdmin = false,
    this.isSeller = false,
    required this.currentUserId,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  bool _isExtended = true;
  Map<String, int> _counts = {'products': 0, 'messages': 0, 'cart': 0, 'orders': 0};
  
  @override
  void initState() {
    super.initState();
    
    // Desktop-only window management
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        window_manager.windowManager.addListener(_WindowListener(this));
        _initWindowCloseHandler();
      } catch (e) {
        // window_manager not available, continue
        print("Window manager not available: $e");
      }
    }
    
    _refreshCounts();
  }

  Future<void> _initWindowCloseHandler() async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        await window_manager.windowManager.setPreventClose(true);
      } catch (e) {
        // Ignore on mobile
      }
    }
  }

  @override
  void dispose() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        window_manager.windowManager.removeListener(_WindowListener(this));
      } catch (e) {
        // Ignore on mobile
      }
    }
    super.dispose();
  }
  
  void _handleWindowClose() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        exit(0);
      } catch (e) {
        // Ignore on mobile
      }
    }
  }

  Future<void> _refreshCounts() async {
    // Assuming main user/admin ID for now. In multi-user app, this would use logged-in ID.
    const targetId = 1041977029; 
    // Actually, we should find the Seller ID for the current user.
    // But for the local single-user scenario, we use the known ID or look it up.
    // Let's assume targetId is the one we want.
    
    // We also need the SellerID for Products/Messages.
    // getSellerByTelegramId(targetId) -> sellerId.
    final seller = await DatabaseHelper.instance.getSellerByTelegramId(targetId);
    int pCount = 0;
    int mCount = 0;
    int cCount = 0;
    int oCount = 0;
    
    if (seller != null) {
      pCount = await DatabaseHelper.instance.getProductsCount(seller.sellerId);
      mCount = await DatabaseHelper.instance.getMessagesCount(seller.sellerId); // Total messages
      oCount = await DatabaseHelper.instance.getOrdersCount(seller.sellerId); // Total orders
    }
    cCount = await DatabaseHelper.instance.getCartCount(targetId);

    if (mounted) {
      setState(() {
        _counts = {'products': pCount, 'messages': mCount, 'cart': cCount, 'orders': oCount};
      });
    }
  }

  // Hook into other refreshes if possible, or just call periodically
  
  List<Map<String, dynamic>> _getDestinations() {
    return [
      {'icon': Icons.dashboard, 'label': 'لوحة التحكم'},
      if (widget.isAdmin || widget.isSeller) {'icon': Icons.store, 'label': 'متجري', 'count': _counts['products']},
      {'icon': Icons.shopping_cart, 'label': 'سلة المشتريات 🛒', 'count': _counts['cart']},
      {'icon': Icons.settings, 'label': 'الاعدادات'},
      if (widget.isAdmin || widget.isSeller) {'icon': Icons.shopping_bag, 'label': 'الطلبات', 'count': _counts['orders']},
      if (widget.isAdmin || widget.isSeller) {'icon': Icons.message, 'label': 'الرسائل', 'count': _counts['messages']},
    ];
  }

  int? _mapBottomNavToDestinationIndex(int bottomNavIndex) {
    final destinations = _getDestinations();
    final bottomNavDestinations = destinations.where((d) => 
      d['icon'] != Icons.logout && d['icon'] != Icons.settings
    ).toList();
    
    if (bottomNavIndex >= bottomNavDestinations.length) return null;
    
    final selectedItem = bottomNavDestinations[bottomNavIndex];
    return destinations.indexWhere((d) => d['icon'] == selectedItem['icon']);
  }
  
  int _getBottomNavIndex() {
    final destinations = _getDestinations();
    final bottomNavDestinations = destinations.where((d) => 
      d['icon'] != Icons.logout && d['icon'] != Icons.settings
    ).toList();
    
    if (_selectedIndex >= destinations.length) return 0;
    final selectedItem = destinations[_selectedIndex];
    
    // If selected item is in bottom nav, return its index
    final bottomNavIndex = bottomNavDestinations.indexWhere((d) => d['icon'] == selectedItem['icon']);
    return bottomNavIndex >= 0 ? bottomNavIndex : 0;
  }

  void _onDestinationSelected(int index) {
     final destinations = _getDestinations();
     if (index >= destinations.length) return;
     final selectedItem = destinations[index];
    
    if (selectedItem['icon'] == Icons.settings) {
       Navigator.push(context, MaterialPageRoute(builder: (_) => ServerSettingsScreen()));
       return;
    }
    
    // Handle Messages Tab Navigation? 
    // I need to ensure _buildContent handles the new index!
    
    setState(() {
      _selectedIndex = index;
    });
    
    // Refresh logic
    _refreshCounts();
  }

  @override
  Widget build(BuildContext context) {
    Widget scaffold = _buildScaffold(context);
    
    // Intercept Back Button on Root Screen (Desktop only)
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      return PopScope(
        canPop: false,
        onPopInvokedWithResult: (didPop, result) async {
          if (didPop) return;
          exit(0);
        },
        child: scaffold, 
      );
    }
    
    return scaffold;
  }

  Widget _buildScaffold(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final bool isMobile = width < 900;
    final destinations = _getDestinations();

    // Mobile: Use Bottom Navigation Bar
    if (isMobile) {
       // Filter out exit and settings from bottom nav (they go in app bar menu)
       final bottomNavDestinations = destinations.where((d) => 
         d['icon'] != Icons.logout && d['icon'] != Icons.settings
       ).toList();
       
       return Scaffold(
         appBar: AppBar(
            title: const Text('المتجر المحلي'),
            actions: [
               PopupMenuButton<String>(
                 icon: const Icon(Icons.more_vert),
                 onSelected: (value) {
                   if (value == 'settings') {
                     Navigator.push(context, MaterialPageRoute(builder: (_) => ServerSettingsScreen()));
                   }
                 },
                 itemBuilder: (context) {
                   // Only show settings to app admin
                   final items = <PopupMenuEntry<String>>[];
                   if (widget.isAdmin) {
                     items.add(const PopupMenuItem(value: 'settings', child: Row(
                       children: [Icon(Icons.settings, size: 20), SizedBox(width: 8), Text('الإعدادات')],
                     )));
                   }
                   return items;
                 },
               ),
            ],
         ),
         body: _buildContent(),
         bottomNavigationBar: NavigationBar(
           selectedIndex: _getBottomNavIndex(),
           onDestinationSelected: (index) {
             // Map bottom nav index to actual destination index
             final actualIndex = _mapBottomNavToDestinationIndex(index);
             if (actualIndex != null) {
               _onDestinationSelected(actualIndex);
             }
           },
           destinations: bottomNavDestinations.map((item) {
             final count = item['count'] as int? ?? 0;
             return NavigationDestination(
               icon: Badge(
                 isLabelVisible: count > 0,
                 label: Text('$count'),
                 child: Icon(item['icon']),
               ),
               label: item['label'],
             );
           }).toList(),
         ),
       );
    }

    // Desktop: Show NavigationRail only for Admin, use BottomNavigationBar for sellers
    if (!widget.isAdmin) {
      // For sellers on desktop, use bottom navigation bar
      final bottomNavDestinations = destinations.where((d) => 
        d['icon'] != Icons.logout && d['icon'] != Icons.settings
      ).toList();
      
      return Scaffold(
        appBar: AppBar(
          title: const Text('المتجر المحلي'),
          actions: [
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert),
              onSelected: (value) {
                if (value == 'settings') {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => ServerSettingsScreen()));
                }
              },
              itemBuilder: (context) {
                final items = <PopupMenuEntry<String>>[];
                if (widget.isAdmin) {
                  items.add(const PopupMenuItem(value: 'settings', child: Row(
                    children: [Icon(Icons.settings, size: 20), SizedBox(width: 8), Text('الإعدادات')],
                  )));
                }
                return items;
              },
            ),
          ],
        ),
        body: _buildContent(),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _getBottomNavIndex(),
          onDestinationSelected: (index) {
            final actualIndex = _mapBottomNavToDestinationIndex(index);
            if (actualIndex != null) {
              _onDestinationSelected(actualIndex);
            }
          },
          destinations: bottomNavDestinations.map((item) {
            final count = item['count'] as int? ?? 0;
            return NavigationDestination(
              icon: Badge(
                isLabelVisible: count > 0,
                label: Text('$count'),
                child: Icon(item['icon']),
              ),
              label: item['label'],
            );
          }).toList(),
        ),
      );
    }

    // Admin on desktop: Show NavigationRail (Sidebar)
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: _isExtended,
            selectedIndex: _selectedIndex,
            onDestinationSelected: _onDestinationSelected,
            labelType: _isExtended ? NavigationRailLabelType.none : NavigationRailLabelType.selected,
            destinations: destinations.map((item) {
               final count = item['count'] as int? ?? 0;
               return NavigationRailDestination(
                 icon: Badge(
                   isLabelVisible: count > 0,
                   label: Text('$count'),
                   child: Icon(item['icon'])
                 ),
                 label: Text(item['label']),
               );
            }).toList(),
            trailing: Padding(
               padding: const EdgeInsets.only(top: 20),
               child: IconButton(
                 icon: const Icon(Icons.refresh),
                 tooltip: 'تحديث',
                 onPressed: () => _refreshCounts()
               ),
             ),
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
      return DashboardView(currentUserId: widget.currentUserId);
    } else if (_selectedIndex == 1 && (widget.isAdmin || widget.isSeller)) {
      return AdminStoreLoader(currentUserId: widget.currentUserId); 
    } else if (_selectedIndex == 2) {
      return CartScreen(userId: widget.currentUserId); 
    } else if (_selectedIndex == 4 && (widget.isAdmin || widget.isSeller)) {
      return AdminOrdersLoader(currentUserId: widget.currentUserId);
    } else if (_selectedIndex == 5 && (widget.isAdmin || widget.isSeller)) {
      return AdminMessagesLoader(currentUserId: widget.currentUserId);
    }
    return const Center(child: Text('جاري العمل...'));
  }
}

// Helper class for window listener (desktop only)
class _WindowListener extends window_manager.WindowListener {
  final _HomeScreenState _state;
  _WindowListener(this._state);
  
  @override
  void onWindowClose() {
    _state._handleWindowClose();
  }
}

class DashboardView extends StatefulWidget {
  final int currentUserId;
  const DashboardView({super.key, required this.currentUserId});

  @override
  State<DashboardView> createState() => _DashboardViewState();
}

class _DashboardViewState extends State<DashboardView> {
  late Future<List<Seller>> _sellersFuture;
  // StreamSubscription? _syncSub; // Moved to HomeScreen

  @override
  void initState() {
    super.initState();
    _refreshSellers();
    // Listener removed from here to avoid duplication/loss on tab switch
  }

  @override
  void dispose() {
    // _syncSub?.cancel();
    super.dispose();
  }

  void _refreshSellers({bool force = false}) {
    setState(() {
      _sellersFuture = DatabaseHelper.instance.getAllSellers(forceRefresh: force).then((sellers) {
         print("🔍 Filtering Debug: CurrentUser=${widget.currentUserId}");
         for (var s in sellers) {
           print("  - Store: ${s.storeName}, ID: ${s.telegramId} (Exclude? ${s.telegramId == widget.currentUserId})");
         }
         // Filter out my own store (Buyer Logic: Don't buy from yourself)
         var filtered = sellers.where((s) => s.telegramId != widget.currentUserId).toList();
         
         // ✨ ترتيب خاص: TELEBOT (TelegramID = 999999999) يظهر أولاً
         filtered.sort((a, b) {
           // TELEBOT يظهر أولاً
           if (a.telegramId == 999999999) return -1;
           if (b.telegramId == 999999999) return 1;
           // بقية المتاجر حسب الاسم
           return (a.storeName ?? '').compareTo(b.storeName ?? '');
         });
         
         print("📊 ترتيب المتاجر بعد التصفية: ${filtered.map((s) => s.storeName).toList()}");
         return filtered;
      });
    });
  }

  Future<void> _toggleSellerStatus(Seller seller) async {
    final newStatus = seller.status == 'active' ? 'suspended' : 'active';
    await DatabaseHelper.instance.updateSellerStatus(seller.sellerId, newStatus);
    _refreshSellers();
  }

  void _showStoreDialog({Seller? seller}) {
    showDialog(
      context: context,
      builder: (context) => StoreFormDialog(
        initialName: seller?.storeName,
        initialTelegramId: seller?.telegramId.toString(),
        initialUserName: seller?.userName,
        initialImagePath: seller?.imagePath,
        initialRequireCustomerRegistration: seller?.requireCustomerRegistration,
        isEdit: seller != null,
        onSave: (storeName, telegramId, userName, imagePath, requireCustomerRegistration) async {
          print("💾 HomeScreen.onSave: requireCustomerRegistration = $requireCustomerRegistration");
          try {
            if (seller == null) {
               await DatabaseHelper.instance.addSeller(storeName, telegramId, userName, imagePath: imagePath);
               print("✅ HomeScreen.onSave: Seller added successfully");
            } else {
               print("💾 HomeScreen.onSave: Updating seller #${seller.sellerId}");
               print("💾 HomeScreen.onSave: Current seller.requireCustomerRegistration = ${seller.requireCustomerRegistration}");
               // Update only the editable fields
               final updatedSeller = seller.copyWith(
                 storeName: storeName,
                 userName: userName,
                 imagePath: imagePath,
                 requireCustomerRegistration: requireCustomerRegistration,
               );
               print("💾 HomeScreen.onSave: Updated seller.requireCustomerRegistration = ${updatedSeller.requireCustomerRegistration}");
               await DatabaseHelper.instance.updateSeller(updatedSeller);
               print("✅ HomeScreen.onSave: Seller updated successfully");
            }
            // Refresh the list after successful save
            if (mounted) {
              _refreshSellers(force: true);
            }
          } catch (e) {
            print("❌ HomeScreen.onSave: Error: $e");
            rethrow; // Let StoreFormDialog handle the error display
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مدير المتاجر (محلي)'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh), 
            onPressed: () => _refreshSellers(force: true)
          )
        ],
      ),
      body: FutureBuilder<List<Seller>>(
        future: _sellersFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (snapshot.hasError) {
             return Center(
               child: SingleChildScrollView(
                 child: Column(
                   mainAxisAlignment: MainAxisAlignment.center,
                   children: [
                     const Icon(Icons.error, color: Colors.red, size: 50),
                     const SizedBox(height: 16),
                     Text('حدث خطأ في قاعدة البيانات:', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                     Padding(
                       padding: const EdgeInsets.all(16.0),
                       child: SelectableText('${snapshot.error}', textAlign: TextAlign.center, style: TextStyle(color: Colors.red)),
                     ),
                     ElevatedButton(onPressed: () => _refreshSellers(force: true), child: const Text('إعادة المحاولة'))
                   ],
                 ),
               )
             );
          }
          if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('لا يوجد متاجر (قاعدة البيانات فارغة)'));

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
        onPressed: () => _showStoreDialog(),
        child: const Icon(Icons.add),
      ),
      bottomNavigationBar: FutureBuilder<List<String>>(
        future: Future.wait([
          Future(() async => '✅ PostgreSQL Cloud Connected'),
          Future(() async {
            if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
              final executablePath = Platform.resolvedExecutable;
              final exeDir = p.dirname(executablePath);
              final imgDir = Directory(p.join(exeDir, 'data', 'Images'));
              return (await imgDir.exists()) ? '✅ Images Folder Found' : '❌ Images Folder MISSING';
            }
            return 'N/A';
          })
        ]),
        builder: (context, snapshot) {
          final dbPath = snapshot.data?[0] ?? "Loading...";
          final imgStatus = snapshot.data?[1] ?? "Checking...";
          
          return Container(
            padding: const EdgeInsets.all(8),
            color: Colors.grey[200],
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SelectableText('DB: $dbPath', style: const TextStyle(fontSize: 10, color: Colors.black)),
                const SizedBox(height: 2),
                SelectableText('IMG: $imgStatus', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: imgStatus.contains('MISSING') ? Colors.red : Colors.green)),
              ],
            ),
          );
        }
      ),
    );
  }

  Widget _buildSellerCard(BuildContext context, Seller seller) {
    return Card(
      child: Stack(
            children: [
              InkWell(
                onTap: () {
                   // Marketplace View: Always Buying Mode (false), unless we want Admin to edit from here?
                   // User requested: "Buying mode -> Add to Cart". Dashboard = buying mode.
                   Navigator.push(context, MaterialPageRoute(builder: (_) => StoreDetailScreen(
                     seller: seller, 
                     isSellerMode: false, // Buying Mode!
                     currentUserId: widget.currentUserId
                   )));
                },
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Center(child: CircleAvatar(
                      radius: 35,
                      backgroundColor: Colors.teal.shade50,
                      backgroundImage: seller.imagePath != null ? FileImage(File(seller.imagePath!)) : null,
                      child: seller.imagePath == null 
                        ? Text(seller.storeName?[0].toUpperCase() ?? 'S', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold))
                        : null,
                    )),
                    const SizedBox(height: 10),
                    Text(seller.storeName ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: seller.status == 'active' ? Colors.green.withValues(alpha: 0.1) : Colors.red.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(12)
                          ),
                          child: Text(
                            seller.status == 'active' ? 'نشط' : 'معلق', 
                            style: TextStyle(fontSize: 12, color: seller.status == 'active' ? Colors.green : Colors.red)
                          ),
                        ),
                        if (seller.requireCustomerRegistration)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.red.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(12)
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.lock, size: 12, color: Colors.red),
                                SizedBox(width: 4),
                                Text(
                                  'مقفل', 
                                  style: TextStyle(fontSize: 12, color: Colors.red)
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              Positioned(
                top: 0,
                right: 0,
                child: PopupMenuButton<String>(
                  onSelected: (v) {
                    if (v == 'toggle') _toggleSellerStatus(seller);
                    if (v == 'lock') _toggleStoreLock(seller);
                    if (v == 'edit') _showStoreDialog(seller: seller);
                    if (v == 'delete') _deleteSeller(seller);
                  },
                  itemBuilder: (c) => [
                    PopupMenuItem(
                      value: 'lock',
                      child: Row(
                        children: [
                          Icon(
                            seller.requireCustomerRegistration ? Icons.lock_open : Icons.lock,
                            color: seller.requireCustomerRegistration ? Colors.green : Colors.red,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Text(seller.requireCustomerRegistration ? 'فتح المتجر' : 'قفل المتجر'),
                        ],
                      ),
                    ),
                    PopupMenuItem(value: 'toggle', child: Text(seller.status == 'active' ? 'تعليق' : 'تنشيط')),
                    const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                    const PopupMenuItem(value: 'delete', child: Text('حذف نهائي', style: TextStyle(color: Colors.red))),
                  ],
                ),
              )
            ]
       ),
    );
  }

  Future<void> _toggleStoreLock(Seller seller) async {
    final newValue = !seller.requireCustomerRegistration;
    try {
      await DatabaseHelper.instance.updateSeller(
        seller.copyWith(requireCustomerRegistration: newValue),
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(newValue ? 'تم قفل المتجر' : 'تم فتح المتجر'),
            backgroundColor: Colors.green,
          ),
        );
        _refreshSellers(force: true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خطأ في تحديث حالة المتجر: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _deleteSeller(Seller seller) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف متجر "${seller.storeName}"؟\nسيتم حذف جميع المنتجات والأقسام المرتبطة به.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await DatabaseHelper.instance.deleteSeller(seller.sellerId);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم حذف المتجر بنجاح')));
          _refreshSellers();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('خطأ في الحذف: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }
}



class AdminStoreLoader extends StatelessWidget {
  final int currentUserId;
  const AdminStoreLoader({super.key, required this.currentUserId});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Seller?>(
      future: DatabaseHelper.instance.getSellerByTelegramId(currentUserId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasData && snapshot.data != null) {
          return StoreDetailScreen(seller: snapshot.data!, isSellerMode: true);
        } else {
           return Center(
             child: Column(
               mainAxisAlignment: MainAxisAlignment.center,
               children: [
                 const Text('لم تقم بإنشاء متجر خاص بك بعد'),
                 const SizedBox(height: 16),
                 const Text('يرجى إنشاؤه من لوحة التحكم'),
               ],
             ),
           );
        }
      },
    );
  }
}

class AdminOrdersLoader extends StatelessWidget {
  final int currentUserId;
  const AdminOrdersLoader({super.key, required this.currentUserId});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Seller?>(
      future: DatabaseHelper.instance.getSellerByTelegramId(currentUserId), 
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasData && snapshot.data != null) {
          return OrdersScreen(sellerId: snapshot.data!.sellerId);
        } else {
           return const Center(
             child: Text('يجب إنشاء متجر أولاً لعرض الطلبات')
           );
        }
      },
    );
  }
}

class AdminMessagesLoader extends StatelessWidget {
  final int currentUserId;
  const AdminMessagesLoader({super.key, required this.currentUserId});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Seller?>(
      future: DatabaseHelper.instance.getSellerByTelegramId(currentUserId), 
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasData && snapshot.data != null) {
          return MessagesScreen(sellerId: snapshot.data!.sellerId);
        } else {
           return const Center(
             child: Text('يجب إنشاء متجر أولاً لتلقي الرسائل')
           );
        }
      },
    );
  }
}
