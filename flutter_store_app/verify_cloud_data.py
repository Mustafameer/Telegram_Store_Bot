#!/usr/bin/env python3
"""
Script to check what data is in the cloud PostgreSQL database
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

def check_data():
    try:
        print('📡 Connecting to PostgreSQL...')
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
        print('✅ Connected\n')
        
        # Check Sellers
        print('=' * 60)
        print('📊 SELLERS (المتاجر)')
        print('=' * 60)
        cursor.execute('SELECT sellerid, telegramid, username, storename, status FROM sellers')
        sellers = cursor.fetchall()
        if sellers:
            print(f'Found {len(sellers)} seller(s):')
            for seller in sellers:
                print(f'  - ID: {seller[0]}, Telegram ID: {seller[1]}, Name: {seller[3]}, Status: {seller[4]}')
        else:
            print('❌ No sellers found')
        
        # Check Categories
        print('\n' + '=' * 60)
        print('📁 CATEGORIES (الفئات)')
        print('=' * 60)
        cursor.execute('SELECT categoryid, sellerid, name FROM categories')
        categories = cursor.fetchall()
        if categories:
            print(f'Found {len(categories)} categor(ies):')
            for cat in categories:
                print(f'  - ID: {cat[0]}, Seller ID: {cat[1]}, Name: {cat[2]}')
        else:
            print('❌ No categories found')
        
        # Check Products
        print('\n' + '=' * 60)
        print('🛍️ PRODUCTS (المنتجات)')
        print('=' * 60)
        cursor.execute('SELECT productid, sellerid, categoryid, name, price, quantity FROM products')
        products = cursor.fetchall()
        if products:
            print(f'Found {len(products)} product(s):')
            for prod in products:
                print(f'  - ID: {prod[0]}, Seller: {prod[1]}, Category: {prod[2]}, Name: {prod[3]}, Price: {prod[4]}, Qty: {prod[5]}')
        else:
            print('❌ No products found')
        
        # Check Product Images
        print('\n' + '=' * 60)
        print('🖼️ PRODUCT IMAGES (صور المنتجات)')
        print('=' * 60)
        cursor.execute('SELECT COUNT(*) FROM productimages')
        img_count = cursor.fetchone()[0]
        print(f'Found {img_count} product image(s)')
        
        # Check Users
        print('\n' + '=' * 60)
        print('👥 USERS (المستخدمون)')
        print('=' * 60)
        cursor.execute('SELECT userid, telegramid, username, usertype FROM users')
        users = cursor.fetchall()
        if users:
            print(f'Found {len(users)} user(s):')
            for user in users:
                print(f'  - ID: {user[0]}, Telegram ID: {user[1]}, Name: {user[2]}, Type: {user[3]}')
        else:
            print('❌ No users found')
        
        # Summary
        print('\n' + '=' * 60)
        print('📈 SUMMARY')
        print('=' * 60)
        print(f'✅ Sellers: {len(sellers)}')
        print(f'✅ Categories: {len(categories)}')
        print(f'✅ Products: {len(products)}')
        print(f'✅ Product Images: {img_count}')
        print(f'✅ Users: {len(users)}')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    check_data()
