
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../models/database_models.dart';
import '../../database/database_helper.dart';

class ProductFormDialog extends StatefulWidget {
  final int sellerId;
  final Product? product;
  final bool requireCustomerRegistration;

  const ProductFormDialog({
    super.key, 
    required this.sellerId, 
    this.product,
    this.requireCustomerRegistration = false,
  });

  @override
  State<ProductFormDialog> createState() => _ProductFormDialogState();
}

class _ProductFormDialogState extends State<ProductFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _descController;
  late TextEditingController _priceController;
  late TextEditingController _wholesalePriceController;
  late TextEditingController _qtyController;
  String? _imagePath;
  int? _selectedCategoryId;

  List<Category> _categories = [];

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.product?.name ?? '');
    _descController = TextEditingController(text: widget.product?.description ?? '');
    // عرض المبالغ كاملة بدون كسور
    _priceController = TextEditingController(
      text: widget.product?.price != null 
          ? widget.product!.price.round().toString() 
          : ''
    );
    _wholesalePriceController = TextEditingController(
      text: widget.product?.wholesalePrice != null 
          ? widget.product!.wholesalePrice!.round().toString() 
          : ''
    );
    _qtyController = TextEditingController(text: widget.product?.quantity.toString() ?? '1');
    _imagePath = widget.product?.imagePath;
    _selectedCategoryId = widget.product?.categoryId;
    
    _loadCategories();
  }

  Future<void> _loadCategories() async {
    final cats = await DatabaseHelper.instance.getCategories(widget.sellerId);
    setState(() {
      _categories = cats;
      // If selected category is not in list (deleted?), reset or keep
      if (_selectedCategoryId != null && !cats.any((c) => c.categoryId == _selectedCategoryId)) {
        _selectedCategoryId = null;
      }
    });
  }

  Future<void> _pickImage() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image);
    if (result != null) {
      setState(() {
        _imagePath = result.files.single.path;
      });
    }
  }

  Future<void> _save() async {
    if (_formKey.currentState!.validate()) {
      try {
        // تحديد الكمية
        int quantity;
        if (widget.requireCustomerRegistration) {
          // للمتاجر المغلقة: الكمية = عدد الصور في ProductImages
          if (widget.product != null) {
            // عند التعديل: حساب الكمية من الصور الموجودة
            final images = await DatabaseHelper.instance.getProductImages(widget.product!.productId);
            quantity = images.length;
          } else {
            // عند الإضافة: الكمية = 1 افتراضياً (ستتم تحديثها بعد إضافة الصور)
            quantity = 1;
          }
        } else {
          // للمتاجر المفتوحة: الكمية يدوية
          quantity = int.tryParse(_qtyController.text) ?? 1;
        }
        
        final product = Product(
          productId: widget.product?.productId ?? 0, 
          sellerId: widget.sellerId,
          categoryId: _selectedCategoryId,
          name: _nameController.text,
          description: _descController.text,
          price: double.tryParse(_priceController.text) ?? 0.0,
          wholesalePrice: double.tryParse(_wholesalePriceController.text),
          quantity: quantity,
          imagePath: _imagePath,
          status: 'active',
        );

        if (widget.product == null) {
          await DatabaseHelper.instance.addProduct(product);
          
          // إذا كان المتجر مقفول، تحديث الكمية بعد إضافة الصور
          if (widget.requireCustomerRegistration) {
            final addedProducts = await DatabaseHelper.instance.getProducts(widget.sellerId);
            if (addedProducts.isNotEmpty) {
              final newProduct = addedProducts.lastWhere(
                (p) => p.name == product.name && p.categoryId == product.categoryId,
                orElse: () => product,
              );
              final images = await DatabaseHelper.instance.getProductImages(newProduct.productId);
              final imageCount = images.length;
              
              // تحديث الكمية
              final updatedProduct = product.copyWith(quantity: imageCount);
              await DatabaseHelper.instance.updateProduct(updatedProduct);
            }
          }
        } else {
          await DatabaseHelper.instance.updateProduct(product);
          
          // إذا كان المتجر مقفول، تحديث الكمية من عدد الصور
          if (widget.requireCustomerRegistration) {
            final images = await DatabaseHelper.instance.getProductImages(widget.product!.productId);
            final imageCount = images.length;
            
            // تحديث الكمية
            final updatedProduct = product.copyWith(quantity: imageCount);
            await DatabaseHelper.instance.updateProduct(updatedProduct);
          }
        }

        if (mounted) Navigator.pop(context, true);
      } catch (e) {
        if (mounted) {
           ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('خطأ في الحفظ: $e'), backgroundColor: Colors.red));
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final dialogWidth = (screenWidth < 600 ? screenWidth * 0.95 : 500.0).toDouble(); // عرض كامل على الموبايل
    
    return AlertDialog(
      title: Text(widget.product == null ? 'إضافة منتج جديد' : 'تعديل المنتج'),
      content: SingleChildScrollView(
        child: Container(
          width: dialogWidth,
          padding: const EdgeInsets.all(8),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'اسم المنتج', border: OutlineInputBorder()),
                  validator: (v) => v!.isEmpty ? 'مطلوب' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _descController,
                  decoration: const InputDecoration(labelText: 'الوصف', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                const SizedBox(height: 12),
                // على الموبايل: عمود واحد لكل حقل، على Desktop: صف واحد
                MediaQuery.of(context).size.width < 600 
                  ? Column(
                      children: [
                        TextFormField(
                          controller: _priceController,
                          decoration: const InputDecoration(
                            labelText: 'سعر البيع', 
                            border: OutlineInputBorder(),
                            hintText: 'مثال: 2000',
                          ),
                          keyboardType: TextInputType.number,
                          validator: (v) => v!.isEmpty ? 'مطلوب' : null,
                          style: const TextStyle(fontSize: 16),
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _wholesalePriceController,
                          decoration: const InputDecoration(
                            labelText: 'سعر الجملة', 
                            border: OutlineInputBorder(),
                            hintText: 'مثال: 1750',
                          ),
                          keyboardType: TextInputType.number,
                          style: const TextStyle(fontSize: 16),
                        ),
                        const SizedBox(height: 12),
                        // الكمية تُحدّث تلقائياً من معرج الصور (read-only)
                        TextFormField(
                          controller: _qtyController,
                          enabled: false,
                          decoration: InputDecoration(
                            labelText: 'الكمية (محدثة من المعرج)',
                            border: const OutlineInputBorder(),
                            disabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: Colors.grey)),
                            hintText: 'يتم التحديث من معرج الصور تلقائياً',
                          ),
                          keyboardType: TextInputType.number,
                          style: const TextStyle(fontSize: 16),
                        ),
                      ],
                    )
                  : Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _priceController,
                            decoration: const InputDecoration(
                              labelText: 'سعر البيع', 
                              border: OutlineInputBorder(),
                              hintText: 'مثال: 2000',
                            ),
                            keyboardType: TextInputType.number,
                            validator: (v) => v!.isEmpty ? 'مطلوب' : null,
                            style: const TextStyle(fontSize: 16),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextFormField(
                            controller: _wholesalePriceController,
                            decoration: const InputDecoration(
                              labelText: 'سعر الجملة', 
                              border: OutlineInputBorder(),
                              hintText: 'مثال: 1750',
                            ),
                            keyboardType: TextInputType.number,
                            style: const TextStyle(fontSize: 16),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // للمتاجر المفتوحة فقط: عرض حقل الكمية
                        if (!widget.requireCustomerRegistration)
                          Expanded(
                            child: TextFormField(
                              controller: _qtyController,
                              enabled: false,
                              decoration: InputDecoration(
                                labelText: 'الكمية (محدثة)',
                                border: const OutlineInputBorder(),
                                disabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: Colors.grey)),
                                hintText: 'من المعرج',
                              ),
                              keyboardType: TextInputType.number,
                              style: const TextStyle(fontSize: 16),
                            ),
                          ),
                      ],
                    ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  value: _selectedCategoryId,
                  decoration: const InputDecoration(labelText: 'الفئة', border: OutlineInputBorder()),
                  items: _categories.map((c) => DropdownMenuItem(value: c.categoryId, child: Text(c.name))).toList(),
                  onChanged: (v) => setState(() => _selectedCategoryId = v),
                )
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء', style: TextStyle(color: Colors.grey))),
        FilledButton(onPressed: _save, child: const Text('حفظ')),
      ],
    );
  }
}
