import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

class StoreFormDialog extends StatefulWidget {
  final String? initialName;
  final String? initialTelegramId;
  final String? initialUserName;
  final String? initialImagePath;
  final bool isEdit;
  final Future<void> Function(String name, int telegramId, String userName, String? imagePath) onSave;

  const StoreFormDialog({
    super.key, 
    this.initialName,
    this.initialTelegramId,
    this.initialUserName,
    this.initialImagePath,
    this.isEdit = false,
    required this.onSave
  });

  @override
  State<StoreFormDialog> createState() => _StoreFormDialogState();
}

class _StoreFormDialogState extends State<StoreFormDialog> {
  late TextEditingController _nameController;
  late TextEditingController _idController;
  late TextEditingController _userController;
  String? _imagePath;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialName);
    _idController = TextEditingController(text: widget.initialTelegramId);
    _userController = TextEditingController(text: widget.initialUserName);
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
      title: Text(widget.isEdit ? 'تعديل المتجر' : 'إضافة متجر جديد'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            GestureDetector(
              onTap: _pickImage,
              child: Container(
              height: 120,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[200],
                shape: BoxShape.rectangle, // Changed to rectangle for better visibility, or keep circle? Detailed view shows circle. Layout is easier with rectangle for upload area.
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade300),
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
                       Text('شعار المتجر', style: TextStyle(color: Colors.grey))
                    ]
                 )
                : null,
            ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'اسم المتجر', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _idController,
              decoration: const InputDecoration(labelText: 'معرف تليجرام (ID)', border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _userController,
              decoration: const InputDecoration(labelText: 'اسم المستخدم (User)', border: OutlineInputBorder()),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        FilledButton(
          onPressed: () async {
            if (_nameController.text.isNotEmpty && _idController.text.isNotEmpty) {
              final tid = int.tryParse(_idController.text);
              if (tid != null) {
                try {
                   await widget.onSave(_nameController.text, tid, _userController.text, _imagePath);
                   // onSave implementation handles Navigator.pop? 
                   // No, usually parent handles it? 
                   // In HomeScreen, it does Navigator.pop. 
                   // But if I want to catch error here, I should probably NOT let parent pop blindly.
                   // Wait. CategoriesTab pops. HomeScreen pops.
                   // If I await here, I catch error here.
                   // But parent 'onSave' calls 'await DatabaseHelper...'.
                   // So if it throws, I catch it here.
                   // So I should NOT pop in parent? Or parent pop is fine?
                   // In HomeScreen: `onSave: (...) async { await DB...; Navigator.pop; }`
                   // If DB throws, subsequent lines in parent won't run.
                   // So it throws to here.
                   // So I catch it here. And I do NOT pop here (parent handles pop on success).
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('خطأ: $e'), backgroundColor: Colors.red));
                  }
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
