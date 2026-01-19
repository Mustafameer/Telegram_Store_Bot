# 📱 Widget Update للصور من Firebase

## الملف: `manage_product_images_screen.dart` (السطور 359-400)

### استبدل هذا:
```dart
Card(
  clipBehavior: Clip.antiAlias,
  child: FutureBuilder<Uint8List?>(
    future: DatabaseHelper.instance.getImageData(image.imagePath),
    builder: (context, snapshot) {
      if (snapshot.connectionState == ConnectionState.waiting) {
        return Container(
          color: Colors.grey[100],
          child: const Center(child: CircularProgressIndicator()),
        );
      }
      
      if (snapshot.hasData && snapshot.data != null) {
        return Image.memory(snapshot.data!, fit: BoxFit.cover);
      }
      
      return Icon(Icons.broken_image);
    },
  ),
)
```

### بـ هذا:
```dart
Card(
  clipBehavior: Clip.antiAlias,
  child: FutureBuilder<String?>(
    future: DatabaseHelper.instance.getImageUrl(image.imagePath),
    builder: (context, snapshot) {
      print('🔍 حالة Firebase URL: ${image.imagePath}, الحالة: ${snapshot.connectionState}');
      
      // إذا توفر رابط Firebase
      if (snapshot.hasData && snapshot.data != null) {
        print('🔥 استخدام Firebase URL: ${snapshot.data}');
        return Image.network(
          snapshot.data!,
          fit: BoxFit.cover,
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded /
                        loadingProgress.expectedTotalBytes!
                    : null,
              ),
            );
          },
          errorBuilder: (context, error, stackTrace) {
            print('⚠️ خطأ Firebase: $error - محاولة fallback');
            // استخدم الطريقة القديمة كـ fallback
            return FutureBuilder<Uint8List?>(
              future: DatabaseHelper.instance.getImageData(image.imagePath),
              builder: (context, memSnapshot) {
                if (memSnapshot.hasData) {
                  return Image.memory(memSnapshot.data!, fit: BoxFit.cover);
                }
                return Container(
                  color: Colors.grey[200],
                  child: const Icon(Icons.broken_image),
                );
              },
            );
          },
        );
      }
      
      // إذا لم يتوفر رابط - استخدم البيانات الثنائية
      return FutureBuilder<Uint8List?>(
        future: DatabaseHelper.instance.getImageData(image.imagePath),
        builder: (context, memSnapshot) {
          if (memSnapshot.connectionState == ConnectionState.waiting) {
            return Container(
              color: Colors.grey[100],
              child: const Center(child: CircularProgressIndicator()),
            );
          }
          
          if (memSnapshot.hasData && memSnapshot.data != null) {
            return Image.memory(memSnapshot.data!, fit: BoxFit.cover);
          }
          
          return Container(
            color: Colors.grey[200],
            child: const Icon(Icons.image_not_supported),
          );
        },
      );
    },
  ),
)
```

---

## ملفات أخرى قد تحتاج تحديث:

### 1. في أي widget يعرض صور المنتجات:
- `lib/screens/products_screen.dart` (إن وجد)
- `lib/screens/product_detail_screen.dart` (إن وجد)
- أي FutureBuilder يستخدم `getImageData()`

### 2. النمط العام للتحديث:

```dart
// ❌ القديم
FutureBuilder<Uint8List?>(
  future: postgresService.getImageData(imagePath),
  builder: (context, snapshot) {
    return Image.memory(snapshot.data!);
  },
)

// ✅ الجديد
FutureBuilder<String?>(
  future: postgresService.getImageUrl(imagePath),
  builder: (context, snapshot) {
    if (snapshot.hasData && snapshot.data != null) {
      return Image.network(snapshot.data!); // Firebase
    }
    
    // Fallback لـ البيانات الثنائية
    return FutureBuilder<Uint8List?>(
      future: postgresService.getImageData(imagePath),
      builder: (context, memSnapshot) {
        return Image.memory(memSnapshot.data!);
      },
    );
  },
)
```

---

## 🧪 الاختبار:

1. **شغل التطبيق**
2. **اعرض صورة منتج**
3. **يجب أن تشوف:**
   - 🔥 Firebase URL في الـ logs
   - ⚡ الصورة تحمل بسرعة
   - ✅ بدون أخطاء

---

**أين بالضبط تحتاج التحديث في manage_product_images_screen.dart؟**
- السطور 359-400 (Card مع Image)
