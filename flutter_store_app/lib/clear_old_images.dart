import 'package:postgres/postgres.dart';

void main() async {
  final connection = await Connection.open(
    Endpoint(
      host: 'your-host.railway.app',
      port: 5432,
      database: 'railway',
      username: 'postgres',
      password: 'your-password',
    ),
  );

  try {
    print('🗑️  جاري حذف جميع الصور القديمة...');
    
    // حذف المنتجات المرتبطة أولاً
    await connection.execute('DELETE FROM "productimages"');
    print('✅ تم حذف جميع السجلات من productimages');
    
    // ثم حذف الصور
    await connection.execute('DELETE FROM "imagestorage"');
    print('✅ تم حذف جميع الصور من imagestorage');
    
    // التحقق
    final count = await connection.query('SELECT COUNT(*) FROM "imagestorage"');
    print('📊 عدد الصور المتبقية: ${count.first[0]}');
    
  } finally {
    await connection.close();
  }
}
