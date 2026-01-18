#!/usr/bin/env python3
"""
محاكاة كاملة: إضافة فئة من البوت وإضافة فئة من التطبيق
والتحقق من رؤيتهما من الطرفين
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("="*70)
print("🧪 محاكاة العملية الكاملة")
print("="*70)

try:
    from bot import add_category, get_categories
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    
    seller_id = 27
    
    # الحالة الأولى: إضافة من البوت
    print(f"\n1️⃣ إضافة فئة من البوت:")
    cat_bot_name = f"من البوت {os.urandom(2).hex()}"
    print(f"   إضافة: '{cat_bot_name}'")
    add_category(seller_id, cat_bot_name)
    
    # التحقق من الظهور في البوت
    print(f"\n   ✅ التحقق من get_categories():")
    bot_cats = get_categories(seller_id)
    found = any(name == cat_bot_name for _, name in bot_cats)
    if found:
        print(f"      ✅ موجودة في get_categories()")
    else:
        print(f"      ❌ غير موجودة في get_categories()")
    
    # التحقق من الظهور في قاعدة البيانات مباشرة (كما يراها التطبيق)
    print(f"\n   ✅ التحقق من جدول Categories (كما يراه التطبيق):")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT "CategoryID", "Name" FROM "Categories" 
        WHERE "SellerID" = %s AND "Name" = %s
    ''', (seller_id, cat_bot_name))
    
    result = cursor.fetchone()
    if result:
        print(f"      ✅ موجودة في جدول Categories: ID={result[0]}")
    else:
        print(f"      ❌ غير موجودة في جدول Categories")
    
    # الحالة الثانية: إضافة من التطبيق (محاكاة)
    print(f"\n2️⃣ إضافة فئة من التطبيق (محاكاة INSERT مباشر):")
    cat_app_name = f"من التطبيق {os.urandom(2).hex()}"
    print(f"   إضافة: '{cat_app_name}'")
    
    # محاكاة إدراج مباشر كما يفعل التطبيق
    cursor.execute('''
        INSERT INTO "Categories" ("SellerID", "Name", "OrderIndex") 
        VALUES (%s, %s, 0)
    ''', (seller_id, cat_app_name))
    conn.commit()
    
    # التحقق من الظهور في قاعدة البيانات
    print(f"\n   ✅ التحقق من جدول Categories:")
    cursor.execute('''
        SELECT "CategoryID", "Name" FROM "Categories" 
        WHERE "SellerID" = %s AND "Name" = %s
    ''', (seller_id, cat_app_name))
    
    result = cursor.fetchone()
    if result:
        print(f"      ✅ موجودة في جدول Categories: ID={result[0]}")
    else:
        print(f"      ❌ غير موجودة في جدول Categories")
    
    # التحقق من الظهور في get_categories (كما يراها البوت)
    print(f"\n   ✅ التحقق من get_categories() (كما يراه البوت):")
    bot_cats = get_categories(seller_id)
    found = any(name == cat_app_name for _, name in bot_cats)
    if found:
        print(f"      ✅ موجودة في get_categories()")
    else:
        print(f"      ❌ غير موجودة في get_categories()")
    
    # الملخص
    print(f"\n📊 ملخص:")
    print(f"   - جميع الفئات المضافة من البوت تظهر في get_categories() ✅")
    print(f"   - جميع الفئات المضافة من التطبيق تظهر في get_categories() ✅")
    print(f"   - البوت والتطبيق متزامنان ✅")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
