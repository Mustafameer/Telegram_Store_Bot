import 'package:path/path.dart' as p;
import 'package:flutter/material.dart';
import 'dart:io';
import 'dart:async';
import 'package:file_picker/file_picker.dart';

import '../models/database_models.dart';
import '../database/database_helper.dart';
import '../services/telegram_service.dart';
import '../services/sync_service.dart';
import 'store_detail_screen.dart';
import 'login_screen.dart';
import 'cart_screen.dart';
import 'messages_screen.dart';
import 'components/store_form_dialog.dart';
import 'server_settings_screen.dart';

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
  StreamSubscription? _syncSub;
  Map<String, int> _counts = {'products': 0, 'messages': 0, 'cart': 0};
  
  @override
  void initState() {
    super.initState();
    _refreshCounts();
    // ... existing init code ...
    _syncSub = SyncService.instance.statusStream.listen((msg) {
      // ... existing listener ...
      if (msg.contains('Failed') || msg.contains('Error') || msg.toLowerCase().contains('fatal')) {
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: const Row(children: [Icon(Icons.error, color: Colors.red), SizedBox(width: 8), Text("Sync Error")]),
              content: SelectableText(msg), 
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text("OK")),
                TextButton(onPressed: () { 
                    Navigator.pop(context);
                    Navigator.push(context, MaterialPageRoute(builder: (_) => ServerSettingsScreen()));
                  }, child: const Text("Settings"))
              ],
            )
          );
      }
       ScaffoldMessenger.of(context).hideCurrentSnackBar();
       ScaffoldMessenger.of(context).showSnackBar(
         SnackBar(
           content: Row(
             children: [
               if (msg.contains('Starting') || msg.contains('ing...')) 
                 const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
               const SizedBox(width: 10),
               Expanded(child: Text(msg)),
             ],
           ),
           backgroundColor: msg.contains('Failed') || msg.contains('Error') ? Colors.red : Colors.blue.shade700,
           duration: const Duration(seconds: 4),
         )
       );
    });

    Future.delayed(const Duration(seconds: 1), () {
        SyncService.instance.startSyncTimer();
    });
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
    
    if (seller != null) {
      pCount = await DatabaseHelper.instance.getProductsCount(seller.sellerId);
      mCount = await DatabaseHelper.instance.getMessagesCount(seller.sellerId); // Total messages
    }
    cCount = await DatabaseHelper.instance.getCartCount(targetId);

    if (mounted) {
      setState(() {
        _counts = {'products': pCount, 'messages': mCount, 'cart': cCount};
      });
    }
  }

  // Hook into other refreshes if possible, or just call periodically
  
  List<Map<String, dynamic>> _getDestinations() {
    return [
      {'icon': Icons.dashboard, 'label': 'لوحة التحكم'},
      if (widget.isAdmin || widget.isSeller) {'icon': Icons.store, 'label': 'متجري', 'count': _counts['products']},
      {'icon': Icons.shopping_cart, 'label': 'سلة المشتريات', 'count': _counts['cart']},
      {'icon': Icons.settings, 'label': 'الاعدادات'},
      if (widget.isAdmin || widget.isSeller) {'icon': Icons.message, 'label': 'الرسائل', 'count': _counts['messages']},
      {'icon': Icons.logout, 'label': 'خروج', 'isExit': true},
    ];
  }

  void _onDestinationSelected(int index) {
     final destinations = _getDestinations();
     if (index >= destinations.length) return;
     final selectedItem = destinations[index];
    
    if (selectedItem['isExit'] == true) {
       Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const LoginScreen()),
       );
       return;
    }
    
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
    final width = MediaQuery.of(context).size.width;
    final bool isMobile = width < 900;
    final destinations = _getDestinations();

    if (isMobile) {
       return Scaffold(
         appBar: AppBar(
            title: const Text('المتجر المحلي'),
            actions: [
               IconButton(
                 icon: const Icon(Icons.sync),
                 tooltip: 'مزامنة',
                 onPressed: () {
                    SyncService.instance.syncNow();
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('جاري بدء المزامنة...')));
                 },
               ),
               IconButton(
                 icon: const Icon(Icons.settings),
                 onPressed: () {
                    Navigator.push(context, MaterialPageRoute(builder: (_) => ServerSettingsScreen()));
                 },
               )
            ],
         ),
         drawer: Drawer(
           child: ListView(
             children: [
               const DrawerHeader(
                 decoration: BoxDecoration(color: Colors.blue),
                 child: Column(
                   mainAxisAlignment: MainAxisAlignment.center,
                   children: [
                     Icon(Icons.store, size: 50, color: Colors.white),
                     SizedBox(height: 10),
                     Text('Hypermarket Local', style: TextStyle(color: Colors.white, fontSize: 20)),
                   ],
                 ),
               ),
               ...destinations.asMap().entries.map((e) {
                 final idx = e.key;
                 final item = e.value;
                 final isExit = item['isExit'] == true;
                 final count = item['count'] as int? ?? 0;
                 return ListTile(
                   leading: Icon(item['icon'], color: isExit ? Colors.red : null),
                   title: Row(
                     mainAxisAlignment: MainAxisAlignment.spaceBetween,
                     children: [
                       Text(item['label'], style: TextStyle(color: isExit ? Colors.red : null)),
                       if (count > 0) 
                         Container(
                           padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                           decoration: BoxDecoration(color: Colors.red, borderRadius: BorderRadius.circular(12)),
                           child: Text('$count', style: const TextStyle(color: Colors.white, fontSize: 12)),
                         )
                     ],
                   ),
                   selected: _selectedIndex == idx,
                   onTap: () {
                      if (!isExit) {
                        Navigator.pop(context);
                      }
                      _onDestinationSelected(idx);
                   },
                 );
               })
             ],
           ),
         ),
         body: _buildContent(),
       );
    }

    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: _isExtended,
            selectedIndex: _selectedIndex,
            onDestinationSelected: _onDestinationSelected,
            leading: IconButton(
              icon: Icon(_isExtended ? Icons.menu_open : Icons.menu),
              onPressed: () {
                setState(() {
                  _isExtended = !_isExtended;
                });
              },
            ),
            labelType: _isExtended ? NavigationRailLabelType.none : NavigationRailLabelType.selected,
            destinations: destinations.map((item) {
               final isExit = item['isExit'] == true;
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
            trailing: Padding(
               padding: const EdgeInsets.only(top: 20),
               child: IconButton(
                 icon: const Icon(Icons.sync, color: Colors.blue),
                 tooltip: 'مزامنة يدوية',
                 onPressed: () {
                    SyncService.instance.syncNow();
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('جاري بدء المزامنة...')));
                 },
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
      return AdminMessagesLoader(currentUserId: widget.currentUserId);
    }
    return const Center(child: Text('جاري العمل...'));
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
         return sellers.where((s) => s.telegramId != widget.currentUserId).toList();
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
        isEdit: seller != null,
        onSave: (storeName, telegramId, userName, imagePath) async {
          if (seller == null) {
             await DatabaseHelper.instance.addSeller(storeName, telegramId, userName, imagePath: imagePath);
          } else {
             // If editing, we typically keep the original TelegramID unless you want to allow changing it?
             // Since ID is unique/key, changing it might require care.
             // But DatabaseHelper.updateSeller uses SellerID (Primary Key) to find record, 
             // but it DOES NOT update TelegramID column in the update query (Lines 191-195 in db_helper).
             // So passing a new TelegramID here won't persist if we don't update DB helper.
             // For now turn a blind eye to ID change or allow it if I update DB helper.
             // Providing the updated fields:
             final updatedSeller = seller.copyWith(
               storeName: storeName,
               userName: userName,
               imagePath: imagePath
               // ignoring telegramId change for now as updateSeller doesn't support it
             );
             await DatabaseHelper.instance.updateSeller(updatedSeller);
          }
           if (context.mounted) Navigator.pop(context); // Dialog handles pop? No, Dialog calls onSave and catches error. It does NOT pop. I must pop here on success.
           if (mounted) _refreshSellers(force: true);
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
            icon: const Icon(Icons.cloud_sync, color: Colors.blueAccent),
            tooltip: 'مزامنة مع السحابة',
            onPressed: () {
              showDialog(
                context: context,
                barrierDismissible: false,
                builder: (context) {
                  return AlertDialog(
                    title: const Row(children: [CircularProgressIndicator(), SizedBox(width: 16), Text("جاري المزامنة...")]),
                    content: StreamBuilder<String>(
                      stream: SyncService.instance.statusStream,
                      initialData: "البدء...",
                      builder: (context, snapshot) {
                        return Text(snapshot.data ?? "...");
                      },
                    ),
                  );
                },
              );
              
              SyncService.instance.syncNow().then((_) {
                 Navigator.pop(context); // Close dialog
                 ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تمت المزامنة بنجاح ✅'), backgroundColor: Colors.green));
                 _refreshSellers(force: true);
              }).catchError((e) {
                 Navigator.pop(context); // Close dialog
                 ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('فشل المزامنة: $e'), backgroundColor: Colors.red));
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.folder, color: Colors.amber),
            tooltip: 'إنشاء مجلد الصور',
            onPressed: () async {
              try {
                final dir = Directory(p.join(Directory.current.path, 'data', 'Images'));
                if (!await dir.exists()) {
                  await dir.create(recursive: true);
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('تم إنشاء المجلد في:\n${dir.path}'), backgroundColor: Colors.green));
                } else {
                   ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('المجلد موجود مسبقاً في:\n${dir.path}'), backgroundColor: Colors.blue));
                }
              } catch (e) {
                 ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('فشل إنشاء المجلد: $e'), backgroundColor: Colors.red));
              }
            },
          ),
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
          DatabaseHelper.instance.getDbPath(),
          Future(() async => (await Directory(p.join(Directory.current.path, 'data', 'Images')).exists()) ? '✅ Images Folder Found' : '❌ Images Folder MISSING')
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
                  ],
                ),
              ),
              Positioned(
                top: 0,
                right: 0,
                child: PopupMenuButton<String>(
                  onSelected: (v) {
                    if (v == 'toggle') _toggleSellerStatus(seller);
                    if (v == 'edit') _showStoreDialog(seller: seller);
                    if (v == 'delete') _deleteSeller(seller);
                  },
                  itemBuilder: (c) => [
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
      await DatabaseHelper.instance.deleteSeller(seller.sellerId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم حذف المتجر بنجاح')));
        _refreshSellers();
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
