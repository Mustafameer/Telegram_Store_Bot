
import 'package:flutter/material.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';

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
    showDialog(
      context: context,
      builder: (context) => CategoryFormDialog(
        initialName: category?.name,
        initialImagePath: category?.imagePath,
        onSave: (name, imagePath) async {
          final newCategory = Category(
            categoryId: category?.categoryId ?? 0,
            sellerId: widget.sellerId,
            name: name,
            orderIndex: category?.orderIndex ?? 0,
            imagePath: imagePath,
          );

          if (category == null) {
            await DatabaseHelper.instance.addCategory(newCategory);
          } else {
            await DatabaseHelper.instance.updateCategory(newCategory);
          }
          if (mounted) _refreshCategories(force: true);
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
                   ElevatedButton(onPressed: () => _refreshCategories(force: true), child: const Text('تحديث'))
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
                      backgroundImage: category.imagePath != null ? FileImage(File(category.imagePath!)) : null,
                      child: category.imagePath == null ? const Icon(Icons.category, color: Color(0xFF2A9D8F)) : null,
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
  final String? initialName;
  final String? initialImagePath;
  final Future<void> Function(String name, String? imagePath) onSave;

  const CategoryFormDialog({
    super.key, 
    this.initialName, 
    this.initialImagePath, 
    required this.onSave
  });

  @override
  State<CategoryFormDialog> createState() => _CategoryFormDialogState();
}

class _CategoryFormDialogState extends State<CategoryFormDialog> {
  late TextEditingController _nameController;
  String? _imagePath;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialName);
    _imagePath = widget.initialImagePath;
  }

  Future<void> _pickImage() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image);
    if (result != null) {
      setState(() {
        _imagePath = result.files.single.path;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.initialName == null ? 'إضافة فئة' : 'تعديل الفئة'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          GestureDetector(
            onTap: _pickImage,
            child: Container(
              height: 120,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[200],
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(8),
                image: _imagePath != null 
                  ? DecorationImage(image: FileImage(File(_imagePath!)), fit: BoxFit.cover)
                  : null,
              ),
              child: _imagePath == null 
                ? const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.add_a_photo, size: 40, color: Colors.grey),
                      SizedBox(height: 8),
                      Text('اضغط لإضافة صورة', style: TextStyle(color: Colors.grey)),
                    ],
                  )
                : null,
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'اسم الفئة'),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        FilledButton(
          onPressed: () async {
            if (_nameController.text.isNotEmpty) {
              try {
                await widget.onSave(_nameController.text, _imagePath);
                if (context.mounted) Navigator.pop(context);
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red));
                }
              }
            }
          },
          child: const Text('حفظ'),
        ),
      ],
    );
  }
}
