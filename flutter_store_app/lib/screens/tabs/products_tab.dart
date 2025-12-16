

import 'dart:io';
import 'package:flutter/material.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';
import '../components/product_form_dialog.dart';

class ProductsTab extends StatefulWidget {
  final int sellerId;
  final bool isEditable;

  const ProductsTab({
    super.key, 
    required this.sellerId, 
    this.isEditable = false,
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
    // Admin ID as default user for now
    const currentUserId = 1041977029; 

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
            padding: const EdgeInsets.all(16),
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
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 250,
                    childAspectRatio: 0.75,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
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
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 250,
                childAspectRatio: 0.75,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: product.imagePath != null && File(product.imagePath!).existsSync()
                ? Image.file(File(product.imagePath!), fit: BoxFit.cover)
                : Container(
                    color: Colors.grey[100],
                    child: Icon(Icons.image, size: 50, color: Colors.grey[400]),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  product.name,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${product.price} د.ع',
                      style: TextStyle(color: Theme.of(context).primaryColor, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'الكمية: ${product.quantity}',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  ],
                ),
                if (widget.isEditable && product.wholesalePrice != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'جملة: ${product.wholesalePrice} د.ع',
                    style: const TextStyle(fontSize: 12, color: Colors.green, fontWeight: FontWeight.bold),
                  ),
                ],
              ],
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
              padding: const EdgeInsets.all(8.0),
              child: FilledButton.icon(
                onPressed: () => _addToCart(product),
                icon: const Icon(Icons.add_shopping_cart, size: 16),
                label: const Text('أضف للسلة'),
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                ),
              ),
            )
        ],
      ),
    );
  }
}
