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

  print('🔍 Testing PostgreSQL Connection...');
  print('   Host: $host');
  print('   Port: $port');
  print('   Database: $database');
  print('   User: $username');
  print('   SSL: $useSSL');

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

    print('✅ Connected successfully!');

    // Check if Sellers table exists and has data
    print('\n📊 Checking database tables...');

    // Check Sellers
    try {
      final sellers = await connection.execute('SELECT COUNT(*) as count FROM "Sellers"');
      print('   Sellers count: ${sellers.first[0]}');
    } catch (e) {
      print('   Sellers table error: $e');
    }

    // Check Categories
    try {
      final categories = await connection.execute('SELECT COUNT(*) as count FROM "Categories"');
      print('   Categories count: ${categories.first[0]}');
    } catch (e) {
      print('   Categories table error: $e');
    }

    // Check Products
    try {
      final products = await connection.execute('SELECT COUNT(*) as count FROM "Products"');
      print('   Products count: ${products.first[0]}');
    } catch (e) {
      print('   Products table error: $e');
    }

    // Check Orders
    try {
      final orders = await connection.execute('SELECT COUNT(*) as count FROM "Orders"');
      print('   Orders count: ${orders.first[0]}');
    } catch (e) {
      print('   Orders table error: $e');
    }

    // Get first seller's telegram ID
    try {
      final result = await connection.execute('SELECT "TelegramID", "StoreName" FROM "Sellers" LIMIT 1');
      if (result.isNotEmpty) {
        final row = result.first;
        print('\n👤 First Seller:');
        print('   TelegramID: ${row[0]}');
        print('   StoreName: ${row[1]}');
      } else {
        print('\n⚠️ No sellers found in database!');
      }
    } catch (e) {
      print('   Error fetching sellers: $e');
    }

    await connection.close();
    print('\n✅ Test completed successfully!');
  } catch (e) {
    print('❌ Connection failed: $e');
  }
}
