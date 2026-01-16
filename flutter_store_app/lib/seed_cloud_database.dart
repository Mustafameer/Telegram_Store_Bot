import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:postgres/postgres.dart' as postgres;

/// Script to seed cloud PostgreSQL database with sample data
Future<void> main() async {
  // Load environment variables
  await dotenv.load(fileName: '.env');

  final host = dotenv.env['DB_HOST'] ?? 'switchback.proxy.rlwy.net';
  final port = int.tryParse(dotenv.env['DB_PORT'] ?? '20266') ?? 20266;
  final database = dotenv.env['DB_NAME'] ?? 'railway';
  final username = dotenv.env['DB_USER'] ?? 'postgres';
  final password = dotenv.env['DB_PASSWORD'] ?? '';
  final useSSL = (dotenv.env['DB_SSL'] ?? 'true').toLowerCase() == 'true';

  try {
    print('📡 Connecting to PostgreSQL Cloud Database...');
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

    // Clear existing data (optional)
    print('🗑️ Clearing existing data...');
    await connection.execute('DELETE FROM OrderItems');
    await connection.execute('DELETE FROM Orders');
    await connection.execute('DELETE FROM Carts');
    await connection.execute('DELETE FROM ProductImages');
    await connection.execute('DELETE FROM Products');
    await connection.execute('DELETE FROM Categories');
    await connection.execute('DELETE FROM Users');
    await connection.execute('DELETE FROM Sellers');

    // Insert Seller
    print('📝 Inserting sample seller...');
    final sellerResult = await connection.execute(
      '''INSERT INTO Sellers ("telegramid", "username", "storename", "status", "imagepath", "requirecustomerregistration")
         VALUES (\$1, \$2, \$3, \$4, \$5, \$6)
         RETURNING "sellerid"''',
      parameters: [
        1041977029,              // telegramid
        'seller_user',           // username
        'متجري الرائع',           // storename (Arabic: My Great Store)
        'active',                // status
        'seller.jpg',            // imagepath
        0,                       // requirecustomerregistration
      ],
    );

    final sellerId = sellerResult.first.toColumnMap()['sellerid'] as int;
    print('✅ Seller created: ID=$sellerId');

    // Insert Categories
    print('📝 Inserting sample categories...');
    final cat1Result = await connection.execute(
      '''INSERT INTO Categories ("sellerid", "name", "orderindex", "imagepath")
         VALUES (\$1, \$2, \$3, \$4)
         RETURNING "categoryid"''',
      parameters: [sellerId, 'إلكترونيات', 1, 'electronics.jpg'],
    );
    final cat1Id = cat1Result.first.toColumnMap()['categoryid'] as int;

    final cat2Result = await connection.execute(
      '''INSERT INTO Categories ("sellerid", "name", "orderindex", "imagepath")
         VALUES (\$1, \$2, \$3, \$4)
         RETURNING "categoryid"''',
      parameters: [sellerId, 'ملابس', 2, 'clothing.jpg'],
    );
    final cat2Id = cat2Result.first.toColumnMap()['categoryid'] as int;

    print('✅ Categories created: ID1=$cat1Id, ID2=$cat2Id');

    // Insert Products for Category 1 (Electronics)
    print('📝 Inserting sample products...');
    final prod1Result = await connection.execute(
      '''INSERT INTO Products ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
         VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9)
         RETURNING "productid"''',
      parameters: [
        sellerId,
        cat1Id,
        'هاتف ذكي',
        'هاتف ذكي حديث بمواصفات عالية',
        599.99,
        450.00,
        50,
        'phone.jpg',
        'active',
      ],
    );
    final prod1Id = prod1Result.first.toColumnMap()['productid'] as int;

    final prod2Result = await connection.execute(
      '''INSERT INTO Products ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
         VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9)
         RETURNING "productid"''',
      parameters: [
        sellerId,
        cat1Id,
        'سماعات بلوتوث',
        'سماعات عالية الجودة مع بطارية طويلة الأمد',
        129.99,
        80.00,
        100,
        'headphones.jpg',
        'active',
      ],
    );
    final prod2Id = prod2Result.first.toColumnMap()['productid'] as int;

    // Insert Products for Category 2 (Clothing)
    final prod3Result = await connection.execute(
      '''INSERT INTO Products ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
         VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9)
         RETURNING "productid"''',
      parameters: [
        sellerId,
        cat2Id,
        'تيشيرت أبيض',
        'تيشيرت قطني مريح بألوان مختلفة',
        19.99,
        10.00,
        200,
        'tshirt.jpg',
        'active',
      ],
    );
    final prod3Id = prod3Result.first.toColumnMap()['productid'] as int;

    print('✅ Products created: ID1=$prod1Id, ID2=$prod2Id, ID3=$prod3Id');

    // Insert Product Images
    print('📝 Inserting product images...');
    await connection.execute(
      '''INSERT INTO ProductImages ("productid", "imagepath")
         VALUES (\$1, \$2)''',
      parameters: [prod1Id, 'phone.jpg'],
    );

    await connection.execute(
      '''INSERT INTO ProductImages ("productid", "imagepath")
         VALUES (\$1, \$2)''',
      parameters: [prod2Id, 'headphones.jpg'],
    );

    await connection.execute(
      '''INSERT INTO ProductImages ("productid", "imagepath")
         VALUES (\$1, \$2)''',
      parameters: [prod3Id, 'tshirt.jpg'],
    );

    print('✅ Product images created');

    // Insert Sample User
    print('📝 Inserting sample user...');
    await connection.execute(
      '''INSERT INTO Users ("telegramid", "username", "usertype", "phonenumber", "fullname")
         VALUES (\$1, \$2, \$3, \$4, \$5)''',
      parameters: [
        987654321,
        'customer_user',
        'customer',
        '+1234567890',
        'محمد علي',
      ],
    );

    print('✅ Sample user created');

    // Close connection
    await connection.close();
    print('✅ Database seeding completed successfully!');
  } catch (e) {
    print('❌ Error: $e');
    rethrow;
  }
}
