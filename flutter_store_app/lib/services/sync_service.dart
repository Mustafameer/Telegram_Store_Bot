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
    // Run immediately (Startup Logic: Pull All)
    syncStartup(); 
    // Then every 15 minutes (Push Inventory + Pull Orders)
    _timer = Timer.periodic(const Duration(minutes: 15), (timer) {
       syncNow();
    });
    print("🔄 Sync Timer Started (15 min interval)");
  }

  void stop() {
    _timer?.cancel();
  }

  // Manual Sync (Button) & Timer: STRICT PUSH (Desktop -> Cloud ONLY)
  Future<void> syncNow() async {
    if (_isSyncing) {
      _statusController.add("Sync already in progress...");
      return;
    }
    
    _isSyncing = true;
    _statusController.add("Starting Sync (Desktop -> Cloud ONLY)...");
    print("☁️ Starting Push Sync...");

    Connection? conn;
    try {
      conn = await _connectToPostgres();
      final dbHelper = DatabaseHelper.instance;

      // 1. PUSH INVENTORY (Local -> Cloud)
      _statusController.add("Pushing Local Inventory...");
      await _pushAllInventory(conn, dbHelper);

      // 2. SKIP Pull Orders (User requested Strict Push)
      // await _pullOrders(conn, dbHelper);
      
      // 3. Sync Images (Upload Only)
      await _syncImages(conn, uploadOnly: true);

      _statusController.add("Push Sync Completed!");
      print("🎉 Push Sync Completed!");
      
    } catch (e) {
      _statusController.add("Sync Failed: $e");
      print("❌ Sync Failed: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  // Startup Sync: Pull Everything (Ensure fresh state)
  Future<void> syncStartup() async {
    if (_isSyncing) {
       print("⚠️ Startup Sync skipped: Sync already in progress");
       return;
    }
    
    _isSyncing = true; 
    print("☁️ Starting Startup Sync (Pull All)...");

    Connection? conn;
    try {
      conn = await _connectToPostgres();
      final dbHelper = DatabaseHelper.instance;

      // PULL ALL (Inventory + Orders)
      await _pullInventory(conn, dbHelper);
      await _pullOrders(conn, dbHelper);
      
      // Bidirectional Image Sync
      await _syncImages(conn, uploadOnly: false); 

      print("🎉 Startup Sync Completed!");
      
    } catch (e) {
      print("❌ Startup Sync Failed: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  Future<Connection> _connectToPostgres() async {
      return await Connection.open(
        Endpoint(
          host: _host,
          database: _databaseName,
          username: _username,
          password: _password,
          port: _port,
        ),
        settings: ConnectionSettings(sslMode: SslMode.disable),
      );
  }

  Future<void> _pushAllInventory(Connection conn, DatabaseHelper dbHelper) async {
      // Sellers
      await _pushTable(conn, dbHelper, 'Sellers', 'Sellers', 'SellerID', {
        'SellerID': 'sellerid',
        'TelegramID': 'telegramid',
        'UserName': 'username',
        'StoreName': 'storename',
        'CreatedAt': 'createdat',
        'Status': 'status',
        'ImagePath': 'imagepath'
      });
      // Categories
      await _pushTable(conn, dbHelper, 'Categories', 'Categories', 'CategoryID', {
        'CategoryID': 'categoryid',
        'SellerID': 'sellerid',
        'Name': 'name',
        'OrderIndex': 'orderindex',
        'ImagePath': 'imagepath'
      });
      // Products
      await _pushTable(conn, dbHelper, 'Products', 'Products', 'ProductID', {
        'ProductID': 'productid',
        'SellerID': 'sellerid',
        'CategoryID': 'categoryid',
        'Name': 'name',
        'Description': 'description',
        'Price': 'price',
        'WholesalePrice': 'wholesaleprice',
        'Quantity': 'quantity',
        'ImagePath': 'imagepath',
        'Status': 'status'
      });
  }

  Future<void> _pullInventory(Connection conn, DatabaseHelper dbHelper) async {
       // Sellers
      await _syncTable(conn, dbHelper, 'Sellers', 'sellerid', {
        'sellerid': 'SellerID',
        'telegramid': 'TelegramID',
        'username': 'UserName',
        'storename': 'StoreName',
        'createdat': 'CreatedAt',
        'status': 'Status',
        'imagepath': 'ImagePath'
      });
       // Categories
      await _syncTable(conn, dbHelper, 'Categories', 'categoryid', {
        'categoryid': 'CategoryID',
        'sellerid': 'SellerID',
        'name': 'Name',
        'orderindex': 'OrderIndex',
        'imagepath': 'ImagePath'
      });
       // Products
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
  }

  Future<void> _pullOrders(Connection conn, DatabaseHelper dbHelper) async {
       // Users
      await _syncTable(conn, dbHelper, 'Users', 'userid', {
         'userid': 'UserID',
         'telegramid': 'TelegramID',
         'username': 'UserName',
         'usertype': 'UserType',
         'phonenumber': 'PhoneNumber',
         'fullname': 'FullName',
         'createdat': 'CreatedAt'
      });
       // Orders
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
       // Order Items
      await _syncTable(conn, dbHelper, 'OrderItems', 'orderitemid', {
         'orderitemid': 'OrderItemID',
         'orderid': 'OrderID',
         'productid': 'ProductID',
         'quantity': 'Quantity',
         'price': 'Price'
      });
  }

  Future<void> _syncImages(Connection conn, {bool uploadOnly = false}) async {
    try {
      _statusController.add("Checking Image Storage (${uploadOnly ? 'Upload Only' : 'Sync'})...");
      print("🖼️ Starting Image Sync (${uploadOnly ? 'Upload Only' : 'Bidirectional'})...");
      
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
      
      // B. Download: Cloud -> Local (SKIP IF UPLOAD ONLY)
      int downloadedCount = 0;
      if (!uploadOnly) {
        _statusController.add("Checking Cloud Images...");
        final cloudFilesResult = await conn.execute('SELECT FileName FROM ImageStorage');
        print("  Cloud Files Found: ${cloudFilesResult.length}");
        
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
      } else {
        print("  ⏩ Skipping Download (Upload Only Mode)");
      }
      
      print("✅ Image Sync Done! Up: $uploadedCount, Down: $downloadedCount");
      
    } catch (e) {
      print("❌ Image Sync Critical Failure: $e");
      _statusController.add("Image Sync Critical Error: $e");
    }
  }

  // PUSH: Local -> Cloud
  Future<void> _pushTable(
      Connection conn, 
      DatabaseHelper dbHelper, 
      String localTableName, 
      String pgTableName,
      String pgPrimaryKey,
      Map<String, String> colMap // key: localCol, value: pgCol
  ) async {
    try {
      print("⬆️ Pushing $localTableName...");
      final db = await dbHelper.database;
      final localData = await db.query(localTableName);
      
      if (localData.isEmpty) return;
      
      for (var row in localData) {
        final pgMap = <String, dynamic>{};
        
        // Map Columns
        colMap.forEach((localKey, pgKey) {
            if (row.containsKey(localKey)) {
              var val = row[localKey];
              // Path Fix: Windows -> Linux
              if (localKey == 'ImagePath' && val != null && val is String) {
                  // Only send relative path or server path?
                  // Server expects: /app/data/Images/filename
                  final fileName = p.basename(val);
                  val = '/app/data/Images/$fileName'; 
              }
              pgMap[pgKey] = val;
            }
        });

        // Build Upsert Query
        final keys = pgMap.keys.toList();
        final values = keys.map((k) => '@$k').toList();
        final updateSet = keys.map((k) => '$k = EXCLUDED.$k').join(', ');
        
        final sql = 'INSERT INTO $pgTableName (${keys.join(', ')}) VALUES (${values.join(', ')}) '
                    'ON CONFLICT ($pgPrimaryKey) DO UPDATE SET $updateSet';
        
        await conn.execute(Sql.named(sql), parameters: pgMap);
      }
      print("  ✅ Pushed ${localData.length} rows from $localTableName");
      
    } catch (e) {
      print("  ⚠️ Failed to push table $localTableName: $e");
      _statusController.add("Push Error ($localTableName): $e");
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
                if (localKey == 'ImagePath' && val != null && val is String) {
                   // Fix for Windows: Postgrest returns Linux paths (/app/data/...)
                   // path.basename on Windows might not split '/' correctly.
                   var normalized = val.replaceAll('/', p.separator).replaceAll('\\', p.separator);
                   final fileName = p.basename(normalized);
                   val = p.join(_localImagesPath, fileName);
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
