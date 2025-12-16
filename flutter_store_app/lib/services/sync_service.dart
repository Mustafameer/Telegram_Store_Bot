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

  // Startup Sync: Pull All (Mirror Cloud State - Handles Deletions)
  Future<void> syncStartup() async {
    if (_isSyncing) {
       print("⚠️ Startup Sync skipped: Sync already in progress");
       return;
    }
    
    _isSyncing = true; 
    print("☁️ Starting Startup Sync (Pull All & Prune)...");

    Connection? conn;
    try {
      conn = await _connectToPostgres();
      final dbHelper = DatabaseHelper.instance;

      // PULL ALL with PRUNE (Delete local if deleted in cloud)
      await _pullInventory(conn, dbHelper, prune: true);
      await _pullOrders(conn, dbHelper);
      
      // Sync Images with Prune (Delete local files if not in cloud)
      // Upload: False (Trust Cloud as Master on Startup)
      await _syncImages(conn, uploadOnly: false, pruneLocal: true); 

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

  Future<void> _pullInventory(Connection conn, DatabaseHelper dbHelper, {bool prune = false}) async {
       // Sellers
      await _syncTable(conn, dbHelper, 'Sellers', 'sellerid', {
        'sellerid': 'SellerID',
        'telegramid': 'TelegramID',
        'username': 'UserName',
        'storename': 'StoreName',
        'createdat': 'CreatedAt',
        'status': 'Status',
        'imagepath': 'ImagePath'
      }, prune: prune);
       // Categories
      await _syncTable(conn, dbHelper, 'Categories', 'categoryid', {
        'categoryid': 'CategoryID',
        'sellerid': 'SellerID',
        'name': 'Name',
        'orderindex': 'OrderIndex',
        'imagepath': 'ImagePath'
      }, prune: prune);
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
      }, prune: prune);
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

  Future<void> _syncImages(Connection conn, {bool uploadOnly = false, bool pruneLocal = false}) async {
    try {
      _statusController.add("Checking Image Storage (${uploadOnly ? 'Upload Only' : 'Sync'})...");
      print("🖼️ Starting Image Sync (Prune: $pruneLocal)...");
      
      // Ensure Table Exists
      try {
        await conn.execute("CREATE TABLE IF NOT EXISTS ImageStorage (FileName TEXT PRIMARY KEY, FileData BYTEA, UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");
      } catch (e) {
         // print("⚠️ Table Creation Warning: $e");
      }
      
      final imgDir = Directory(_localImagesPath);
      if (!await imgDir.exists()) await imgDir.create(recursive: true);
      
      final localFiles = imgDir.listSync().whereType<File>().toList();
      
      // A. Upload: Local -> Cloud (Only if NOT uploadOnly=false AND pruneLocal=true, 
      // actually if pruneLocal=true (Startup), we trust cloud, so maybe skip upload? 
      // Safe bet: Upload if it's explicitly strictly new? 
      // User complaint: "Deleted in Cloud returned to Disk". This means we shouldn't download deleted stuff.
      // But complaint "Local deleted stuff stays" requires Prune.
      
      // If uploadOnly is true (Button), we just Upload.
      // If we are in Startup (pruneLocal=true), we probably shouldn't upload indiscriminately if we want to mirror.
      // But let's keep upload logic for now unless it causes issues.
      // Wait, if pruneLocal is TRUE, we are doing a "Download Mirror".
      
      if (!pruneLocal) {
          int uploadedCount = 0;
          for (var file in localFiles) {
            final fileName = p.basename(file.path);
            try {
              final check = await conn.execute(Sql.named('SELECT 1 FROM ImageStorage WHERE FileName = @name'), parameters: {'name': fileName});
              if (check.isEmpty) {
                  _statusController.add("Uploading $fileName...");
                  final bytes = await file.readAsBytes();
                  await conn.execute(
                    Sql.named('INSERT INTO ImageStorage (FileName, FileData) VALUES (@name, @data)'), 
                    parameters: {'name': fileName, 'data': TypedValue(Type.byteArray, bytes)}
                  );
                  uploadedCount++;
              }
            } catch (e) { print("Upload error $fileName: $e"); }
          }
          if (uploadedCount > 0) _statusController.add("Uploaded $uploadedCount images.");
      }
      
      // B. Download / Prune: Cloud -> Local
      if (!uploadOnly) {
        _statusController.add("Checking Cloud Images...");
        final cloudFilesResult = await conn.execute('SELECT FileName FROM ImageStorage');
        final Set<String> cloudFileNames = {};
        
        int downloadedCount = 0;
        int prunedCount = 0;
        
        for (var row in cloudFilesResult) {
          final cloudName = row[0] as String;
          cloudFileNames.add(cloudName);
          final localFile = File(p.join(imgDir.path, cloudName));
          
          if (!await localFile.exists()) {
             try {
               _statusController.add("Downloading $cloudName...");
               final dataResult = await conn.execute(
                 Sql.named('SELECT FileData FROM ImageStorage WHERE FileName = @name'),
                 parameters: {'name': cloudName}
               );
               if (dataResult.isNotEmpty && dataResult.first[0] != null) {
                   await localFile.writeAsBytes(dataResult.first[0] as List<int>);
                   downloadedCount++;
               }
             } catch (e) { print("Download error $cloudName: $e"); }
          }
        }
        
        // PRUNE LOCAL
        if (pruneLocal) {
            for (var file in localFiles) {
                final localName = p.basename(file.path);
                if (!cloudFileNames.contains(localName)) {
                    try {
                        await file.delete();
                        prunedCount++;
                        print("🗑️ Pruned local image: $localName");
                    } catch (e) {
                        print("⚠️ Failed to prune $localName: $e");
                    }
                }
            }
             if (prunedCount > 0) _statusController.add("Pruned $prunedCount obsolete local images.");
        }

        if (downloadedCount > 0) _statusController.add("Downloaded $downloadedCount images.");
      }
      
      print("✅ Image Sync Done!");
      
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
      Map<String, String> colMap,
      {bool prune = false}
  ) async {
     try {
       print("⬇️ Pulling $pgTableName (Prune: $prune)...");
       final result = await conn.execute('SELECT * FROM $pgTableName');
       
       // Handle Pruning (Delete local records not in Cloud)
       if (prune) {
           final localPrimaryKey = colMap[pgPrimaryKey]; 
           if (localPrimaryKey != null) {
               // Get Cloud IDs
               final cloudIds = <String>{}; // Using string for generality
               for (final row in result) {
                   final pgMap = row.toColumnMap();
                   if (pgMap[pgPrimaryKey] != null) {
                       cloudIds.add(pgMap[pgPrimaryKey].toString());
                   }
               }
               
               // Usually we want to map Table Name... simpler to assume 'pgTableName' maps to 'localTableName' = 'pgTableName' 
               // (Except casing, but dbHelper handles that?)
               // dbHelper usually takes table name.
               // Assuming table names match
               final db = await dbHelper.database;
               
               // We need dynamic table name. All my calls use same name (Sellers, Products...)
               // Just be careful with 'OrderItems' -> 'OrderItems'
               
               // Fetch all Local IDs
               final localTable = pgTableName; // Assumption holds for this app
               final localRows = await db.query(localTable, columns: [localPrimaryKey]);
               
               int deletedCount = 0;
               final batchDelete = db.batch();
               
               for (var row in localRows) {
                   final id = row[localPrimaryKey].toString();
                   if (!cloudIds.contains(id)) {
                       batchDelete.delete(localTable, where: '$localPrimaryKey = ?', whereArgs: [row[localPrimaryKey]]);
                       deletedCount++;
                   }
               }
               if (deletedCount > 0) {
                   await batchDelete.commit(noResult: true);
                   print("🗑️ Pruned $deletedCount records from $localTable");
               }
           }
       }
       
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
