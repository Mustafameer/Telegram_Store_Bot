import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import 'package:intl/intl.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

// دالة لتنسيق المبالغ مع فاصلة الآلاف وإزالة الكسور
String formatPrice(dynamic price) {
  if (price == null) return '0';
  final numValue = price is num ? price : double.tryParse(price.toString()) ?? 0;
  final rounded = numValue.round();
  final formatter = NumberFormat('#,###', 'ar');
  return formatter.format(rounded);
}

class SelectImagesScreen extends StatefulWidget {
  final Product product;
  final int sellerId;
  final int? customerTelegramId;

  const SelectImagesScreen({
    super.key,
    required this.product,
    required this.sellerId,
    this.customerTelegramId,
  });

  @override
  State<SelectImagesScreen> createState() => _SelectImagesScreenState();
}

class _SelectImagesScreenState extends State<SelectImagesScreen> {
  List<ProductImage> _images = [];
  bool _isLoading = true;
  int _selectedQuantity = 1;

  @override
  void initState() {
    super.initState();
    _loadImages();
  }

  Future<void> _loadImages() async {
    setState(() => _isLoading = true);
    try {
      final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
      // تصفية الصور ذات imagePath الفارغ
      final validImages = images.where((img) => img.imagePath.isNotEmpty).toList();
      setState(() {
        _images = validImages;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('خطأ في تحميل الصور: $e')),
        );
      }
    }
  }

  Future<void> _buyImages() async {
    if (_selectedQuantity > _images.length) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الكمية المحددة أكبر من الصور المتاحة')),
      );
      return;
    }

    // الحصول على معلومات الزبون باستخدام Telegram ID
    if (widget.customerTelegramId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('يجب تسجيل الدخول أولاً')),
      );
      return;
    }

    // البحث عن الزبون باستخدام Telegram ID
    final customers = await DatabaseHelper.instance.getCreditCustomers(widget.sellerId);
    final customer = customers.firstWhere(
      (c) => c.telegramId == widget.customerTelegramId,
      orElse: () => throw Exception('الزبون غير موجود'),
    );

    // حساب المبلغ الإجمالي
    final totalAmount = widget.product.price * _selectedQuantity;

    try {
      // 1. إضافة المعاملة الائتمانية
      await DatabaseHelper.instance.addCreditTransaction(
        customerId: customer.customerId,
        sellerId: widget.sellerId,
        transactionType: 'Purchase',
        amount: totalAmount,
        description: 'شراء ${_selectedQuantity} صورة من منتج: ${widget.product.name}',
      );

      // 2. تحديث كمية المنتج (تقليل بعدد الصور المشتراة)
      final newQuantity = (widget.product.quantity - _selectedQuantity).clamp(0, double.infinity).toInt();
      final updatedProduct = Product(
        productId: widget.product.productId,
        sellerId: widget.product.sellerId,
        categoryId: widget.product.categoryId,
        name: widget.product.name,
        description: widget.product.description,
        price: widget.product.price,
        wholesalePrice: widget.product.wholesalePrice,
        quantity: newQuantity,
        imagePath: widget.product.imagePath,
        status: widget.product.status,
      );
      await DatabaseHelper.instance.updateProduct(updatedProduct);

      // 3. حذف الصور المشتراة من قاعدة البيانات (محليًا)
      final imagesToDelete = _images.take(_selectedQuantity).toList();
      final imageIdsToDelete = imagesToDelete.map((img) => img.imageId).toList();
      
      for (final image in imagesToDelete) {
        await DatabaseHelper.instance.deleteProductImage(image.imageId);
      }

      // 4. إخبار البوت بحذف الصور من قاعدة البيانات (Cloud)
      print('🗑️ إرسال أمر حذف الصور للبوت...');
      try {
        final response = await http.post(
          Uri.parse('http://localhost:5000/api/delete-purchased-images'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'product_id': widget.product.productId,
            'image_ids': imageIdsToDelete,
          }),
        ).timeout(const Duration(seconds: 5));
        
        if (response.statusCode == 200) {
          print('✅ تم حذف الصور من البوت بنجاح');
        } else {
          print('⚠️ خطأ في حذف الصور من البوت: ${response.statusCode}');
        }
      } catch (e) {
        print('⚠️ تنبيه: لم يتمكن من الاتصال بالبوت لحذف الصور: $e');
        // لا نعطل الشراء إذا فشل حذف الصور من البوت
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ تم الشراء بنجاح! تم إضافة ${formatPrice(totalAmount)} د.ع إلى حسابك'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      print('❌ خطأ في شراء الصور: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خطأ في الشراء: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('اختر عدد الصور'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _images.isEmpty
              ? const Center(child: Text('لا توجد صور متاحة لهذا المنتج'))
              : Column(
                  children: [
                    // معلومات المنتج
                    Card(
                      margin: const EdgeInsets.all(16),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.product.name,
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Colors.blue[900], // أزرق غامق
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'السعر: ${formatPrice(widget.product.price)} د.ع للصورة الواحدة',
                              style: const TextStyle(fontSize: 16),
                            ),
                            Text(
                              'الصور المتاحة: ${_images.length} صورة',
                              style: const TextStyle(fontSize: 14, color: Colors.grey),
                            ),
                            Text(
                              'الكمية المتاحة: ${_images.length} صورة',
                              style: const TextStyle(fontSize: 14, color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                    ),
                    // اختيار الكمية
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'اختر عدد الصور:',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 16),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: List.generate(
                              _images.length,
                              (index) {
                                final qty = index + 1;
                                final isSelected = _selectedQuantity == qty;
                                return ChoiceChip(
                                  label: Text('$qty'),
                                  selected: isSelected,
                                  onSelected: (selected) {
                                    if (selected) {
                                      setState(() => _selectedQuantity = qty);
                                    }
                                  },
                                );
                              },
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'المبلغ الإجمالي: ${formatPrice(widget.product.price * _selectedQuantity)} د.ع',
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.blue,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(),
                    // زر الشراء
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _buyImages,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            backgroundColor: Colors.green,
                            foregroundColor: Colors.white,
                          ),
                          child: const Text(
                            'شراء الصور',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}
