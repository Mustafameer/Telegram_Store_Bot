import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';

class ManageProductImagesScreen extends StatefulWidget {
  final Product product;

  const ManageProductImagesScreen({super.key, required this.product});

  @override
  State<ManageProductImagesScreen> createState() =>
      _ManageProductImagesScreenState();
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
      final images = await DatabaseHelper.instance.getProductImages(
        widget.product.productId,
      );
      final validImages = images
          .where((img) => img.imagePath.isNotEmpty)
          .toList();
      setState(() {
        _images = validImages;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red),
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
              final imageId = await DatabaseHelper.instance.addProductImage(
                widget.product.productId,
                file.path!,
                imageOrder: imageOrder++,
              );
              if (imageId > 0) {
                addedCount++;
              }
            } catch (e) {
              print('خطأ: $e');
            }
          }
        }

        if (addedCount > 0) {
          await _loadImages();
          
          // تحديث الكمية تلقائياً = عدد الصور
          final updatedProduct = widget.product.copyWith(quantity: _images.length);
          await DatabaseHelper.instance.updateProduct(updatedProduct);
          
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('✅ تم إضافة $addedCount صورة'),
                backgroundColor: Colors.green,
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _deleteImage(ProductImage image) async {
    try {
      await DatabaseHelper.instance.deleteProductImage(image.imageId);
      setState(() {
        _images.removeWhere((img) => img.imageId == image.imageId);
      });
      
      // تحديث الكمية تلقائياً = عدد الصور المتبقية
      final updatedProduct = widget.product.copyWith(quantity: _images.length);
      await DatabaseHelper.instance.updateProduct(updatedProduct);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ تم حذف الصورة'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('إدارة الصور: ${widget.product.name}')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  child: _images.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.image_not_supported,
                                size: 64,
                                color: Colors.grey[400],
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'لا توجد صور',
                                style: Theme.of(
                                  context,
                                ).textTheme.headlineSmall,
                              ),
                              const SizedBox(height: 32),
                              ElevatedButton.icon(
                                onPressed: _addImages,
                                icon: const Icon(Icons.add_a_photo),
                                label: const Text('إضافة صور'),
                              ),
                            ],
                          ),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(16),
                          gridDelegate:
                              const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 9,
                                crossAxisSpacing: 8,
                                mainAxisSpacing: 8,
                                childAspectRatio: 1.0,
                              ),
                          itemCount: _images.length,
                          itemBuilder: (context, index) {
                            final image = _images[index];
                            return Container(
                              child: Stack(
                                children: [
                                  Card(
                                    clipBehavior: Clip.antiAlias,
                                    child: FutureBuilder<String?>(
                                      future: DatabaseHelper.instance
                                          .getImageUrl(image.imagePath),
                                      builder: (context, snapshot) {
                                        // جرب Firebase أولاً
                                        if (snapshot.hasData &&
                                            snapshot.data != null) {
                                          return Image.network(
                                            snapshot.data!,
                                            fit: BoxFit.cover,
                                            errorBuilder:
                                                (context, error, stackTrace) {
                                                  // إذا فشل Firebase، استخدم البيانات المحلية
                                                  return FutureBuilder<
                                                    Uint8List?
                                                  >(
                                                    future: DatabaseHelper
                                                        .instance
                                                        .getImageData(
                                                          image.imagePath,
                                                        ),
                                                    builder:
                                                        (context, memSnapshot) {
                                                          if (memSnapshot
                                                                  .hasData &&
                                                              memSnapshot
                                                                      .data !=
                                                                  null) {
                                                            return Image.memory(
                                                              memSnapshot.data!,
                                                              fit: BoxFit.cover,
                                                            );
                                                          }
                                                          return Container(
                                                            color: Colors
                                                                .grey[200],
                                                            child: const Icon(
                                                              Icons
                                                                  .broken_image,
                                                            ),
                                                          );
                                                        },
                                                  );
                                                },
                                          );
                                        }

                                        // إذا لم يتوفر Firebase، استخدم البيانات المحلية
                                        return FutureBuilder<Uint8List?>(
                                          future: DatabaseHelper.instance
                                              .getImageData(image.imagePath),
                                          builder: (context, memSnapshot) {
                                            if (memSnapshot.connectionState ==
                                                ConnectionState.waiting) {
                                              return Container(
                                                color: Colors.grey[100],
                                                child: const Center(
                                                  child:
                                                      CircularProgressIndicator(),
                                                ),
                                              );
                                            }

                                            if (memSnapshot.hasData &&
                                                memSnapshot.data != null) {
                                              return Image.memory(
                                                memSnapshot.data!,
                                                fit: BoxFit.cover,
                                              );
                                            }

                                            return Container(
                                              color: Colors.grey[200],
                                              child: const Icon(
                                                Icons.image_not_supported,
                                              ),
                                            );
                                          },
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
      floatingActionButton: FloatingActionButton(
        onPressed: _addImages,
        tooltip: 'إضافة صور',
        child: const Icon(Icons.add_a_photo),
      ),
    );
  }
}
