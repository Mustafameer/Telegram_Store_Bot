import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';

class ManageProductImagesScreen extends StatefulWidget {
  final Product product;

  const ManageProductImagesScreen({
    super.key,
    required this.product,
  });

  @override
  State<ManageProductImagesScreen> createState() => _ManageProductImagesScreenState();
}

class _ManageProductImagesScreenState extends State<ManageProductImagesScreen> {
  List<ProductImage> _images = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadImages();
  }

  Future<void> _loadImages() async {
    setState(() => _isLoading = true);
    try {
      final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
      setState(() {
        _images = images;
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

  Future<void> _addImages() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.image,
        allowMultiple: true,
      );

      if (result != null && result.files.isNotEmpty) {
        int addedCount = 0;
        int imageOrder = _images.length;

        for (var file in result.files) {
          if (file.path != null) {
            try {
              await DatabaseHelper.instance.addProductImage(
                widget.product.productId,
                file.path!,
                imageOrder: imageOrder++,
              );
              addedCount++;
            } catch (e) {
              print('خطأ في إضافة الصورة ${file.name}: $e');
            }
          }
        }
        
        // تحديث كمية المنتج تلقائياً إذا كان المتجر مقفول
        if (addedCount > 0) {
          final seller = await DatabaseHelper.instance.getSellerById(widget.product.sellerId);
          if (seller?.requireCustomerRegistration == true) {
            // إعادة تحميل الصور بعد الإضافة
            final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
            final imageCount = images.length;
            
            print('📊 عدد الصور بعد الإضافة: $imageCount');
            
            // الحصول على المنتج المحدث من قاعدة البيانات
            final products = await DatabaseHelper.instance.getProducts(widget.product.sellerId);
            final currentProduct = products.firstWhere(
              (p) => p.productId == widget.product.productId,
              orElse: () => widget.product,
            );
            
            // تحديث الكمية
            final updatedProduct = currentProduct.copyWith(quantity: imageCount);
            await DatabaseHelper.instance.updateProduct(updatedProduct);
            
            print('✅ تم تحديث الكمية إلى: $imageCount');
          }
        }

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('تم إضافة $addedCount صورة بنجاح'),
              backgroundColor: Colors.green,
            ),
          );
          _loadImages();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('خطأ في إضافة الصور: $e')),
        );
      }
    }
  }

  Future<void> _deleteImage(ProductImage image) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: const Text('هل أنت متأكد من حذف هذه الصورة؟'),
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
          await DatabaseHelper.instance.deleteProductImage(image.imageId);
          
          // تحديث كمية المنتج تلقائياً إذا كان المتجر مقفول
          final seller = await DatabaseHelper.instance.getSellerById(widget.product.sellerId);
          if (seller?.requireCustomerRegistration == true) {
            // إعادة تحميل الصور بعد الحذف
            final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
            final imageCount = images.length;
            
            print('📊 عدد الصور بعد الحذف: $imageCount');
            
            // الحصول على المنتج المحدث من قاعدة البيانات
            final products = await DatabaseHelper.instance.getProducts(widget.product.sellerId);
            final currentProduct = products.firstWhere(
              (p) => p.productId == widget.product.productId,
              orElse: () => widget.product,
            );
            
            // تحديث الكمية
            final updatedProduct = currentProduct.copyWith(quantity: imageCount);
            await DatabaseHelper.instance.updateProduct(updatedProduct);
            
            print('✅ تم تحديث الكمية إلى: $imageCount');
          }
          
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('تم حذف الصورة بنجاح'),
                backgroundColor: Colors.green,
              ),
            );
            _loadImages();
          }
        } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('خطأ في حذف الصورة: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('إدارة صور: ${widget.product.name}'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // معلومات المنتج
                Card(
                  margin: const EdgeInsets.all(16),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                widget.product.name,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'عدد الصور: ${_images.length}',
                                style: const TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _addImages,
                          icon: const Icon(Icons.add_photo_alternate),
                          label: const Text('إضافة صور'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.blue,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                // قائمة الصور
                Expanded(
                  child: _images.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.photo_library_outlined,
                                size: 64,
                                color: Colors.grey,
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'لا توجد صور حالياً',
                                style: TextStyle(
                                  fontSize: 16,
                                  color: Colors.grey,
                                ),
                              ),
                              const SizedBox(height: 16),
                              ElevatedButton.icon(
                                onPressed: _addImages,
                                icon: const Icon(Icons.add_photo_alternate),
                                label: const Text('إضافة صور'),
                              ),
                            ],
                          ),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(16),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 3,
                            crossAxisSpacing: 16,
                            mainAxisSpacing: 16,
                            childAspectRatio: 1.0,
                          ),
                          itemCount: _images.length,
                          itemBuilder: (context, index) {
                            final image = _images[index];
                            final file = File(image.imagePath);
                            final exists = file.existsSync();

                            return Stack(
                              children: [
                                Card(
                                  clipBehavior: Clip.antiAlias,
                                  child: exists
                                      ? Image.file(
                                          file,
                                          fit: BoxFit.cover,
                                          errorBuilder: (context, error, stackTrace) {
                                            return Container(
                                              color: Colors.grey[200],
                                              child: const Icon(
                                                Icons.broken_image,
                                                size: 40,
                                                color: Colors.grey,
                                              ),
                                            );
                                          },
                                        )
                                      : Container(
                                          color: Colors.grey[200],
                                          child: const Icon(
                                            Icons.image_not_supported,
                                            size: 40,
                                            color: Colors.grey,
                                          ),
                                        ),
                                ),
                                Positioned(
                                  top: 4,
                                  right: 4,
                                  child: Container(
                                    decoration: const BoxDecoration(
                                      color: Colors.red,
                                      shape: BoxShape.circle,
                                    ),
                                    child: IconButton(
                                      icon: const Icon(
                                        Icons.delete,
                                        color: Colors.white,
                                        size: 20,
                                      ),
                                      onPressed: () => _deleteImage(image),
                                      tooltip: 'حذف الصورة',
                                    ),
                                  ),
                                ),
                                if (!exists)
                                  Positioned(
                                    bottom: 4,
                                    left: 4,
                                    right: 4,
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.orange.withOpacity(0.8),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: const Text(
                                        'ملف غير موجود',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 10,
                                        ),
                                        textAlign: TextAlign.center,
                                      ),
                                    ),
                                  ),
                              ],
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
