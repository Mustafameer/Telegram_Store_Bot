import 'dart:io';
import 'package:postgres/postgres.dart';
import 'package:path/path.dart' as p;

// Hardcoded from SyncService
const String _host = 'switchback.proxy.rlwy.net';
const int _port = 20266;
const String _databaseName = 'railway';
const String _username = 'postgres';
const String _password = 'bqcTJxNXLgwOftDoarrtmjmjYWurEIEh';
const String _localImagesPath = r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images';

Future<void> main() async {
  print("🔌 Connecting to Postgres...");
  
  final conn = await Connection.open(
    Endpoint(
      host: _host,
      database: _databaseName,
      username: _username,
      password: _password,
      port: _port,
    ),
    settings: ConnectionSettings(sslMode: SslMode.disable),
  );

  print("✅ Connected.");

  final imgDir = Directory(_localImagesPath);
  if (!await imgDir.exists()) {
    print("❌ Image folder not found: $_localImagesPath");
    return;
  }

  final localFiles = imgDir.listSync().whereType<File>().toList();
  print("🔍 Found ${localFiles.length} local files.");

  for (var file in localFiles) {
    final fileName = p.basename(file.path);
    print("Checking $fileName...");

    try {
      final check = await conn.execute(Sql.named('SELECT 1 FROM ImageStorage WHERE FileName = @name'), parameters: {'name': fileName});
      
      if (check.isEmpty) {
          print("📤 Uploading $fileName...");
          final bytes = await file.readAsBytes();
          
          await conn.execute(
            Sql.named('INSERT INTO ImageStorage (FileName, FileData) VALUES (@name, @data)'), 
            parameters: {'name': fileName, 'data': TypedValue(Type.byteArray, bytes)}
          );
          print("✅ Upload Success: $fileName");
      } else {
          print("⏭️ Skipped $fileName (Exists in Cloud)");
      }
    } catch (e) {
      print("❌ Error uploading $fileName: $e");
    }
  }

  await conn.close();
  print("🏁 Done.");
}
