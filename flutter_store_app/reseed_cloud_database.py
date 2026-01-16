#!/usr/bin/env python3
"""
Script to reseed cloud PostgreSQL database with sample data
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'switchback.proxy.rlwy.net')
DB_PORT = int(os.getenv('DB_PORT', '20266'))
DB_NAME = os.getenv('DB_NAME', 'railway')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_SSL = os.getenv('DB_SSL', 'true').lower() == 'true'

def seed_database():
    try:
        print('📡 Connecting to PostgreSQL Cloud Database...')
        sslmode = 'require' if DB_SSL else 'disable'
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=sslmode
        )
        
        cursor = conn.cursor()
        print('✅ Connected to PostgreSQL')

        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM "sellers"')
        seller_count = cursor.fetchone()[0]
        
        if seller_count > 0:
            print(f'\n⚠️ Database already has {seller_count} seller(s)')
            response = input('Do you want to clear and reseed? (yes/no): ').strip().lower()
            if response != 'yes':
                print('❌ Cancelled by user')
                cursor.close()
                conn.close()
                return

        # Clear existing data
        print('\n🗑️ Clearing existing data...')
        cursor.execute('DELETE FROM "orderitems"')
        cursor.execute('DELETE FROM "orders"')
        cursor.execute('DELETE FROM "carts"')
        cursor.execute('DELETE FROM "productimages"')
        cursor.execute('DELETE FROM "products"')
        cursor.execute('DELETE FROM "categories"')
        cursor.execute('DELETE FROM "users"')
        cursor.execute('DELETE FROM "sellers"')
        conn.commit()
        print('✅ Database cleared')

        # Insert Seller
        print('\n📝 Inserting sample seller...')
        cursor.execute('''
            INSERT INTO "sellers" ("telegramid", "username", "storename", "status", "imagepath", "requirecustomerregistration")
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING "sellerid"
        ''', (1041977029, 'seller_user', 'متجري الرائع', 'active', 'seller.jpg', 0))
        
        seller_id = cursor.fetchone()[0]
        conn.commit()
        print(f'✅ Seller created: ID={seller_id}')

        # Insert Categories
        print('\n📝 Inserting sample categories...')
        cursor.execute('''
            INSERT INTO "categories" ("sellerid", "name", "orderindex", "imagepath")
            VALUES (%s, %s, %s, %s)
            RETURNING "categoryid"
        ''', (seller_id, 'إلكترونيات', 1, 'electronics.jpg'))
        cat1_id = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO "categories" ("sellerid", "name", "orderindex", "imagepath")
            VALUES (%s, %s, %s, %s)
            RETURNING "categoryid"
        ''', (seller_id, 'ملابس', 2, 'clothing.jpg'))
        cat2_id = cursor.fetchone()[0]
        
        conn.commit()
        print(f'✅ Categories created: ID1={cat1_id}, ID2={cat2_id}')

        # Insert Products for Category 1 (Electronics)
        print('\n📝 Inserting sample products...')
        cursor.execute('''
            INSERT INTO "products" ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING "productid"
        ''', (seller_id, cat1_id, 'هاتف ذكي', 'هاتف ذكي حديث بمواصفات عالية', 599.99, 450.00, 50, 'phone.jpg', 'active'))
        prod1_id = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO "products" ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING "productid"
        ''', (seller_id, cat1_id, 'سماعات بلوتوث', 'سماعات عالية الجودة مع بطارية طويلة الأمد', 129.99, 80.00, 100, 'headphones.jpg', 'active'))
        prod2_id = cursor.fetchone()[0]

        # Insert Products for Category 2 (Clothing)
        cursor.execute('''
            INSERT INTO "products" ("sellerid", "categoryid", "name", "description", "price", "wholesaleprice", "quantity", "imagepath", "status")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING "productid"
        ''', (seller_id, cat2_id, 'تيشيرت أبيض', 'تيشيرت قطني مريح بألوان مختلفة', 19.99, 10.00, 200, 'tshirt.jpg', 'active'))
        prod3_id = cursor.fetchone()[0]

        conn.commit()
        print(f'✅ Products created: ID1={prod1_id}, ID2={prod2_id}, ID3={prod3_id}')

        # Insert Product Images
        print('\n📝 Inserting product images...')
        cursor.execute('''
            INSERT INTO "productimages" ("productid", "imagepath")
            VALUES (%s, %s)
        ''', (prod1_id, 'phone.jpg'))

        cursor.execute('''
            INSERT INTO "productimages" ("productid", "imagepath")
            VALUES (%s, %s)
        ''', (prod2_id, 'headphones.jpg'))

        cursor.execute('''
            INSERT INTO "productimages" ("productid", "imagepath")
            VALUES (%s, %s)
        ''', (prod3_id, 'tshirt.jpg'))

        conn.commit()
        print('✅ Product images created')

        # Insert Sample User
        print('\n📝 Inserting sample user...')
        cursor.execute('''
            INSERT INTO "users" ("telegramid", "username", "usertype", "phonenumber", "fullname")
            VALUES (%s, %s, %s, %s, %s)
        ''', (987654321, 'customer_user', 'customer', '+1234567890', 'محمد علي'))
        
        conn.commit()
        print('✅ Sample user created')

        # Summary
        print('\n' + '=' * 60)
        print('📊 SEEDING COMPLETED SUCCESSFULLY!')
        print('=' * 60)
        print(f'✅ 1 Seller created (ID: {seller_id})')
        print(f'✅ 2 Categories created')
        print(f'✅ 3 Products created')
        print(f'✅ 3 Product images created')
        print(f'✅ 1 User created')
        print('=' * 60)

        # Close connection
        cursor.close()
        conn.close()

    except Exception as e:
        print(f'❌ Error: {e}')
        raise

if __name__ == '__main__':
    seed_database()
