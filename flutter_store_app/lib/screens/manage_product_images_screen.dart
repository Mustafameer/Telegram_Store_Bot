import 'dart:typed_data';
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
      print('🔍 جاري تحميل الصور للمنتج: ${widget.product.productId}');
      final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
      print('✅ تم تحميل ${images.length} صورة للمنتج ${widget.product.productId}');
      for (var img in images) {
        print('   - صورة ID: ${img.imageId}, المسار: ${img.imagePath}');
      }
      setState(() {
        _images = images;
        _isLoading = false;
      });
    } catch (e, stackTrace) {
      print('❌ خطأ في تحميل الصور: $e');
      print('📍 StackTrace: $stackTrace');
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خطأ في تحميل الصور: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
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
        print('📁 تم اختيار ${result.files.length} صورة');
        int addedCount = 0;
        int imageOrder = _images.length;

        for (var file in result.files) {
          if (file.path != null) {
            try {
              print('📤 جاري إضافة الصورة: ${file.name}');
              final imageId = await DatabaseHelper.instance.addProductImage(
                widget.product.productId,
                file.path!,
                imageOrder: imageOrder++,
              );
              if (imageId > 0) {
                print('✅ تم إضافة الصورة بنجاح: ${file.name} (ID: $imageId)');
                addedCount++;
              } else {
                print('❌ فشل إضافة الصورة: ${file.name}');
              }
            } catch (e) {
              print('❌ خطأ في إضافة الصورة ${file.name}: $e');
            }
          }
        }
        
        print('📊 تم إضافة $addedCount صورة من أصل ${result.files.length}');
        
        // تحديث كمية المنتج تلقائياً
        if (addedCount > 0) {
          try {
            print('📥 جاري جلب الصور بعد الإضافة...');
            final images = await DatabaseHelper.instance.getProductImages(widget.product.productId);
            final imageCount = images.length;
            
            print('📊 عدد الصور بعد الإضافة: $imageCount');
            print('   - الصور:');
            for (var img in images) {
              print('   - صورة ID: ${img.imageId}, المسار: ${img.imagePath}');
            }
            
            // تحديث الكمية بناءً على عدد الصور
            print('🔄 جاري تحديث الكمية من ${widget.product.quantity} إلى $imageCount');
            final updatedProduct = widget.product.copyWith(quantity: imageCount);
            await DatabaseHelper.instance.updateProduct(updatedProduct);
            
            print('✅ تم تحديث الكمية إلى: $imageCount');
            print('📝 المنتج المحدث: ${updatedProduct.name}, الكمية: ${updatedProduct.quantity}');
          } catch (e) {
            print('❌ خطأ في تحديث الكمية: $e');
          }
        }

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('تم إضافة $addedCount صورة بنجاح'),
              backgroundColor: Colors.green,
            ),
          );
          await Future.delayed(const Duration(milliseconds: 500));
          _loadImages();
        }
      }
    } catch (e) {
      print('❌ خطأ في عملية الإضافة: $e');
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
            
            // تحديث الكمية مباشرة
            final updatedProduct = widget.product.copyWith(quantity: imageCount);
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
        title: Text(
          'إدارة صور: ${widget.product.name}',
          style: TextStyle(
            color: Colors.blue[900], // أزرق غامق
          ),
        ),
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
                            
                            // حساب الحجم: 4×4 سم = ~454×454 pixels (عند 96 DPI)
                            final imageSize = 454.0;
                            
                            return Container(
                              width: imageSize,
                              height: imageSize,
                              child: Stack(
                                children: [
                                  Card(
                                  clipBehavior: Clip.antiAlias,
                                  child: FutureBuilder<Uint8List?>(
                                    future: DatabaseHelper.instance.getImageData(image.imagePath),
                                    builder: (context, snapshot) {
                                      print('🔍 حالة الصورة: ${image.imagePath}, الحالة: ${snapshot.connectionState}');
                                      
                                      if (snapshot.connectionState == ConnectionState.waiting) {
                                        print('⏳ جاري تحميل الصورة: ${image.imagePath}');
                                        return Container(
                                          color: Colors.grey[100],
                                          child: const Center(
                                            child: CircularProgressIndicator(),
                                          ),
                                        );
                                      }
                                      
                                      if (snapshot.hasData && snapshot.data != null) {
                                        print('✅ تم تحميل الصورة بنجاح: ${image.imagePath}, الحجم: ${snapshot.data!.length} bytes');
                                        return Image.memory(
                                          snapshot.data!,
                                          fit: BoxFit.cover,
                                          errorBuilder: (context, error, stackTrace) {
                                            print('❌ خطأ في عرض الصورة: ${image.imagePath}, الخطأ: $error');
                                            return Container(
                                              color: Colors.grey[200],
                                              child: const Column(
                                                mainAxisAlignment: MainAxisAlignment.center,
                                                children: [
                                                  Icon(
                                                    Icons.broken_image,
                                                    size: 40,
                                                    color: Colors.grey,
                                                  ),
                                                  SizedBox(height: 8),
                                                  Text(
                                                    'خطأ في الصورة',
                                                    style: TextStyle(fontSize: 10, color: Colors.grey),
                                                  ),
                                                ],
                                              ),
                                            );
                                          },
                                        );
                                      }
                                      
                                      if (snapshot.hasError) {
                                        print('⚠️ خطأ في تحميل الصورة: ${image.imagePath}, الخطأ: ${snapshot.error}');
                                        return Container(
                                          color: Colors.red[100],
                                          child: Center(
                                            child: Column(
                                              mainAxisAlignment: MainAxisAlignment.center,
                                              children: [
                                                const Icon(
                                                  Icons.error,
                                                  size: 40,
                                                  color: Colors.red,
                                                ),
                                                const SizedBox(height: 8),
                                                Text(
                                                  '${snapshot.error}'.length > 30 ? '${snapshot.error}'.substring(0, 30) + '...' : '${snapshot.error}',
                                                  style: const TextStyle(fontSize: 9, color: Colors.red),
                                                  textAlign: TextAlign.center,
                                                ),
                                              ],
                                            ),
                                          ),
                                        );
                                      }
                                      
                                      print('⚠️ لم يتم تحميل الصورة: ${image.imagePath}، البيانات: ${snapshot.data}');
                                      return Container(
                                        color: Colors.grey[300],
                                        child: const Center(
                                          child: Column(
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              Icon(
                                                Icons.image_not_supported,
                                                size: 40,
                                                color: Colors.grey,
                                              ),
                                              SizedBox(height: 8),
                                              Text(
                                                'لم يتم تحميل الصورة',
                                                style: TextStyle(fontSize: 10, color: Colors.grey),
                                              ),
                                            ],
                                          ),
                                        ),
                                      );
                                    },
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
                              ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
