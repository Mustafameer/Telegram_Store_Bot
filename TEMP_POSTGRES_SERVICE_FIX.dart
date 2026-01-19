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
        // Cache انتهت صلاحيته
        _imageCache.remove(fileName);
        _imageCacheTime.remove(fileName);
      }
      
      await _ensureConnection();
      
      // ✅ استرجاع البيانات بصيغة hex (أكثر موثوقية من base64)
      // hex encoding يتجنب مشاكل الترميز والأحرف الخاصة
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
        // ✅ تحويل hex string إلى bytes
        final hexString = hexData.toString();
        print('🔄 تحويل hex إلى bytes: $fileName (${hexString.length} حرف)');
        
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
