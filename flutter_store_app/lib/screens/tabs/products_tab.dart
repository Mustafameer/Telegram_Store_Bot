

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';
import '../components/product_form_dialog.dart';

// دالة لتنسيق المبالغ مع فاصلة الآلاف وإزالة الكسور
String formatPrice(dynamic price) {
  if (price == null) return '0';
  final numValue = price is num ? price : double.tryParse(price.toString()) ?? 0;
  final rounded = numValue.round();
  final formatter = NumberFormat('#,###', 'ar');
  return formatter.format(rounded);
}

class ProductsTab extends StatefulWidget {
  final int sellerId;
  final bool isEditable;
  final VoidCallback? onCartChanged;
  final int? currentUserId;

  const ProductsTab({
    super.key, 
    required this.sellerId, 
    this.isEditable = false,
    this.onCartChanged,
    this.currentUserId,
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
      final cats = await DatabaseHelper.instance.getCategories(widget.sellerId, forceRefresh: force);
      final prods = await DatabaseHelper.instance.getProducts(widget.sellerId, forceRefresh: force);
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
    final result = await showDialog(
      context: context,
      builder: (context) => ProductFormDialog(sellerId: widget.sellerId, product: product),
    );
    if (result == true) {
      _refreshData();
    }
  }

  Future<void> _deleteProduct(int productId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: const Text('هل أنت متأكد من حذف هذا المنتج؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('حذف', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm == true) {
      await DatabaseHelper.instance.deleteProduct(productId);
      _refreshData();
    }
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
                IconButton(onPressed: () => setSt(() => q > 1 ? q-- : q), icon: const Icon(Icons.remove)),
                Text('$q', style: const TextStyle(fontSize: 20)),
                IconButton(onPressed: () => setSt(() => q < product.quantity ? q++ : q), icon: const Icon(Icons.add)),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
            FilledButton(
              onPressed: () => Navigator.pop(context, q),
              child: const Text('إضافة'),
            ),
          ],
        );
      }
    );

    if (qty != null && qty > 0) {
      await DatabaseHelper.instance.addToCart(currentUserId, product.productId, qty, product.price);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تمت الإضافة للسلة')));
        widget.onCartChanged?.call();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_errorMessage != null) return Center(child: Text('Error: $_errorMessage'));
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
                     ElevatedButton(onPressed: () => _refreshData(force: true), child: const Text('تحديث')),
                     const SizedBox(width: 16),
                     FilledButton.icon(
                        onPressed: () => _showProductForm(),
                        icon: const Icon(Icons.add),
                        label: const Text('إضافة منتج'),
                     ),
                   ],
                 ),
              ]
            ],
          )
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
            padding: EdgeInsets.all(MediaQuery.of(context).size.width < 600 ? 8 : 16),
            sliver: SliverMainAxisGroup(
              slivers: [
                ..._categories.map((cat) {
            final productsInCat = grouped[cat.categoryId] ?? [];
            if (productsInCat.isEmpty) return const SliverToBoxAdapter(child: SizedBox.shrink());

            return SliverMainAxisGroup(
              slivers: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 16.0),
                    child: Row(
                      children: [
                        Container(width: 4, height: 24, color: Theme.of(context).primaryColor),
                        const SizedBox(width: 8),
                        Text(
                          cat.name,
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverGrid(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final product = productsInCat[index];
                      return _buildProductCard(product);
                    },
                    childCount: productsInCat.length,
                  ),
                  gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: MediaQuery.of(context).size.width < 600 
                        ? (MediaQuery.of(context).size.width - 32) / 2  // Mobile: 2 columns مع padding
                        : 250,  // Desktop: fixed size
                    childAspectRatio: MediaQuery.of(context).size.width < 600 ? 0.52 : 0.61, // تقليل الارتفاع 1 سم من الأسفل
                    crossAxisSpacing: MediaQuery.of(context).size.width < 600 ? 12 : 16,
                    mainAxisSpacing: MediaQuery.of(context).size.width < 600 ? 12 : 16,
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
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold, color: Colors.grey[700]),
                    ),
                  ],
                ),
              ),
            ),
            SliverGrid(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final product = uncategorized[index];
                  return _buildProductCard(product);
                },
                childCount: uncategorized.length,
              ),
              gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: MediaQuery.of(context).size.width < 600 
                    ? (MediaQuery.of(context).size.width - 32) / 2  // Mobile: 2 columns مع padding
                    : 250,  // Desktop: fixed size
                childAspectRatio: MediaQuery.of(context).size.width < 600 ? 0.52 : 0.61, // تقليل الارتفاع 1 سم من الأسفل
                crossAxisSpacing: MediaQuery.of(context).size.width < 600 ? 12 : 16,
                mainAxisSpacing: MediaQuery.of(context).size.width < 600 ? 12 : 16,
              ),
            ),
          ]
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
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Image Section - أكبر مساحة وأفضل عرض
          AspectRatio(
            aspectRatio: 1.0, // مربع مثالي للصورة
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(12),
                  topRight: Radius.circular(12),
                ),
              ),
              child: product.imagePath != null && File(product.imagePath!).existsSync()
                  ? ClipRRect(
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(12),
                        topRight: Radius.circular(12),
                      ),
                      child: Image.file(
                        File(product.imagePath!),
                        fit: BoxFit.cover,
                        width: double.infinity,
                        height: double.infinity,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            color: Colors.grey[200],
                            child: const Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.broken_image, size: 40, color: Colors.grey),
                                SizedBox(height: 8),
                                Text('خطأ في الصورة', style: TextStyle(fontSize: 12, color: Colors.grey)),
                              ],
                            ),
                          );
                        },
                      ),
                    )
                  : Container(
                      decoration: BoxDecoration(
                        color: Colors.grey[100],
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(12),
                          topRight: Radius.circular(12),
                        ),
                      ),
                      child: const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.image, size: 50, color: Colors.grey),
                          SizedBox(height: 8),
                          Text('لا توجد صورة', style: TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      ),
                    ),
            ),
          ),
          Flexible(
            child: Padding(
              padding: EdgeInsets.all(MediaQuery.of(context).size.width < 600 ? 10.0 : 12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    product.name,
                    style: TextStyle(
                      fontWeight: FontWeight.bold, 
                      fontSize: MediaQuery.of(context).size.width < 600 ? 13 : 16
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      Text(
                        '${formatPrice(product.price)} د.ع',
                        style: TextStyle(
                          color: Colors.blue, 
                          fontWeight: FontWeight.bold,
                          fontSize: MediaQuery.of(context).size.width < 600 ? 11 : 14
                        ),
                      ),
                      Text(
                        'الكمية: ${product.quantity}',
                        style: TextStyle(
                          fontSize: MediaQuery.of(context).size.width < 600 ? 10 : 12, 
                          color: Colors.grey[600]
                        ),
                      ),
                    ],
                  ),
                  if (widget.isEditable && product.wholesalePrice != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      'جملة: ${formatPrice(product.wholesalePrice)} د.ع',
                      style: TextStyle(
                        fontSize: MediaQuery.of(context).size.width < 600 ? 10 : 12, 
                        color: Colors.green, 
                        fontWeight: FontWeight.bold
                      ),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 1,
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (widget.isEditable)
            Container(
              color: Colors.grey[50],
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  IconButton(
                    icon: const Icon(Icons.edit, size: 20, color: Colors.blue),
                    onPressed: () => _showProductForm(product: product),
                    tooltip: 'تعديل',
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete, size: 20, color: Colors.red),
                    onPressed: () => _deleteProduct(product.productId),
                    tooltip: 'حذف',
                  ),
                ],
              ),
            )
          else
            Padding(
              padding: EdgeInsets.all(MediaQuery.of(context).size.width < 600 ? 4.0 : 8.0),
              child: FilledButton.icon(
                onPressed: () => _addToCart(product),
                icon: Icon(
                  Icons.add_shopping_cart, 
                  size: MediaQuery.of(context).size.width < 600 ? 14 : 16
                ),
                label: Text(
                  'أضف للسلة',
                  style: TextStyle(
                    fontSize: MediaQuery.of(context).size.width < 600 ? 12 : 14
                  ),
                ),
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.symmetric(
                    horizontal: MediaQuery.of(context).size.width < 600 ? 8 : 16,
                    vertical: MediaQuery.of(context).size.width < 600 ? 4 : 8,
                  ),
                ),
              ),
            )
        ],
      ),
    );
  }
}
