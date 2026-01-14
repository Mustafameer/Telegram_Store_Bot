/// example_home_screen_v2.dart
/// 
/// مثال على كيفية تحديث شاشات التطبيق للعمل مع Direct Cloud
///

import 'package:flutter/material.dart';
import '../services/sync_service_v2.dart';
import '../models/database_models.dart';

/// ============= صفحة المتجر (متجر بيعي) =============
class SellerStoreScreen extends StatefulWidget {
  const SellerStoreScreen({Key? key}) : super(key: key);

  @override
  State<SellerStoreScreen> createState() => _SellerStoreScreenState();
}

class _SellerStoreScreenState extends State<SellerStoreScreen> {
  final SyncServiceV2 _syncService = SyncServiceV2.instance;
  
  final _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('متجري'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showAddProductDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // ❌ قديم: حقل بحث محلي فقط
          // ✅ جديد: بحث سحابي مباشر
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'ابحث عن منتج...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              onChanged: (value) {
                setState(() => _searchQuery = value);
              },
            ),
          ),
          Expanded(
            child: FutureBuilder<List<ProductModel>>(
              // ✅ جديد: جلب مباشرة من السحابة كل مرة يتغير البحث
              future: _searchQuery.isEmpty
                  ? _syncService.getMyProducts()
                  : _syncService.getMyProducts(search: _searchQuery),
              builder: (context, snapshot) {
                // حالة التحميل
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: CircularProgressIndicator(),
                  );
                }

                // حالة الخطأ
                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.red),
                        const SizedBox(height: 16),
                        Text('خطأ: ${snapshot.error}'),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () => setState(() {}),
                          child: const Text('إعادة محاولة'),
                        ),
                      ],
                    ),
                  );
                }

                final products = snapshot.data ?? [];

                // قائمة فارغة
                if (products.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.shopping_bag_outlined, size: 48, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('لا توجد منتجات بعد'),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: _showAddProductDialog,
                          icon: const Icon(Icons.add),
                          label: const Text('أضف منتج'),
                        ),
                      ],
                    ),
                  );
                }

                // عرض المنتجات
                return ListView.builder(
                  itemCount: products.length,
                  itemBuilder: (context, index) {
                    final product = products[index];
                    return ProductCard(
                      product: product,
                      onEdit: () => _showEditProductDialog(product),
                      onDelete: () => _deleteProduct(product.productId),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ❌ قديم: الحفظ المحلي أولاً
  // ✅ جديد: الحفظ السحابي مباشرة
  void _showAddProductDialog() {
    final nameController = TextEditingController();
    final descController = TextEditingController();
    final priceController = TextEditingController();
    final categoryController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('منتج جديد'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'اسم المنتج'),
              ),
              TextField(
                controller: descController,
                decoration: const InputDecoration(labelText: 'الوصف'),
                maxLines: 3,
              ),
              TextField(
                controller: priceController,
                decoration: const InputDecoration(labelText: 'السعر'),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: categoryController,
                decoration: const InputDecoration(labelText: 'الفئة'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                // ✅ جديد: حفظ مباشر في السحابة
                await _syncService.addProduct(
                  name: nameController.text,
                  description: descController.text,
                  price: double.parse(priceController.text),
                  category: categoryController.text,
                );

                if (mounted) {
                  Navigator.pop(context);
                  setState(() {}); // لتحديث القائمة
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('✅ تمت إضافة المنتج بنجاح')),
                  );
                }
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('❌ خطأ: $e')),
                );
              }
            },
            child: const Text('إضافة'),
          ),
        ],
      ),
    );
  }

  void _showEditProductDialog(ProductModel product) {
    final nameController = TextEditingController(text: product.name);
    final descController = TextEditingController(text: product.description);
    final priceController = TextEditingController(text: product.price.toString());
    final categoryController = TextEditingController(text: product.category ?? '');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تعديل المنتج'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'اسم المنتج'),
              ),
              TextField(
                controller: descController,
                decoration: const InputDecoration(labelText: 'الوصف'),
                maxLines: 3,
              ),
              TextField(
                controller: priceController,
                decoration: const InputDecoration(labelText: 'السعر'),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: categoryController,
                decoration: const InputDecoration(labelText: 'الفئة'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                // ✅ جديد: تحديث مباشر في السحابة
                await _syncService.updateProduct(
                  productId: product.productId,
                  name: nameController.text,
                  description: descController.text,
                  price: double.parse(priceController.text),
                  category: categoryController.text,
                );

                if (mounted) {
                  Navigator.pop(context);
                  setState(() {});
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('✅ تم تحديث المنتج بنجاح')),
                  );
                }
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('❌ خطأ: $e')),
                );
              }
            },
            child: const Text('حفظ'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteProduct(int productId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: const Text('هل تريد حقاً حذف هذا المنتج؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _syncService.deleteProduct(productId);
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ تم حذف المنتج بنجاح')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('❌ خطأ: $e')),
        );
      }
    }
  }
}

/// ============= بطاقة المنتج =============
class ProductCard extends StatelessWidget {
  final ProductModel product;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const ProductCard({
    Key? key,
    required this.product,
    required this.onEdit,
    required this.onDelete,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(8),
      child: ListTile(
        // ✅ جديد: عرض الصورة - بدعم BYTEA والمسارات المحلية
        leading: _buildProductImage(),
        title: Text(
          product.name,
          style: TextStyle(
            color: Colors.blue[900], // أزرق غامق
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(product.category ?? 'بدون فئة'),
            Text('${product.price} ريال', style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        trailing: PopupMenuButton(
          itemBuilder: (context) => [
            PopupMenuItem(
              child: const Text('تعديل'),
              onTap: onEdit,
            ),
            PopupMenuItem(
              child: const Text('حذف', style: TextStyle(color: Colors.red)),
              onTap: onDelete,
            ),
          ],
        ),
      ),
    );
  }

  /// دالة مساعدة لبناء عنصر الصورة
  /// تدعم: BYTEA من قاعدة البيانات + صور محلية + صور افتراضية
  Widget _buildProductImage() {
    // 1. إذا كانت الصورة BYTEA (بيانات ثنائية)
    if (product.imageData != null && product.imageData!.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: Image.memory(
          product.imageData!,
          width: 60,
          height: 60,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            return _placeholderImage();
          },
        ),
      );
    }

    // 2. إذا كانت هناك مسار صورة (لكن قد لا يكون URL صحيح)
    if (product.imagePath != null && product.imagePath!.isNotEmpty) {
      final imagePath = product.imagePath!;
      
      // تحقق إذا كان URL صحيح (يبدأ بـ http)
      if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        return ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: Image.network(
            imagePath,
            width: 60,
            height: 60,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return _placeholderImage();
            },
          ),
        );
      }
      
      // إذا كان مسار محلي (مثل /app/data/Images/...)
      // لا يمكن عرضه مباشرة - استخدم صورة افتراضية
      return _placeholderImage();
    }

    // 3. صورة افتراضية إذا لم تكن هناك صورة
    return _placeholderImage();
  }

  /// صورة افتراضية
  Widget _placeholderImage() {
    return Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        borderRadius: BorderRadius.circular(4),
      ),
      child: const Icon(Icons.image, color: Colors.grey),
    );
  }
}

/// ============= صفحة الطلبات (كمشتري) =============
class OrdersScreen extends StatefulWidget {
  const OrdersScreen({Key? key}) : super(key: key);

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  final SyncServiceV2 _syncService = SyncServiceV2.instance;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('طلباتي'),
      ),
      body: FutureBuilder<List<OrderModel>>(
        // ✅ جديد: الحصول على الطلبات من السحابة
        future: _syncService.getMyOrders(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(child: Text('خطأ: ${snapshot.error}'));
          }

          final orders = snapshot.data ?? [];

          if (orders.isEmpty) {
            return const Center(
              child: Text('لا توجد طلبات بعد'),
            );
          }

          return ListView.builder(
            itemCount: orders.length,
            itemBuilder: (context, index) {
              final order = orders[index];
              return Card(
                margin: const EdgeInsets.all(8),
                child: ListTile(
                  title: Text('الطلب #${order.orderId}'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('الحالة: ${order.status}'),
                      Text('السعر: ${order.totalPrice} ريال'),
                      Text('التاريخ: ${order.createdAt.toString().split(' ')[0]}'),
                    ],
                  ),
                  onTap: () => _showOrderDetails(order),
                ),
              );
            },
          );
        },
      ),
    );
  }

  void _showOrderDetails(OrderModel order) async {
    try {
      final orderDetails = await _syncService.getOrderDetails(order.orderId);
      
      if (mounted && orderDetails != null) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('تفاصيل الطلب #${order.orderId}'),
            content: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('الحالة: ${order.status}'),
                  Text('السعر الإجمالي: ${orderDetails.totalPrice} ريال'),
                  const Divider(),
                  const Text('العناصر:', style: TextStyle(fontWeight: FontWeight.bold)),
                  ...orderDetails.items.map((item) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text('- منتج #${item.productId}: ${item.quantity} x ${item.price} ريال'),
                  )),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('إغلاق'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ خطأ: $e')),
      );
    }
  }
}

/// ============= نموذج Providers (اختياري) =============
///
/// إذا كنت تستخدم Provider أو GetX، يمكنك إنشاء Provider مثل:
///
/// class ProductProvider extends ChangeNotifier {
///   final SyncServiceV2 _syncService = SyncServiceV2.instance;
///   List<Product> _products = [];
///   bool _isLoading = false;
///   String? _error;
///
///   List<Product> get products => _products;
///   bool get isLoading => _isLoading;
///   String? get error => _error;
///
///   Future<void> loadMyProducts(String? search) async {
///     _isLoading = true;
///     _error = null;
///     notifyListeners();
///
///     try {
///       _products = search == null
///           ? await _syncService.getMyProducts()
///           : await _syncService.getMyProducts(search: search);
///     } catch (e) {
///       _error = e.toString();
///     } finally {
///       _isLoading = false;
///       notifyListeners();
///     }
///   }
///
///   Future<void> addProduct(Product product) async {
///     try {
///       final newProduct = await _syncService.addProduct(
///         name: product.name,
///         description: product.description,
///         price: product.price,
///         category: product.category,
///         imageUrl: product.imagePath,
///       );
///       _products.add(newProduct);
///       notifyListeners();
///     } catch (e) {
///       _error = e.toString();
///       notifyListeners();
///     }
///   }
/// }
///
/// // الاستخدام في الـ UI:
/// // Consumer<ProductProvider>(
/// //   builder: (context, provider, _) {
/// //     if (provider.isLoading) return CircularProgressIndicator();
/// //     return ListView(children: ...);
/// //   },
/// // )
