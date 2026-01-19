
import 'package:flutter/material.dart';
import 'dart:typed_data';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';
import '../../services/postgres_service.dart';

import 'dart:io';
import 'package:file_picker/file_picker.dart';

// ... (CategoryFormDialog class implementation)

class CategoriesTab extends StatefulWidget {
  final int sellerId;
  final bool isEditable;

  const CategoriesTab({
    super.key, 
    required this.sellerId, 
    this.isEditable = false,
  });

  @override
  State<CategoriesTab> createState() => _CategoriesTabState();
}

class _CategoriesTabState extends State<CategoriesTab> {
  late Future<List<Category>> _categoriesFuture;

  @override
  void initState() {
    super.initState();
    _refreshCategories();
  }

  Future<void> _refreshCategories({bool force = false}) async {
    setState(() {
      _categoriesFuture = DatabaseHelper.instance.getCategories(widget.sellerId, forceRefresh: force);
    });
    await _categoriesFuture; // Wait for it to complete for RefreshIndicator
  }

  // ... (Dialog methods use _refreshCategories() which defaults to force=false, which is fine as write invalidates cache)

  Future<void> _deleteCategory(int categoryId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: const Text('هل أنت متأكد من حذف هذا القسم؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('حذف')),
        ],
      ),
    );

    if (confirm == true) {
      await DatabaseHelper.instance.deleteCategory(categoryId);
      _refreshCategories(force: true);
    }
  }

  void _showCategoryDialog({Category? category}) {
    // ⚠️ السماح للبائع بإضافة الفئات لمتجره حتى لو كان مقفولاً
    // لكن منع TELEBOT من الفئات (لأنه متجر موحد)
    if (!widget.isEditable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🔒 هذا المتجر ليس متجرك - لا يمكنك إضافة فئات'),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }
    
    showDialog(
      context: context,
      builder: (context) => CategoryFormDialog(
        categoryId: category?.categoryId,
        initialName: category?.name,
        initialImagePath: category?.imagePath,
        isEditable: widget.isEditable,
        onSave: (name, imagePath, imageBytes) async {
          final newCategory = Category(
            categoryId: category?.categoryId ?? 0,
            sellerId: widget.sellerId,
            name: name,
            orderIndex: category?.orderIndex ?? 0,
            imagePath: imagePath,
            imageFileName: category?.imageFileName,
            imageUrl: category?.imageUrl,
          );

          try {
            print('🔄 [CategoriesTab] Starting category save...');
            if (category == null) {
              print('📝 [CategoriesTab] Adding new category: $name');
              final newCategoryId = await DatabaseHelper.instance.addCategory(newCategory);
              print('✅ [CategoriesTab] New category added successfully (ID: $newCategoryId)');
              
              // Save image to database if provided
              if (imageBytes != null && newCategoryId != null) {
                final fileName = 'category_${newCategoryId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
                final saved = await PostgresService().saveCategoryImage(newCategoryId, imageBytes, fileName);
                if (saved) {
                  print('✅ Category image saved to database');
                } else {
                  print('⚠️ Failed to save category image');
                }
              }
            } else {
              print('✏️ [CategoriesTab] Updating category: $name');
              await DatabaseHelper.instance.updateCategory(newCategory);
              print('✅ [CategoriesTab] Category updated successfully');
              
              // Save image to database if provided
              if (imageBytes != null) {
                final fileName = 'category_${category.categoryId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
                await PostgresService().saveCategoryImage(category.categoryId, imageBytes, fileName);
                print('✅ Category image updated in database');
              }
            }
          } catch (e) {
            print('❌ [CategoriesTab] Error saving category: $e');
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('❌ خطأ: $e')),
              );
            }
            return;
          }
          
          if (mounted) {
            print('🔄 [CategoriesTab] Refreshing categories list...');
            await _refreshCategories(force: true);
            print('✅ [CategoriesTab] Categories list refreshed');
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<List<Category>>(
        future: _categoriesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          
          final categories = snapshot.data ?? [];
          
           if (categories.isEmpty) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('لا يوجد فئات'),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ElevatedButton(onPressed: () => _refreshCategories(force: true), child: const Text('تحديث')),
                        if (widget.isEditable) ...[
                          const SizedBox(width: 16),
                          FilledButton.icon(
                            onPressed: () => _showCategoryDialog(),
                            icon: const Icon(Icons.add),
                            label: const Text('إضافة فئة'),
                          ),
                        ],
                      ],
                    ),
                  ],
                )
              );
           }

          return RefreshIndicator(
            onRefresh: () => _refreshCategories(force: true),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: categories.length,
              itemBuilder: (context, index) {
                final category = categories[index];
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Theme.of(context).primaryColor.withValues(alpha: 0.1),
                      child: _CategoryImageBuilder(categoryId: category.categoryId),
                    ),
                    title: Text(category.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                    trailing: widget.isEditable 
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit, color: Colors.blue),
                              onPressed: () => _showCategoryDialog(category: category),
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete, color: Colors.red),
                              onPressed: () => _deleteCategory(category.categoryId),
                            ),
                          ],
                        )
                      : null,
                  ),
                );
              },
            ),
          );
        },
      ),
      floatingActionButton: widget.isEditable 
        ? FloatingActionButton(
          onPressed: () => _showCategoryDialog(),
          child: const Icon(Icons.add),
        )
        : null,
    );
  }
}

class CategoryFormDialog extends StatefulWidget {
  final int? categoryId;
  final String? initialName;
  final String? initialImagePath;
  final bool isEditable;
  final Future<void> Function(String name, String? imagePath, Uint8List? imageBytes) onSave;

  const CategoryFormDialog({
    super.key,
    this.categoryId,
    this.initialName, 
    this.initialImagePath,
    this.isEditable = true,
    required this.onSave
  });

  @override
  State<CategoryFormDialog> createState() => _CategoryFormDialogState();
}

class _CategoryFormDialogState extends State<CategoryFormDialog> {
  late TextEditingController _nameController;
  String? _imagePath;
  Uint8List? _imageBytes;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialName);
    _imagePath = widget.initialImagePath;
  }

  Future<void> _pickImage() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image);
    if (result != null) {
      final file = File(result.files.single.path!);
      final bytes = await file.readAsBytes();
      setState(() {
        _imagePath = result.files.single.path;
        _imageBytes = bytes;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          Expanded(
            child: Text(widget.initialName == null ? 'إضافة فئة' : 'تعديل الفئة'),
          ),
          if (!widget.isEditable)
            const Icon(Icons.lock, color: Colors.red, size: 20),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          GestureDetector(
            onTap: widget.isEditable ? _pickImage : null,
            child: Container(
              height: 120,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[200],
                border: Border.all(color: widget.isEditable ? Colors.grey : Colors.red),
                borderRadius: BorderRadius.circular(8),
                image: _imagePath != null 
                  ? DecorationImage(image: FileImage(File(_imagePath!)), fit: BoxFit.cover)
                  : null,
              ),
              child: _imagePath == null 
                ? Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        widget.isEditable ? Icons.add_a_photo : Icons.lock,
                        size: 40,
                        color: widget.isEditable ? Colors.grey : Colors.red,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        widget.isEditable ? 'اضغط لإضافة صورة' : '🔒 لا يمكن التعديل',
                        style: TextStyle(
                          color: widget.isEditable ? Colors.grey : Colors.red,
                        ),
                      ),
                    ],
                  )
                : null,
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nameController,
            enabled: widget.isEditable,
            decoration: InputDecoration(
              labelText: 'اسم الفئة',
              suffixIcon: !widget.isEditable ? const Icon(Icons.lock, color: Colors.red) : null,
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        FilledButton(
          onPressed: widget.isEditable && _nameController.text.isNotEmpty ? () async {
            try {
              await widget.onSave(_nameController.text, _imagePath, _imageBytes);
              if (context.mounted) {
                await Future.delayed(const Duration(milliseconds: 500));
                if (context.mounted) Navigator.pop(context);
              }
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red));
              }
            }
          } : null,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!widget.isEditable) const Icon(Icons.lock, size: 16),
              const SizedBox(width: 4),
              const Text('حفظ'),
            ],
          ),
        ),
      ],
    );
  }
}
// Widget لعرض صورة الفئة من قاعدة البيانات
class _CategoryImageBuilder extends StatelessWidget {
  final int categoryId;

  const _CategoryImageBuilder({required this.categoryId});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Uint8List?>(
      future: PostgresService().getCategoryImageData(categoryId),
      builder: (context, snapshot) {
        if (snapshot.hasData && snapshot.data != null) {
          return Image.memory(
            snapshot.data!,
            fit: BoxFit.cover,
          );
        }
        return const Icon(Icons.category, color: Color(0xFF2A9D8F));
      },
    );
  }
}