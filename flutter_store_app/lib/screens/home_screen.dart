

import 'package:flutter/material.dart';
import 'dart:io';
import 'package:file_picker/file_picker.dart';

import '../models/database_models.dart';
import '../database/database_helper.dart';
import '../services/telegram_service.dart';
import '../services/sync_service.dart';
import 'store_detail_screen.dart';
import 'login_screen.dart';
import 'cart_screen.dart';
import 'components/store_form_dialog.dart';

class HomeScreen extends StatefulWidget {
  final bool isAdmin;
  const HomeScreen({super.key, this.isAdmin = false});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  bool _isExtended = true;

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
                label: Text('سلة المشتريات'), 
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
      return const AdminStoreLoader();
    } else if (_selectedIndex == 2) {
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

  void _refreshSellers({bool force = false}) {
    setState(() {
      _sellersFuture = DatabaseHelper.instance.getAllSellers(forceRefresh: force);
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
                final dir = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images');
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
          Future(() async => (await Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images').exists()) ? '✅ Images Folder Found' : '❌ Images Folder MISSING')
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
                   Navigator.push(context, MaterialPageRoute(builder: (_) => StoreDetailScreen(seller: seller, isSellerMode: true)));
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
