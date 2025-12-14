
import 'package:flutter/material.dart';
import '../../database/database_helper.dart';
import '../../models/database_models.dart';

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

  void _refreshCategories() {
    setState(() {
      _categoriesFuture = DatabaseHelper.instance.getCategories(widget.sellerId);
    });
  }


  Future<void> _editCategory(Category category) async {
    final controller = TextEditingController(text: category.name);
    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تعديل الفئة'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'اسم الفئة'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              if (controller.text.isNotEmpty) {
                 await DatabaseHelper.instance.updateCategory(Category(
                   categoryId: category.categoryId,
                   sellerId: category.sellerId,
                   name: controller.text,
                 ));
                 if (mounted) {
                   Navigator.pop(context);
                   _refreshCategories();
                 }
              }
            },
            child: const Text('حفظ'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteCategory(int categoryId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('حذف الفئة'),
        content: const Text('هل أنت متأكد من حذف هذه الفئة؟ سيتم حذف جميع المنتجات المرتبطة بها.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(context, true), 
            child: const Text('حذف', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await DatabaseHelper.instance.deleteCategory(categoryId);
      _refreshCategories();
    }
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
             return const Center(child: Text('لا يوجد فئات'));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: categories.length,
            itemBuilder: (context, index) {
              final category = categories[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Theme.of(context).primaryColor.withValues(alpha: 0.1),
                    child: const Icon(Icons.category, color: Color(0xFF2A9D8F)),
                  ),
                  title: Text(category.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                  trailing: widget.isEditable 
                    ? Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit, color: Colors.blue),
                            onPressed: () => _editCategory(category),
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
          );
        },
      ),
      floatingActionButton: widget.isEditable 
        ? FloatingActionButton(
          onPressed: () {
             showDialog(context: context, builder: (context) {
               final controller = TextEditingController();
               return AlertDialog(
                 title: const Text('إضافة فئة جديدة'),
                 content: TextField(
                   controller: controller,
                   decoration: const InputDecoration(labelText: 'اسم الفئة'),
                 ),
                 actions: [
                   TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
                   FilledButton(
                     onPressed: () async {
                       if (controller.text.isNotEmpty) {
                         await DatabaseHelper.instance.addCategory(Category(
                           categoryId: 0, 
                           sellerId: widget.sellerId,
                           name: controller.text,
                         ));
                         if (mounted) {
                           Navigator.pop(context);
                           _refreshCategories();
                         }
                       }
                     }, 
                     child: const Text('إضافة')
                   ),
                 ],
               );
             });
          },
          child: const Icon(Icons.add),
        )
        : null,
    );
  }
}
