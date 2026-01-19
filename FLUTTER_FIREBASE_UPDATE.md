# 📱 Flutter Firebase Integration

## الملفات التي تحتاج تحديث:

### 1. `lib/services/postgres_service.dart`

#### أضف هذه الدالة الجديدة:

```dart
Future<String?> getImageUrl(String fileName) async {
  """الحصول على رابط Firebase للصورة"""
  try {
    if (fileName.isEmpty) {
      print('❌ اسم الملف فارغ');
      return null;
    }
    
    await _ensureConnection();
    
    // جرب الحصول على رابط Firebase أولاً
    final results = await _connection!.execute(
      'SELECT url FROM imagestorage WHERE filename = \$1',
      parameters: [fileName],
    );
    
    if (results.isNotEmpty) {
      final url = results.first.toColumnMap()['url'];
      if (url != null && url.toString().isNotEmpty) {
        print('🔥 Firebase URL: ${url.toString()}');
        return url.toString();
      }
    }
    
    print('⚠️ لم يتم العثور على رابط Firebase');
    return null;
    
  } catch (e) {
    print('❌ خطأ: $e');
    return null;
  }
}
```

#### عدّل دالة `getImageData()`:

```dart
Future<Uint8List?> getImageData(String fileName) async {
  try {
    if (fileName.isEmpty) {
      print('❌ اسم الملف فارغ');
      return null;
    }
    
    // تحقق من الـ cache أولاً
    if (_imageCache.containsKey(fileName)) {
      final cacheTime = _imageCacheTime[fileName];
      if (cacheTime != null) {
        final elapsed = DateTime.now().difference(cacheTime);
        if (elapsed.inMinutes < _cacheValidityMinutes) {
          print('💾 استرجاع من الـ cache: $fileName');
          return _imageCache[fileName];
        }
      }
      _imageCache.remove(fileName);
      _imageCacheTime.remove(fileName);
    }
    
    await _ensureConnection();
    
    // استرجاع البيانات بصيغة hex (للـ fallback)
    final results = await _connection!.execute(
      'SELECT encode(filedata, \'hex\') as filedata FROM imagestorage WHERE filename = \$1',
      parameters: [fileName],
    );
    
    if (results.isEmpty) {
      print('⚠️ لم يتم العثور على الصورة: $fileName');
      return null;
    }
    
    final row = results.first.toColumnMap();
    final hexData = row['filedata'];
    
    if (hexData == null) {
      print('⚠️ بيانات الصورة فارغة: $fileName');
      return null;
    }

    try {
      // تحويل hex string إلى bytes
      final hexString = hexData.toString();
      print('🔄 تحويل hex إلى bytes: $fileName');
      
      final uint8Bytes = Uint8List.fromList(
        List<int>.generate(hexString.length ~/ 2, (i) => 
          int.parse(hexString.substring(i * 2, i * 2 + 2), radix: 16)
        )
      );
      
      print('✅ تم التحويل بنجاح: ${uint8Bytes.length} bytes');
      
      // احفظ في الـ cache
      _imageCache[fileName] = uint8Bytes;
      _imageCacheTime[fileName] = DateTime.now();
      
      return uint8Bytes;
    } catch (e) {
      print('❌ خطأ في تحويل hex: $e');
      return null;
    }
  } catch (e) {
    print('❌ خطأ في جلب بيانات الصورة: $e');
    return null;
  }
}
```

---

### 2. في Widgets (قراءة الصور):

بدلاً من:
```dart
FutureBuilder<Uint8List?>(
  future: postgresService.getImageData(imagePath),
  builder: (context, snapshot) {
    if (snapshot.hasData) {
      return Image.memory(snapshot.data!);
    }
    return Icon(Icons.image);
  },
)
```

استخدم:
```dart
FutureBuilder<String?>(
  future: postgresService.getImageUrl(imagePath),
  builder: (context, snapshot) {
    // إذا توفر رابط Firebase
    if (snapshot.hasData && snapshot.data != null) {
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
          print('خطأ في تحميل من Firebase: $error');
          // استخدم الطريقة القديمة كـ fallback
          return FutureBuilder<Uint8List?>(
            future: postgresService.getImageData(imagePath),
            builder: (context, memSnapshot) {
              if (memSnapshot.hasData) {
                return Image.memory(memSnapshot.data!);
              }
              return Icon(Icons.broken_image);
            },
          );
        },
      );
    }
    
    // إذا لم يتوفر رابط، استخدم البيانات الثنائية
    return FutureBuilder<Uint8List?>(
      future: postgresService.getImageData(imagePath),
      builder: (context, memSnapshot) {
        if (memSnapshot.hasData) {
          return Image.memory(memSnapshot.data!);
        }
        if (memSnapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        return Icon(Icons.image_not_supported);
      },
    );
  },
)
```

---

## 🧪 الاختبار:

### 1. جرّب Bot:
```
أرسل صورة من Telegram → يجب أن يرى في Firebase Console ✅
```

### 2. جرّب Flutter:
```
أضف منتج مع صورة → يجب أن تظهر بسرعة ⚡
```

---

**هل تريد أن أساعدك في تطبيق هذه التحديثات على Flutter أيضاً؟** 🚀
