/// Initialize PostgreSQL database with schema
/// This script creates all necessary tables if they don't exist

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:postgres/postgres.dart' as postgres;

Future<void> main() async {
  // Load .env file
  await dotenv.load(fileName: '.env');

  // Get connection parameters from .env
  final host = dotenv.env['DB_HOST'] ?? 'switchback.proxy.rlwy.net';
  final port = int.tryParse(dotenv.env['DB_PORT'] ?? '20266') ?? 20266;
  final database = dotenv.env['DB_NAME'] ?? 'railway';
  final username = dotenv.env['DB_USER'] ?? 'postgres';
  final password = dotenv.env['DB_PASSWORD'] ?? '';
  final useSSL = (dotenv.env['DB_SSL'] ?? 'true').toLowerCase() == 'true';

  print('🔧 Initializing PostgreSQL Database...');

  try {
    // Connect to PostgreSQL
    final connection = await postgres.Connection.open(
      postgres.Endpoint(
        host: host,
        port: port,
        database: database,
        username: username,
        password: password,
      ),
      settings: postgres.ConnectionSettings(
        sslMode: useSSL ? postgres.SslMode.require : postgres.SslMode.disable,
      ),
    );

    print('✅ Connected to PostgreSQL');

    // Create schema
    print('\n📝 Creating tables...');

    // 1. Sellers table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Sellers" (
        "SellerID" SERIAL PRIMARY KEY,
        "TelegramID" BIGINT UNIQUE,
        "UserName" VARCHAR(255),
        "StoreName" VARCHAR(255),
        "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        "Status" VARCHAR(50) DEFAULT 'active',
        "ImagePath" TEXT,
        "RequireCustomerRegistration" INTEGER DEFAULT 0
      )
    ''');
    print('   ✅ Sellers table created');

    // 2. Categories table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Categories" (
        "CategoryID" SERIAL PRIMARY KEY,
        "SellerID" INTEGER,
        "Name" VARCHAR(255),
        "OrderIndex" INTEGER DEFAULT 0,
        "ImagePath" TEXT
      )
    ''');
    print('   ✅ Categories table created');

    // 3. Products table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Products" (
        "ProductID" SERIAL PRIMARY KEY,
        "SellerID" INTEGER,
        "CategoryID" INTEGER,
        "Name" VARCHAR(255),
        "Description" TEXT,
        "Price" NUMERIC(10,2),
        "WholesalePrice" NUMERIC(10,2),
        "Quantity" INTEGER,
        "ImagePath" TEXT,
        "Status" VARCHAR(50) DEFAULT 'active'
      )
    ''');
    print('   ✅ Products table created');

    // 4. Users table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Users" (
        "UserID" SERIAL PRIMARY KEY,
        "TelegramID" BIGINT UNIQUE,
        "UserName" VARCHAR(255),
        "PhoneNumber" VARCHAR(20),
        "FullName" VARCHAR(255),
        "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        "UserType" VARCHAR(50)
      )
    ''');
    print('   ✅ Users table created');

    // 5. Orders table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Orders" (
        "OrderID" SERIAL PRIMARY KEY,
        "BuyerID" INTEGER,
        "SellerID" INTEGER,
        "Total" NUMERIC(10,2),
        "Status" VARCHAR(50),
        "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        "DeliveryAddress" TEXT,
        "Notes" TEXT,
        "PaymentMethod" VARCHAR(50),
        "FullyPaid" INTEGER DEFAULT 0
      )
    ''');
    print('   ✅ Orders table created');

    // 6. OrderItems table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "OrderItems" (
        "OrderItemID" SERIAL PRIMARY KEY,
        "OrderID" INTEGER,
        "ProductID" INTEGER,
        "Quantity" INTEGER,
        "Price" NUMERIC(10,2)
      )
    ''');
    print('   ✅ OrderItems table created');

    // 7. Messages table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "Messages" (
        "MessageID" SERIAL PRIMARY KEY,
        "OrderID" INTEGER,
        "SellerID" INTEGER,
        "MessageType" VARCHAR(50),
        "MessageText" TEXT,
        "IsRead" INTEGER DEFAULT 0,
        "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    ''');
    print('   ✅ Messages table created');

    // 8. CreditCustomers table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "CreditCustomers" (
        "CustomerID" SERIAL PRIMARY KEY,
        "SellerID" INTEGER,
        "FullName" VARCHAR(255),
        "PhoneNumber" VARCHAR(20),
        "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    ''');
    print('   ✅ CreditCustomers table created');

    // 9. CustomerCredit table
    await connection.execute('''
      CREATE TABLE IF NOT EXISTS "CustomerCredit" (
        "CreditID" SERIAL PRIMARY KEY,
        "CustomerID" INTEGER,
        "SellerID" INTEGER,
        "TransactionType" VARCHAR(50),
        "Amount" NUMERIC(10,2),
        "Description" TEXT,
        "BalanceBefore" NUMERIC(10,2),
        "BalanceAfter" NUMERIC(10,2),
        "TransactionDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    ''');
    print('   ✅ CustomerCredit table created');

    // Insert sample Seller data
    print('\n📊 Inserting sample data...');
    
    // Check if seller already exists
    final existing = await connection.execute(
      'SELECT COUNT(*) as count FROM "Sellers" WHERE "TelegramID" = \$1',
      parameters: [1041977029]
    );

    if (existing.first[0] as int == 0) {
      await connection.execute('''
        INSERT INTO "Sellers" ("TelegramID", "UserName", "StoreName", "Status", "RequireCustomerRegistration")
        VALUES (\$1, \$2, \$3, \$4, \$5)
      ''', parameters: [1041977029, 'testuser', 'Test Store', 'active', 0]);
      print('   ✅ Sample seller inserted');

      // Get the seller ID
      final sellerResult = await connection.execute(
        'SELECT "SellerID" FROM "Sellers" WHERE "TelegramID" = \$1',
        parameters: [1041977029]
      );
      
      final sellerId = sellerResult.first[0] as int;

      // Insert sample category
      await connection.execute('''
        INSERT INTO "Categories" ("SellerID", "Name", "OrderIndex")
        VALUES (\$1, \$2, \$3)
      ''', parameters: [sellerId, 'Sample Category', 0]);
      print('   ✅ Sample category inserted');

      // Insert sample product
      await connection.execute('''
        INSERT INTO "Products" ("SellerID", "CategoryID", "Name", "Price", "Quantity", "Status")
        VALUES (\$1, \$2, \$3, \$4, \$5, \$6)
      ''', parameters: [sellerId, 1, 'Sample Product', 100.00, 10, 'active']);
      print('   ✅ Sample product inserted');
    } else {
      print('   ℹ️ Seller already exists, skipping sample data');
    }

    await connection.close();
    print('\n✅ Database initialization completed successfully!');
  } catch (e) {
    print('❌ Error: $e');
  }
}
