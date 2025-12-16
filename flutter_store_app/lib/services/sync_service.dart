import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:postgres/postgres.dart';
import 'package:path/path.dart' as p;
import '../database/database_helper.dart';
import 'package:sqflite/sqflite.dart'; 

class SyncService {
  // Singleton
  static final SyncService instance = SyncService._init();
  SyncService._init();

  // Configuration (From User)
  static const String _host = 'switchback.proxy.rlwy.net';
  static const int _port = 20266;
  static const String _databaseName = 'railway';
  static const String _username = 'postgres';
  static const String _password = 'bqcTJxNXLgwOftDoarrtmjmjYWurEIEh';

  // Constants
  static const String _localImagesPath = r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images';

  bool _isSyncing = false;
  Timer? _timer;
  
  // Public stream for UI to listen to sync status/errors
  final _statusController = StreamController<String>.broadcast();
  Stream<String> get statusStream => _statusController.stream;

  // Start the background timer
  void startSyncTimer() {
    _timer?.cancel();
    // Run immediately
    syncNow(); 
    // Then every 15 minutes
    _timer = Timer.periodic(const Duration(minutes: 15), (timer) {
      syncNow();
    });
    print("🔄 Sync Timer Started (15 min interval)");
  }

  void stop() {
    _timer?.cancel();
  }

  // Main Sync Method
  Future<void> syncNow() async {
    if (_isSyncing) {
      _statusController.add("Sync already in progress...");
      return;
    }
    
    _isSyncing = true;
    _statusController.add("Starting Cloud Sync...");
    print("☁️ Starting Cloud Sync...");

    Connection? conn;
    try {
      // 1. Connect to Postgres
      conn = await Connection.open(
        Endpoint(
          host: _host,
          database: _databaseName,
          username: _username,
          password: _password,
          port: _port,
        ),
        settings: ConnectionSettings(sslMode: SslMode.disable),
      );
      
      _statusController.add("Connected to Cloud DB. Downloading Data...");
      print("✅ Connected to Cloud Database!");

      final dbHelper = DatabaseHelper.instance;

      // 2. Fetch Remote Data & Upsert Local
      await _syncTable(conn, dbHelper, 'Sellers', 'sellerid', {
        'sellerid': 'SellerID',
        'telegramid': 'TelegramID',
        'username': 'UserName',
        'storename': 'StoreName',
        'createdat': 'CreatedAt',
        'status': 'Status',
        'imagepath': 'ImagePath'
      });
      
      await _syncTable(conn, dbHelper, 'Categories', 'categoryid', {
        'categoryid': 'CategoryID',
        'sellerid': 'SellerID',
        'name': 'Name',
        'orderindex': 'OrderIndex',
        'imagepath': 'ImagePath'
      });
      
      await _syncTable(conn, dbHelper, 'Products', 'productid', {
         'productid': 'ProductID',
         'sellerid': 'SellerID',
         'categoryid': 'CategoryID',
         'name': 'Name',
         'description': 'Description',
         'price': 'Price',
         'wholesaleprice': 'WholesalePrice',
         'quantity': 'Quantity',
         'imagepath': 'ImagePath',
         'status': 'Status'
      });
      
       // Users (Buyers)
      await _syncTable(conn, dbHelper, 'Users', 'userid', {
         'userid': 'UserID',
         'telegramid': 'TelegramID',
         'username': 'UserName',
         'usertype': 'UserType',
         'phonenumber': 'PhoneNumber',
         'fullname': 'FullName',
         'createdat': 'CreatedAt'
      });
      
      await _syncTable(conn, dbHelper, 'Orders', 'orderid', {
         'orderid': 'OrderID',
         'buyerid': 'BuyerID',
         'sellerid': 'SellerID',
         'total': 'Total',
         'status': 'Status',
         'createdat': 'CreatedAt',
         'deliveryaddress': 'DeliveryAddress',
         'notes': 'Notes',
         'paymentmethod': 'PaymentMethod',
         'fullypaid': 'FullyPaid'
      });
      
      await _syncTable(conn, dbHelper, 'OrderItems', 'orderitemid', {
         'orderitemid': 'OrderItemID',
         'orderid': 'OrderID',
         'productid': 'ProductID',
         'quantity': 'Quantity',
         'price': 'Price'
      });
      
      // 3. Sync Images
      await _syncImages(conn);

      _statusController.add("Sync Completed Successfully!");
      print("🎉 Cloud Sync Completed Successfully!");
      
    } catch (e) {
      _statusController.add("Sync Failed: $e");
      print("❌ Cloud Sync Failed: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  Future<void> _syncImages(Connection conn) async {
    try {
      _statusController.add("Checking Image Storage...");
      print("🖼️ Starting Image Sync...");
      
      // Ensure Table Exists
      try {
        await conn.execute("CREATE TABLE IF NOT EXISTS ImageStorage (FileName TEXT PRIMARY KEY, FileData BYTEA, UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");
      } catch (e) {
         print("⚠️ Table Creation Warning: $e");
         // It might exist, proceed.
      }
      
      final imgDir = Directory(_localImagesPath);
      if (!await imgDir.exists()) await imgDir.create(recursive: true);
      
      // A. Upload: Local -> Cloud
      final localFiles = imgDir.listSync().whereType<File>().toList();
      print("  Local Files Found: ${localFiles.length}");
      _statusController.add("Found ${localFiles.length} local images.");
      
      int uploadedCount = 0;
      for (var file in localFiles) {
        final fileName = p.basename(file.path);
        
        try {
           // efficient check
           final check = await conn.execute(Sql.named('SELECT 1 FROM ImageStorage WHERE FileName = @name'), parameters: {'name': fileName});
           
           if (check.isEmpty) {
              _statusController.add("Uploading $fileName...");
              final bytes = await file.readAsBytes();
              await conn.execute(
                Sql.named('INSERT INTO ImageStorage (FileName, FileData) VALUES (@name, @data)'), 
                parameters: {
                  'name': fileName, 
                  'data': TypedValue(Type.byteArray, bytes)
                }
              );
              uploadedCount++;
              print("  ✅ Uploaded $fileName");
           }
        } catch (e) {
           print("  ❌ Failed to upload $fileName: $e");
           _statusController.add("Error uploading $fileName. Skipping.");
        }
      }
      if (uploadedCount > 0) _statusController.add("Uploaded $uploadedCount images.");
      
      // B. Download: Cloud -> Local
      _statusController.add("Checking Cloud Images...");
      final cloudFilesResult = await conn.execute('SELECT FileName FROM ImageStorage');
      print("  Cloud Files Found: ${cloudFilesResult.length}");
      
      int downloadedCount = 0;
      for (var row in cloudFilesResult) {
        final cloudName = row[0] as String;
        final localFile = File(p.join(imgDir.path, cloudName));
        
        if (!await localFile.exists()) {
           try {
             _statusController.add("Downloading $cloudName...");
             final dataResult = await conn.execute(
               Sql.named('SELECT FileData FROM ImageStorage WHERE FileName = @name'),
               parameters: {'name': cloudName}
             );
             
             if (dataResult.isNotEmpty) {
               final binaryData = dataResult.first[0];
               if (binaryData != null) {
                 await localFile.writeAsBytes(binaryData as List<int>);
                 downloadedCount++;
                 print("  ✅ Downloaded $cloudName");
               }
             }
           } catch (e) {
              print("  ❌ Failed to download $cloudName: $e");
           }
        }
      }
      if (downloadedCount > 0) _statusController.add("Downloaded $downloadedCount images.");
      
      print("✅ Image Sync Done! Up: $uploadedCount, Down: $downloadedCount");
      
    } catch (e) {
      print("❌ Image Sync Critical Failure: $e");
      _statusController.add("Image Sync Critical Error: $e");
    }
  }

  Future<void> _syncTable(
      Connection conn, 
      DatabaseHelper dbHelper, 
      String pgTableName, 
      String pgPrimaryKey, 
      Map<String, String> colMap
  ) async {
     try {
       print("⬇️ Pulling $pgTableName...");
       final result = await conn.execute('SELECT * FROM $pgTableName');
       
       if (result.isEmpty) return;
       
       final db = await dbHelper.database;
       final batch = db.batch();

       for (final row in result) {
          final localMap = <String, dynamic>{};
          final pgMap = row.toColumnMap();
          
          colMap.forEach((pgKey, localKey) {
             if (pgMap.containsKey(pgKey)) {
                var val = pgMap[pgKey];
                if (val is DateTime) {
                  val = val.toIso8601String();
                }
                localMap[localKey] = val;
             }
          });
          
          batch.insert(pgTableName, localMap, conflictAlgorithm: ConflictAlgorithm.replace);
       }
       
       await batch.commit(noResult: true);
       
     } catch (e) {
       print("  ⚠️ Failed to sync table $pgTableName: $e");
     }
  }
}
