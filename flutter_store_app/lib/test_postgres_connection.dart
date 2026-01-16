// Test file to verify PostgreSQL migration
// اختبار للتحقق من نجاح هجرة PostgreSQL

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:postgres/postgres.dart' as postgres;

void main() async {
  print('🧪 Testing PostgreSQL Connection...');
  print('');
  
  try {
    // Load environment variables
    await dotenv.load(fileName: '.env');
    print('✅ .env file loaded');
    print('');
    
    // Check required variables
    final databaseUrl = dotenv.env['DATABASE_URL'];
    if (databaseUrl == null || databaseUrl.isEmpty) {
      print('❌ DATABASE_URL not found in .env');
      print('   Please set DATABASE_URL or individual config options');
      return;
    }
    
    print('📡 DATABASE_URL found');
    print('   First 40 chars: ${databaseUrl.substring(0, 40)}...');
    print('');
    
    // Parse connection string
    print('🔍 Parsing connection string...');
    try {
      Uri uri = Uri.parse(databaseUrl);
      print('✅ URI parsed successfully');
      print('   Host: ${uri.host}');
      print('   Port: ${uri.port}');
      print('   Database: ${uri.path.replaceFirst('/', '')}');
      print('   User: ${uri.userInfo.split(':')[0]}');
      print('   SSL: ${uri.queryParameters['sslmode'] == 'require' ? 'YES' : 'NO'}');
      print('');
    } catch (e) {
      print('❌ Failed to parse URI: $e');
      return;
    }
    
    // Try to connect
    print('🔌 Attempting to connect to PostgreSQL...');
    try {
      final uri = Uri.parse(databaseUrl);
      final username = uri.userInfo.split(':')[0];
      final password = uri.userInfo.split(':')[1];
      final host = uri.host;
      final port = uri.port;
      final database = uri.path.replaceFirst('/', '');
      final useSSL = uri.queryParameters['sslmode'] == 'require';
      
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
      
      print('✅ Connected to PostgreSQL!');
      print('');
      
      // Test query
      print('🔍 Testing database query...');
      try {
        final result = await connection.execute('SELECT 1 as test');
        print('✅ Test query successful');
        print('   Result: ${result.first.toColumnMap()}');
        print('');
      } catch (e) {
        print('❌ Test query failed: $e');
      }
      
      // Close connection
      await connection.close();
      print('✅ Connection closed');
      print('');
      
      print('🎉 All checks passed! PostgreSQL migration is ready.');
      print('');
      print('Next steps:');
      print('1. Make sure .env file is in the project root');
      print('2. Run: flutter pub get');
      print('3. Run: flutter run -d windows');
      
    } catch (e) {
      print('❌ Connection failed: $e');
      print('');
      print('Troubleshooting:');
      print('1. Check if DATABASE_URL is correct');
      print('2. Check if the database server is running');
      print('3. Check internet connection');
      print('4. Try using individual config options instead of DATABASE_URL');
    }
    
  } catch (e) {
    print('❌ Error: $e');
  }
}
