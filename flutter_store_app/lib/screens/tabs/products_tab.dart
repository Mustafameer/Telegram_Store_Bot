import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';
import '../components/product_form_dialog.dart';
import '../manage_product_images_screen.dart';

// دالة لتنسيق المبالغ مع فاصلة الآلاف وإزالة الكسور
String formatPrice(dynamic price) {
  if (price == null) return '0';
  final numValue = price is num
      ? price
      : double.tryParse(price.toString()) ?? 0;
  final rounded = numValue.round();
  final formatter = NumberFormat('#,###', 'ar');
  return formatter.format(rounded);
}

class ProductsTab extends StatefulWidget {
  final int sellerId;
  final bool isEditable;
  final VoidCallback? onCartChanged;
  final int? currentUserId;
  final bool requireCustomerRegistration; // إضافة هذا الحقل

  const ProductsTab({
    super.key,
    required this.sellerId,
    this.isEditable = false,
    this.onCartChanged,
    this.currentUserId,
    this.requireCustomerRegistration = false, // القيمة الافتراضية
  });

  @override
  State<ProductsTab> createState() => _ProductsTabState();
}

class _ProductsTabState extends State<ProductsTab> {
  bool _isLoading = true;
  List<Category> _categories = [];
  List<Product> _products = [];
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _refreshData();
  }

  Future<void> _refreshData({bool force = false}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final cats = await DatabaseHelper.instance.getCategories(
        widget.sellerId,
        forceRefresh: force,
      );
      final prods = await DatabaseHelper.instance.getProducts(
        widget.sellerId,
        forceRefresh: force,
      );
      if (mounted) {
        setState(() {
          _categories = cats;
          _products = prods;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _showProductForm({Product? product}) async {
    // ⚠️ السماح فقط إذا كان المتجر قابلاً للتعديل
    if (!widget.isEditable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🔒 هذا المتجر محجوز - لا يمكن تعديل المنتجات'),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }

    // الحصول على معلومات المتجر
    final seller = await DatabaseHelper.instance.getSellerById(widget.sellerId);
    final requireCustomerRegistration =
        seller?.requireCustomerRegistration ?? false;

    final result = await showDialog(
      context: context,
      builder: (context) => ProductFormDialog(
        sellerId: widget.sellerId,
        product: product,
        requireCustomerRegistration: requireCustomerRegistration,
      ),
    );
    if (result == true) {
      _refreshData();
    }
  }

  Future<void> _deleteProduct(int productId) async {
    // ⚠️ السماح فقط إذا كان المتجر قابلاً للتعديل
    if (!widget.isEditable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🔒 هذا المتجر محجوز - لا يمكن حذف المنتجات'),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }

    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: const Text('هل أنت متأكد من حذف هذا المنتج؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('حذف', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await DatabaseHelper.instance.deleteProduct(productId);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم حذف المنتج بنجاح')),
          );
        }
        _refreshData();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('خطأ في الحذف: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  Future<void> _manageProductImages(Product product) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ManageProductImagesScreen(product: product),
      ),
    );
    // تحديث البيانات بعد العودة من شاشة إدارة الصور مع إعادة التحميل من قاعدة البيانات
    _refreshData(force: true);
  }

  Future<void> _addToCart(Product product) async {
    // Start with Passed ID, fallback to Admin ID if null (safety net)
    final currentUserId = widget.currentUserId ?? 1041977029;

    final qty = await showDialog<int>(
      context: context,
      builder: (context) {
        int q = 1;
        return AlertDialog(
          title: const Text('إضافة للسلة'),
          content: StatefulBuilder(
            builder: (context, setSt) => Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  onPressed: () => setSt(() => q > 1 ? q-- : q),
                  icon: const Icon(Icons.remove),
                ),
                Text('$q', style: const TextStyle(fontSize: 20)),
                IconButton(
                  onPressed: () => setSt(() => q < product.quantity ? q++ : q),
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('إلغاء'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, q),
              child: const Text('إضافة'),
            ),
          ],
        );
      },
    );

    if (qty != null && qty > 0) {
      await DatabaseHelper.instance.addToCart(
        currentUserId,
        product.productId,
        qty,
        product.price,
      );
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('تمت الإضافة للسلة')));
        widget.onCartChanged?.call();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_errorMessage != null)
      return Center(child: Text('Error: $_errorMessage'));
    if (_products.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('لا يوجد منتجات'),
            if (widget.isEditable) ...[
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    onPressed: () => _refreshData(force: true),
                    child: const Text('تحديث'),
                  ),
                  const SizedBox(width: 16),
                  FilledButton.icon(
                    onPressed: () => _showProductForm(),
                    icon: const Icon(Icons.add),
                    label: const Text('إضافة منتج'),
                  ),
                ],
              ),
            ],
          ],
        ),
      );
    }

    // Group Products
    final Map<int, List<Product>> grouped = {};
    final List<Product> uncategorized = [];

    for (var p in _products) {
      if (p.categoryId != null) {
        if (!grouped.containsKey(p.categoryId)) grouped[p.categoryId!] = [];
        grouped[p.categoryId!]!.add(p);
      } else {
        uncategorized.add(p);
      }
    }

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () => _refreshData(force: true),
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: EdgeInsets.all(
                MediaQuery.of(context).size.width < 600 ? 8 : 16,
              ),
              sliver: SliverMainAxisGroup(
                slivers: [
                  ..._categories.map((cat) {
                    final productsInCat = grouped[cat.categoryId] ?? [];
                    if (productsInCat.isEmpty)
                      return const SliverToBoxAdapter(child: SizedBox.shrink());

                    return SliverMainAxisGroup(
                      slivers: [
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 16.0),
                            child: Row(
                              children: [
                                Container(
                                  width: 4,
                                  height: 24,
                                  color: Theme.of(context).primaryColor,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  cat.name,
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineSmall
                                      ?.copyWith(fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          ),
                        ),
                        SliverGrid(
                          delegate: SliverChildBuilderDelegate((
                            context,
                            index,
                          ) {
                            final product = productsInCat[index];
                            return _buildProductCard(product);
                          }, childCount: productsInCat.length),
                          gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent:
                                MediaQuery.of(context).size.width < 600
                                ? (MediaQuery.of(context).size.width - 32) /
                                      2 // Mobile: 2 columns مع padding
                                : 250, // Desktop: fixed size
                            childAspectRatio: () {
                              // للمشترين في المتاجر المقفولة: استخدام نسبة مربع (1.0) لبطاقة 4.97 × 4.97
                              // لصاحب المتجر أو المتاجر المفتوحة: استخدام الأبعاد الأصلية
                              final isRestrictedForBuyer =
                                  !widget.isEditable &&
                                  widget.requireCustomerRegistration;

                              if (isRestrictedForBuyer) {
                                // للمتاجر المقفولة: نسبة مربع تماماً (1.0)
                                return 1.0;
                              } else {
                                // الأبعاد للمتاجر المفتوحة أو لصاحب المتجر (زيادة النسبة لتجنب overflow)
                                return MediaQuery.of(context).size.width < 600
                                    ? 0.58
                                    : 0.62;
                              }
                            }(),
                            crossAxisSpacing:
                                MediaQuery.of(context).size.width < 600
                                ? 12
                                : 16,
                            mainAxisSpacing:
                                MediaQuery.of(context).size.width < 600
                                ? 12
                                : 16,
                          ),
                        ),
                      ],
                    );
                  }),
                  if (uncategorized.isNotEmpty) ...[
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 16.0),
                        child: Row(
                          children: [
                            Container(width: 4, height: 24, color: Colors.grey),
                            const SizedBox(width: 8),
                            Text(
                              'غير مصنف',
                              style: Theme.of(context).textTheme.headlineSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.grey[700],
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    SliverGrid(
                      delegate: SliverChildBuilderDelegate((context, index) {
                        final product = uncategorized[index];
                        return _buildProductCard(product);
                      }, childCount: uncategorized.length),
                      gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent:
                            MediaQuery.of(context).size.width < 600
                            ? (MediaQuery.of(context).size.width - 32) /
                                  2 // Mobile: 2 columns مع padding
                            : 378, // Desktop: 10 سم = 378 بكسل
                        childAspectRatio: 1.0, // مربع: 10 × 10 سم
                        crossAxisSpacing:
                            MediaQuery.of(context).size.width < 600 ? 12 : 16,
                        mainAxisSpacing: MediaQuery.of(context).size.width < 600
                            ? 12
                            : 16,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: widget.isEditable
          ? FloatingActionButton(
              onPressed: () => _showProductForm(),
              child: const Icon(Icons.add),
            )
          : null,
    );
  }

  Widget _buildProductCard(Product product) {
    // للمتاجر المقفولة: عرض بدون صور مع زر خاص لاختيار الصور
    final bool isRestrictedStore = widget.requireCustomerRegistration && !widget.isEditable;

    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        mainAxisSize: MainAxisSize.min,
        children: [
          // محتوى البطاقة بدون صور
          Padding(
            padding: EdgeInsets.all(
              MediaQuery.of(context).size.width < 600 ? 3.0 : 4.0,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // اسم المنتج
                Text(
                  product.name,
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    color: const Color(0xFF0D47A1), // أزرق غامق جداً
                    fontSize: MediaQuery.of(context).size.width < 600
                        ? 14
                        : 16,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),
                // السعر والكمية
                Wrap(
                  spacing: 4,
                  runSpacing: 2,
                  children: [
                    Text(
                      '${formatPrice(product.price)} د.ع',
                      style: TextStyle(
                        color: Colors.blue,
                        fontWeight: FontWeight.bold,
                        fontSize: MediaQuery.of(context).size.width < 600
                            ? 11
                            : 13,
                      ),
                    ),
                    Text(
                      'الكمية: ${product.quantity}',
                      style: TextStyle(
                        fontSize: MediaQuery.of(context).size.width < 600
                            ? 12
                            : 13,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
                // سعر الجملة (إذا كان في وضع التعديل)
                if (widget.isEditable && product.wholesalePrice != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'جملة: ${formatPrice(product.wholesalePrice)} د.ع',
                    style: TextStyle(
                      fontSize: MediaQuery.of(context).size.width < 600
                          ? 9
                          : 10,
                      color: Colors.green,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ],
              ],
            ),
          ),
          // أزرار الكمية للمتاجر المقفولة (بدون صور)
          if (!widget.isEditable && isRestrictedStore)
            StatefulBuilder(
              builder: (context, setState) {
                int selectedQuantity = 1;
                return Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: MediaQuery.of(context).size.width < 600
                        ? 4.0
                        : 6.0,
                    vertical: 2,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // أزرار الكمية
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          IconButton(
                            onPressed: () {
                              if (selectedQuantity > 1) {
                                setState(() {
                                  selectedQuantity--;
                                });
                              }
                            },
                            icon: const Icon(
                              Icons.remove_circle_outline,
                            ),
                            color: Colors.red,
                            iconSize:
                                MediaQuery.of(context).size.width < 600
                                    ? 20
                                    : 24,
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.grey[50],
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: Colors.grey[300]!,
                              ),
                            ),
                            child: Text(
                              '$selectedQuantity',
                              style: TextStyle(
                                fontSize:
                                    MediaQuery.of(context).size.width < 600
                                        ? 12
                                        : 14,
                              ),
                            ),
                          ),
                          IconButton(
                            onPressed: () {
                              if (selectedQuantity < product.quantity) {
                                setState(() {
                                  selectedQuantity++;
                                });
                              }
                            },
                            icon: const Icon(
                              Icons.add_circle_outline,
                            ),
                            color: Colors.green,
                            iconSize:
                                MediaQuery.of(context).size.width < 600
                                    ? 20
                                    : 24,
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      FilledButton(
                        onPressed: () {
                          _addToCart(product);
                        },
                        style: FilledButton.styleFrom(
                          visualDensity: VisualDensity.compact,
                          padding: EdgeInsets.symmetric(
                            horizontal:
                                MediaQuery.of(context).size.width < 600
                                    ? 16
                                    : 20,
                            vertical: 8,
                          ),
                        ),
                        child: Text(
                          'أضف للسلة',
                          style: TextStyle(
                            fontSize:
                                MediaQuery.of(context).size.width < 600
                                    ? 11
                                    : 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          // أزرار التعديل والحذف للمتاجر المفتوحة (نفس تصميم المشتري)
          if (widget.isEditable)
            Padding(
              padding: EdgeInsets.symmetric(
                horizontal: MediaQuery.of(context).size.width < 600
                    ? 4.0
                    : 6.0,
                vertical: 2,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.edit,
                      size: 20,
                      color: Colors.blue,
                    ),
                    onPressed: () => _showProductForm(product: product),
                    tooltip: 'تعديل',
                    iconSize: 20,
                  ),
                  // زر إدارة الصور
                  if (widget.requireCustomerRegistration)
                    IconButton(
                      icon: const Icon(
                        Icons.photo_library,
                        size: 20,
                        color: Colors.green,
                      ),
                      onPressed: () => _manageProductImages(product),
                      tooltip: 'إدارة الصور',
                      iconSize: 20,
                    ),
                  IconButton(
                    icon: const Icon(
                      Icons.delete,
                      size: 20,
                      color: Colors.red,
                    ),
                    onPressed: () => _deleteProduct(product.productId),
                    tooltip: 'حذف',
                    iconSize: 20,
                  ),
                ],
              ),
            )
        ],
      ),
    );
  }

}
