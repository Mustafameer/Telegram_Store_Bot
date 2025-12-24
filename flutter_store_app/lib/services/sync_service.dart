import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:postgres/postgres.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart'; 
import 'package:path_provider/path_provider.dart';
import '../database/database_helper.dart';
import 'server_config.dart';

class SyncService {
  // Singleton
  static final SyncService instance = SyncService._init();
  SyncService._init();


  // Constants
  Future<String> get _localImagesPath async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
       // Check parent directory first (Bot Integration)
       final parentDir = Directory(p.join(Directory.current.parent.path, 'data', 'Images'));
       if (await parentDir.exists()) {
          print("📂 Found Bot Images Directory: ${parentDir.path}");
          return parentDir.path;
       }
       return p.join(Directory.current.path, 'data', 'Images');
    } else {
       final docs = await getApplicationDocumentsDirectory();
       return p.join(docs.path, 'Images');
    }
  }

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
    _isSyncing = true;
    _statusController.add("جاري بدء المزامنة (رفع البيانات) - v2...");
    print("☁️ Starting Push Sync (v2 Fixed)...");

    Connection? conn;
    try {
      conn = await _connectToPostgres();
      await _ensureRemoteSchema(conn);
      final dbHelper = DatabaseHelper.instance;

      // 1. PROCESS DELETIONS
      _statusController.add("جاري معالجة المحذوفات...");
      await _processDeletions(conn, dbHelper);

      // 2. PUSH INVENTORY
      _statusController.add("جاري رفع المنتجات...");
      await _pushAllInventory(conn, dbHelper);

      // 3. PUSH ORDERS
      _statusController.add("جاري رفع الطلبات...");
      await _pushAllOrders(conn, dbHelper);
      
      // 4. PUSH MESSAGES
      _statusController.add("جاري رفع الرسائل...");
      await _pushAllMessages(conn, dbHelper);
      
      // 5. Sync Images
      await _syncImages(conn, uploadOnly: true);

      _statusController.add("✅ تمت المزامنة بنجاح");
      print("🎉 Push Sync Completed!");
      
    } catch (e) {
      _statusController.add("❌ فشل المزامنة: $e");
      print("❌ Sync Failed: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  // Handle Queued Deletions
  Future<void> _processDeletions(Connection conn, DatabaseHelper dbHelper) async {
    try {
      final deletions = await dbHelper.getDeletedItems();
      if (deletions.isEmpty) return;
      
      final processedIds = <int>[];

      for (var row in deletions) {
        final id = row['ID'] as int;
        final table = row['TableName'] as String;
        final remoteId = row['RemoteID'] as int;
        
        try {
          // Map local table name to remote table name/key if different
          String remoteTable = table; 
          String remoteKey = 'ID'; // Default fallback
          
          if (table == 'Orders') {
            remoteTable = 'Orders';
            remoteKey = 'OrderID';
            // Also delete Items & Messages
             await conn.execute(Sql.named('DELETE FROM OrderItems WHERE OrderID = @id'), parameters: {'id': remoteId});
             await conn.execute(Sql.named('DELETE FROM Messages WHERE OrderID = @id'), parameters: {'id': remoteId});
          } else if (table == 'Products') {
             remoteTable = 'Products';
             remoteKey = 'ProductID'; // Remote is ProductID
          } else if (table == 'OrderItems') {
             remoteTable = 'OrderItems';
             remoteKey = 'orderitemid'; // Remote is orderitemid
          }
          
          final result = await conn.execute(
            Sql.named('DELETE FROM $remoteTable WHERE $remoteKey = @id'), 
            parameters: {'id': remoteId}
          );
          
          processedIds.add(id);
          print("🗑️ Remote Deleted: $table #$remoteId");
          
        } catch (e) {
          print("⚠️ Failed to delete remote $table #$remoteId: $e");
        }
      }
      
      if (processedIds.isNotEmpty) {
        await dbHelper.clearDeletedItems(processedIds);
      }
      
    } catch (e) {
      print("⚠️ Process Deletions Failed: $e");
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
    print("🚀 SYNC SERVICE VERSION: 3.0 (Lowercase Keys Fix)");
    _statusController.add("جاري بدء المزامنة التلقائية (سحب)...");

    Connection? conn;
    try {
      conn = await _connectToPostgres();
      await _ensureRemoteSchema(conn);
      final dbHelper = DatabaseHelper.instance;
      
      // 0. Process any pending local deletions first!
      await _processDeletions(conn, dbHelper);

      // PULL ALL with PRUNE (Delete local if deleted in cloud)
      await _pullInventory(conn, dbHelper, prune: true);
      // DO NOT PRUNE ORDERS - Risk of deleting local unsynced orders!
      await _pullOrders(conn, dbHelper, prune: false);
      
      // Sync Images with Prune (Delete local files if not in cloud)
      // Upload: False (Trust Cloud as Master on Startup)
      await _syncImages(conn, uploadOnly: false, pruneLocal: true); 

      print("🎉 Startup Sync Completed!");
      _statusController.add("تمت المزامنة بنجاح ✅");
      
    } catch (e) {
      print("❌ Startup Sync Failed: $e");
      _statusController.add("فشل المزامنة التلقائية: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  Future<Connection> _connectToPostgres() async {
    final config = await ServerConfig.getConfig();
    
    return await Connection.open(
        Endpoint(
          host: config['host'],
          database: config['database'],
          username: config['username'],
          password: config['password'],
          port: config['port'],
        ),
        settings: ConnectionSettings(
           sslMode: config['ssl'] == true ? SslMode.require : SslMode.disable,
        ),
      );
  }



  Future<void> _pushAllInventory(Connection conn, DatabaseHelper dbHelper) async {
      // Sellers
      await _pushTable(conn, dbHelper, 'Sellers', 'Sellers', 'sellerid', {
        'SellerID': 'sellerid',
        'TelegramID': 'telegramid',
        'UserName': 'username',
        'StoreName': 'storename',
        'CreatedAt': 'createdat',
        'Status': 'status',
        'ImagePath': 'imagepath'
      });
      // Categories
      await _pushTable(conn, dbHelper, 'Categories', 'Categories', 'categoryid', {
        'CategoryID': 'categoryid',
        'SellerID': 'sellerid',
        'Name': 'name',
        'OrderIndex': 'orderindex',
        'ImagePath': 'imagepath'
      });
      // Products
      await _pushTable(conn, dbHelper, 'Products', 'Products', 'productid', {
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

  Future<void> _pushAllOrders(Connection conn, DatabaseHelper dbHelper) async {
      // Orders
      await _pushTable(conn, dbHelper, 'Orders', 'Orders', 'orderid', {
        'OrderID': 'orderid',
        'BuyerID': 'buyerid',
        'SellerID': 'sellerid',
        'Total': 'total', 
        'Status': 'status',
        'CreatedAt': 'createdat', // Corrected from OrderDate/orderdate
        'DeliveryAddress': 'deliveryaddress',
        'Notes': 'notes',
        'PaymentMethod': 'paymentmethod',
        'FullyPaid': 'fullypaid'
      });

      // OrderItems
      try {
          await _pushTable(conn, dbHelper, 'OrderItems', 'OrderItems', 'orderitemid', {
            'OrderItemID': 'orderitemid',
            'OrderID': 'orderid',
            'ProductID': 'productid',
            'Quantity': 'quantity',
            'Price': 'price'
          });
      } catch (e) {
          print("❌ CRITICAL ERROR SYNCING ORDER ITEMS: $e");
          _statusController.add("فشل مزامنة عناصر الطلب: $e");
      }
  }

  // Full Migration (Local -> Remote)
  Future<void> uploadFullDatabase() async {
    // ... (rest of method seems fine or we assume it calls _pushAll* methods)
    if (_isSyncing) return;
    _isSyncing = true;
    _statusController.add("Starting Full Migration...");
    
    Connection? conn;
    try {
      conn = await _connectToPostgres();
      await _ensureRemoteSchema(conn);
      final dbHelper = DatabaseHelper.instance;

      _statusController.add("Migrating Inventory...");
      await _pushAllInventory(conn, dbHelper);

      _statusController.add("Migrating Orders...");
      await _pushAllOrders(conn, dbHelper);

      _statusController.add("Migrating Images...");
      await _syncImages(conn, uploadOnly: true);

      _statusController.add("Resetting Sequences...");
      await _resetSequences(conn);

      _statusController.add("Migration Complete! ✅");
    } catch (e) {
      _statusController.add("Migration Failed: $e");
    } finally {
      await conn?.close();
      _isSyncing = false;
    }
  }

  Future<void> _resetSequences(Connection conn) async {
    try {
      // Reset Serial Sequences to match the highest ID we just inserted
      await conn.execute("SELECT setval('categories_categoryid_seq', COALESCE((SELECT MAX(CategoryID) FROM Categories), 1))");
      await conn.execute("SELECT setval('products_productid_seq', COALESCE((SELECT MAX(ProductID) FROM Products), 1))");
      await conn.execute("SELECT setval('orders_orderid_seq', COALESCE((SELECT MAX(OrderID) FROM Orders), 1))");
      await conn.execute("SELECT setval('orderitems_orderitemid_seq', COALESCE((SELECT MAX(OrderItemID) FROM OrderItems), 1))");
      print("✅ Sequences Reset");
    } catch (e) {
      print("⚠️ Sequence Reset Failed (ignorable if tables empty): $e");
    }
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

  Future<void> _pullOrders(Connection conn, DatabaseHelper dbHelper, {bool prune = false}) async {
       // Users
      await _syncTable(conn, dbHelper, 'Users', 'userid', {
         'userid': 'UserID',
         'telegramid': 'TelegramID',
         'username': 'UserName',
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
      }, prune: prune);
       // Order Items
      await _syncTable(conn, dbHelper, 'OrderItems', 'orderitemid', {
         'orderitemid': 'OrderItemID',
         'orderid': 'OrderID',
         'productid': 'ProductID',
         'quantity': 'Quantity',
         'price': 'Price'
      }, prune: prune);

      // Messages
      await _syncMessages(conn, dbHelper, prune: prune);

      // Credit Sync
      await _syncCredit(conn, dbHelper, prune: prune);
  }

  Future<void> _syncMessages(Connection conn, DatabaseHelper dbHelper, {bool prune = false}) async {
      // Messages
      await _syncTable(conn, dbHelper, 'Messages', 'messageid', {
        'messageid': 'MessageID',
        'orderid': 'OrderID',
        'sellerid': 'SellerID',
        'messagetype': 'MessageType',
        'messagetext': 'MessageText',
        'isread': 'IsRead',
        'createdat': 'CreatedAt'
      }, prune: prune);
  }
  
  Future<void> _syncCredit(Connection conn, DatabaseHelper dbHelper, {bool prune = false}) async {
      // CreditCustomers
      await _syncTable(conn, dbHelper, 'CreditCustomers', 'customerid', {
        'customerid': 'CustomerID',
        'sellerid': 'SellerID',
        'fullname': 'FullName',
        'phonenumber': 'PhoneNumber',
        'createdat': 'CreatedAt'
      }, prune: prune);

       // CustomerCredit
      await _syncTable(conn, dbHelper, 'CustomerCredit', 'creditid', {
        'creditid': 'CreditID',
        'customerid': 'CustomerID',
        'sellerid': 'SellerID',
        'transactiontype': 'TransactionType',
        'amount': 'Amount',
        'description': 'Description',
        'balancebefore': 'BalanceBefore',
        'balanceafter': 'BalanceAfter',
        'transactiondate': 'TransactionDate'
      }, prune: prune);
  }

  Future<void> _pushAllMessages(Connection conn, DatabaseHelper dbHelper) async {
       // Messages
       await _pushTable(conn, dbHelper, 'Messages', 'Messages', 'messageid', {
            'MessageID': 'messageid',
            'OrderID': 'orderid',
            'SellerID': 'sellerid',
            'MessageType': 'messagetype',
            'MessageText': 'messagetext',
            'IsRead': 'isread',
            'CreatedAt': 'createdat'
       });
       
       // Credits
       await _pushTable(conn, dbHelper, 'CreditCustomers', 'CreditCustomers', 'customerid', {
          'CustomerID': 'customerid',
          'SellerID': 'sellerid',
          'FullName': 'fullname',
          'PhoneNumber': 'phonenumber',
          'CreatedAt': 'createdat'
       });
       await _pushTable(conn, dbHelper, 'CustomerCredit', 'CustomerCredit', 'creditid', {
          'CreditID': 'creditid',
          'CustomerID': 'customerid',
          'SellerID': 'sellerid',
          'TransactionType': 'transactiontype',
          'Amount': 'amount',
          'Description': 'description',
          'BalanceBefore': 'balancebefore',
          'BalanceAfter': 'balanceafter',
          'TransactionDate': 'transactiondate'
       });
  }

  Future<void> _syncImages(Connection conn, {bool uploadOnly = false, bool pruneLocal = false}) async {
    try {
      _statusController.add("جاري فحص تخزين الصور...");
      print("🖼️ Starting Image Sync with Garbage Collection...");

      // 1. Get All Active Images from Local DB
      final db = await DatabaseHelper.instance.database;
      final Set<String> activeImages = {};
      
      final products = await db.query('Products', columns: ['ImagePath']);
      final sellers = await db.query('Sellers', columns: ['ImagePath']);
      final categories = await db.query('Categories', columns: ['ImagePath']);
      
      for (var row in [...products, ...sellers, ...categories]) {
          final path = row['ImagePath'] as String?;
          if (path != null && path.isNotEmpty) {
              activeImages.add(p.basename(path));
          }
      }
      print("📊 Active Images Count: ${activeImages.length}");
      
      // Ensure Table Exists
      try {
        await conn.execute("CREATE TABLE IF NOT EXISTS ImageStorage (FileName TEXT PRIMARY KEY, FileData BYTEA, UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");
      } catch (e) { }

      final imgDir = Directory(await _localImagesPath);
      if (!await imgDir.exists()) await imgDir.create(recursive: true);
      
      final localFiles = imgDir.listSync().whereType<File>().toList();
      
      // 2. Local Prune (Delete files not in activeImages)
      int prunedLocal = 0;
      for (var file in localFiles) {
          final name = p.basename(file.path);
          if (!activeImages.contains(name)) {
              try {
                  await file.delete();
                  prunedLocal++;
                  print("🗑️ GC: Deleted local orphan: $name");
              } catch (e) {
                  print("⚠️ GC: Failed to delete local orphan $name: $e");
              }
          }
      }
      if (prunedLocal > 0) _statusController.add("تم تنظيف $prunedLocal صور محلية غير مستخدمة.");
      
      // 3. Cloud Prune & Download
      if (!uploadOnly) {
          final cloudFilesResult = await conn.execute('SELECT FileName FROM ImageStorage');
          int prunedCloud = 0;
          
          for (var row in cloudFilesResult) {
             final cloudName = row[0] as String;
             
             if (!activeImages.contains(cloudName)) {
                 // Delete Orphan from Cloud
                 try {
                     await conn.execute(Sql.named('DELETE FROM ImageStorage WHERE FileName = @name'), parameters: {'name': cloudName});
                     prunedCloud++;
                     print("☁️🗑️ GC: Deleted cloud orphan: $cloudName");
                 } catch (e) { print("⚠️ GC: Cloud delete failed: $e"); }
             } else {
                 // It is active! Check if we need to download it
                 final localFile = File(p.join(imgDir.path, cloudName));
                 if (!await localFile.exists()) {
                     try {
                         _statusController.add("جاري تنزيل الصورة $cloudName...");
                         final dataResult = await conn.execute(
                           Sql.named('SELECT FileData FROM ImageStorage WHERE FileName = @name'),
                           parameters: {'name': cloudName}
                         );
                         if (dataResult.isNotEmpty && dataResult.first[0] != null) {
                             // Cast based on driver version/result type (binary)
                             var fileData = dataResult.first[0];
                             if (fileData is Uint8List) {
                                await localFile.writeAsBytes(fileData);
                             } else if (fileData is List<int>) {
                                await localFile.writeAsBytes(List<int>.from(fileData));
                             }
                             print("✅ Downloaded $cloudName");
                         }
                     } catch (e) { print("Download error $cloudName: $e"); }
                 }
             }
          }
          if (prunedCloud > 0) _statusController.add("تم تنظيف $prunedCloud صور سحابية غير مستخدمة.");
      }
      
      // 4. Upload Missing Active Images
      int uploadedCount = 0;
      final remainingLocalFiles = imgDir.listSync().whereType<File>().toList();
      
      for (var file in remainingLocalFiles) {
          final fileName = p.basename(file.path);
          if (!activeImages.contains(fileName)) continue; 
          
          try {
             // Efficient check before upload?
             final check = await conn.execute(Sql.named('SELECT 1 FROM ImageStorage WHERE FileName = @name'), parameters: {'name': fileName});
             if (check.isEmpty) {
                 _statusController.add("جاري رفع $fileName...");
                 final bytes = await file.readAsBytes();
                 await conn.execute(
                   Sql.named('INSERT INTO ImageStorage (FileName, FileData) VALUES (@name, @data)'), 
                   parameters: {'name': fileName, 'data': TypedValue(Type.byteArray, bytes)}
                 );
                 uploadedCount++;
             }
          } catch (e) { print("Upload error $fileName: $e"); }
      }
      if (uploadedCount > 0) _statusController.add("تم رفع $uploadedCount صور.");

      print("✅ Image Sync & GC Done!");
      
    } catch (e) {
      print("❌ Image Sync Critical Failure: $e");
      _statusController.add("خطأ حرج في مزامنة الصور: $e");
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
        // Quote identifiers to be safe
        final quotedKeys = keys.map((k) => '"$k"').toList();
        final updateSet = keys.map((k) => '"$k" = EXCLUDED."$k"').join(', ');
        
        // Ensure Primary Key is also quoted if we use it in conflict
        final quotedPK = '"$pgPrimaryKey"'; 
        
        final sql = 'INSERT INTO $pgTableName (${quotedKeys.join(', ')}) VALUES (${values.join(', ')}) '
                    'ON CONFLICT ($quotedPK) DO UPDATE SET $updateSet';
        
        // DEBUG LOGGING
        if (localTableName == 'OrderItems') {
           print("🛠️ DEBUG SQL: $sql");
           print("🛠️ DEBUG KEYS: $keys");
        }
        
        await conn.execute(Sql.named(sql), parameters: pgMap);
      }
      print("  ✅ Pushed ${localData.length} rows from $localTableName");
      
    } catch (e) {
      print("  ⚠️ Failed to push table $localTableName: $e");
      _statusController.add("خطأ في رفع ($localTableName): $e");
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
       
       // SAFETY GUARD: Never prune OrderItems or Orders automatically during sync
       // This prevents local data loss if cloud is empty/lagging.
       if (prune && (pgTableName == 'OrderItems' || pgTableName == 'Orders')) {
          print("🛡️ SAFETY: Disabled Pruning for $pgTableName to protect local data.");
          prune = false;
       }

       final result = await conn.execute('SELECT * FROM $pgTableName');
       final imagesPath = await _localImagesPath; // Preload path
       
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
               
               final db = await dbHelper.database;
               
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
                   val = p.join(imagesPath, fileName);
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


  Future<void> _ensureRemoteSchema(Connection conn) async {
    print("🛠️ Verifying Remote Schema...");
    try {
      // 1. Sellers
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Sellers (
          SellerID SERIAL PRIMARY KEY,
          TelegramID BIGINT UNIQUE,
          UserName TEXT,
          StoreName TEXT,
          CreatedAt TEXT,
          Status TEXT DEFAULT 'active',
          ImagePath TEXT
        )
      ''');

      // 2. Categories
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Categories (
          CategoryID SERIAL PRIMARY KEY,
          SellerID INTEGER,
          Name TEXT,
          OrderIndex INTEGER DEFAULT 0,
          ImagePath TEXT
        )
      ''');

      // 3. Products
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Products (
          ProductID SERIAL PRIMARY KEY,
          SellerID INTEGER,
          CategoryID INTEGER,
          Name TEXT,
          Description TEXT,
          Price NUMERIC,
          WholesalePrice NUMERIC,
          Quantity INTEGER,
          ImagePath TEXT,
          Status TEXT DEFAULT 'active'
        )
      ''');

      // 4. Users (For Buyers)
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Users (
          UserID SERIAL PRIMARY KEY,
          TelegramID BIGINT UNIQUE,
          UserName TEXT,
          PhoneNumber TEXT,
          FullName TEXT,
          CreatedAt TEXT,
          UserType TEXT
        )
      ''');

      // 5. Orders
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Orders (
          OrderID SERIAL PRIMARY KEY,
          BuyerID INTEGER,
          SellerID INTEGER,
          Total NUMERIC,
          Status TEXT,
          CreatedAt TEXT,
          DeliveryAddress TEXT,
          Notes TEXT,
          PaymentMethod TEXT,
          FullyPaid INTEGER DEFAULT 0
        )
      ''');

      // 6. OrderItems
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS OrderItems (
          OrderItemID SERIAL PRIMARY KEY,
          OrderID INTEGER,
          ProductID INTEGER,
          Quantity INTEGER,
          Price NUMERIC
        )
      ''');

      // 7. Credits
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS CreditCustomers (
          CustomerID SERIAL PRIMARY KEY,
          SellerID INTEGER,
          FullName TEXT,
          PhoneNumber TEXT,
          CreatedAt TEXT
        )
      ''');
       await conn.execute('''
        CREATE TABLE IF NOT EXISTS CustomerCredit (
          CreditID SERIAL PRIMARY KEY,
          CustomerID INTEGER,
          SellerID INTEGER,
          TransactionType TEXT,
          Amount NUMERIC,
          Description TEXT,
          BalanceBefore NUMERIC,
          BalanceAfter NUMERIC,
          TransactionDate TEXT
        )
      ''');

      // 8. Messages
      await conn.execute('''
        CREATE TABLE IF NOT EXISTS Messages (
          MessageID SERIAL PRIMARY KEY,
          OrderID INTEGER,
          SellerID INTEGER,
          MessageType TEXT,
          MessageText TEXT,
          IsRead INTEGER DEFAULT 0,
          CreatedAt TEXT
        )
      ''');

      // 9. ImageStorage
      await conn.execute("CREATE TABLE IF NOT EXISTS ImageStorage (FileName TEXT PRIMARY KEY, FileData BYTEA, UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");

      print("✅ Remote Schema Verified");
    } catch (e) {
      print("⚠️ Remote Schema Check Warn: $e");
      _statusController.add("Remote Schema Check: $e");
    }
  }
}
