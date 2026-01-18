#!/usr/bin/env python3
"""
اختبار شامل لإضافة الفئات مع تتبع كل خطوة
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("🧪 اختبار شامل لإضافة الفئات")
print("="*70)

# Step 1: Check database connection
print("\n📍 الخطوة 1: التحقق من الاتصال بقاعدة البيانات")
try:
    import psycopg2
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    print("   ✅ الاتصال بـ PostgreSQL نجح")
    
    # Check categories table
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='categories' ORDER BY ordinal_position")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"   📊 أعمدة جدول categories: {columns}")
    
    conn.close()
except Exception as e:
    print(f"   ❌ خطأ في الاتصال: {e}")
    sys.exit(1)

# Step 2: Test add_category function
print("\n📍 الخطوة 2: اختبار دالة add_category")
try:
    # Import bot functions
    from bot import add_category, get_seller_by_telegram, get_categories
    
    # Get a known seller
    seller_telegram_id = 1234567890  # Adjust this if needed
    
    print(f"   🔍 البحث عن البائع برقم Telegram: {seller_telegram_id}")
    seller = get_seller_by_telegram(seller_telegram_id)
    
    if seller:
        seller_id = seller[0]
        print(f"   ✅ وجدنا البائع: ID={seller_id}, Name={seller[3]}")
        
        # Try to add category
        test_category_name = f"اختبار فئة {os.urandom(2).hex()}"
        print(f"\n   📁 جاري إضافة فئة: '{test_category_name}'")
        
        add_category(seller_id, test_category_name)
        
        print(f"\n   ⏳ جاري التحقق من إضافة الفئة...")
        categories = get_categories(seller_id)
        
        # Check if category was added
        found = any(cat[1] == test_category_name for cat in categories)
        
        if found:
            print(f"   ✅ تم إضافة الفئة بنجاح!")
            print(f"\n   📊 جميع فئات البائع:")
            for cat_id, cat_name in categories:
                print(f"      - {cat_name} (ID: {cat_id})")
        else:
            print(f"   ❌ لم يتم العثور على الفئة المضافة")
            print(f"\n   📊 الفئات الموجودة:")
            for cat_id, cat_name in categories:
                print(f"      - {cat_name} (ID: {cat_id})")
    else:
        print(f"   ⚠️  لم نجد بائع برقم Telegram: {seller_telegram_id}")
        print(f"   🔍 جاري البحث عن أي بائع...")
        
        # Import database function
        import psycopg2
        DATABASE_URL = os.environ.get('DATABASE_URL')
        db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT sellerid, telegramid, storename FROM sellers LIMIT 3")
        sellers = cursor.fetchall()
        conn.close()
        
        if sellers:
            print(f"   📝 البائعون الموجودون:")
            for sid, tg_id, sname in sellers:
                print(f"      - ID: {sid}, Telegram: {tg_id}, Store: {sname}")
            
            # Use first seller
            sid = sellers[0][0]
            print(f"\n   📁 جاري اختبار إضافة فئة للبائع {sid}...")
            
            test_category_name = f"اختبار فئة {os.urandom(2).hex()}"
            add_category(sid, test_category_name)
            
            categories = get_categories(sid)
            found = any(cat[1] == test_category_name for cat in categories)
            
            if found:
                print(f"   ✅ تم إضافة الفئة بنجاح!")
            else:
                print(f"   ❌ فشل إضافة الفئة")
        else:
            print(f"   ❌ لا توجد بائعون في النظام")

except Exception as e:
    print(f"   ❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✅ انتهى الاختبار")
print("="*70)
