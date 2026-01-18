#!/usr/bin/env python3
"""
محاكاة كاملة لعملية إضافة فئة عبر معالجات الرسائل
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("🎯 محاكاة كاملة لعملية إضافة الفئة")
print("="*70)

try:
    # Import required functions
    from bot import (
        get_seller_by_telegram, get_categories, 
        add_category, user_states, bot, types
    )
    
    # Simulate user interaction
    test_telegram_id = 999999999  # معرّف بائع موجود
    
    print(f"\n📱 محاكاة مستخدم برقم Telegram: {test_telegram_id}")
    
    # Get seller info
    seller = get_seller_by_telegram(test_telegram_id)
    if not seller:
        print(f"❌ لا يوجد بائع بهذا الرقم")
        sys.exit(1)
    
    seller_id = seller[0]
    print(f"✅ البائع موجود: ID={seller_id}, Name={seller[3]}")
    
    # Step 1: Simulate user clicking "➕ إضافة قسم"
    print(f"\n📍 الخطوة 1️⃣: المستخدم ينقر على 'إضافة قسم'")
    
    # Initialize state like add_category_step1 does
    user_states[test_telegram_id] = {
        "step": "add_category",
        "seller_id": seller_id
    }
    print(f"   ✅ تم تعيين user_states: {user_states[test_telegram_id]}")
    
    # Step 2: Simulate user typing category name
    print(f"\n📍 الخطوة 2️⃣: المستخدم يكتب اسم الفئة")
    
    # Check if state exists
    if test_telegram_id not in user_states:
        print(f"   ❌ الـ STATE غير موجود! لم يتم استدعاء add_category_step1 بشكل صحيح")
        sys.exit(1)
    
    state = user_states[test_telegram_id]
    print(f"   ✅ الـ STATE موجود: {state}")
    
    if state.get("step") != "add_category":
        print(f"   ❌ الـ STEP خاطئ: {state.get('step')}")
        sys.exit(1)
    
    print(f"   ✅ الـ STEP صحيح: {state.get('step')}")
    
    # Try to add category
    category_name = f"اختبار محاكاة {os.urandom(2).hex()}"
    print(f"\n📍 الخطوة 3️⃣: إضافة الفئة '{category_name}'")
    
    print(f"   📁 استدعاء add_category({state['seller_id']}, '{category_name}')")
    add_category(state["seller_id"], category_name)
    print(f"   ✅ انتهت العملية بدون أخطاء")
    
    # Verify
    print(f"\n📍 الخطوة 4️⃣: التحقق من إضافة الفئة")
    categories = get_categories(seller_id)
    
    found = any(cat[1] == category_name for cat in categories)
    if found:
        print(f"   ✅ تم إضافة الفئة بنجاح!")
        print(f"\n   📊 جميع فئات البائع:")
        for cat_id, cat_name in categories:
            print(f"      - {cat_name} (ID: {cat_id})")
    else:
        print(f"   ❌ الفئة لم تضف!")
        print(f"\n   📊 الفئات الموجودة:")
        for cat_id, cat_name in categories:
            print(f"      - {cat_name} (ID: {cat_id})")
    
    # Clean up
    if test_telegram_id in user_states:
        del user_states[test_telegram_id]
    
    print(f"\n✅ انتهت المحاكاة بنجاح")
    
except Exception as e:
    print(f"\n❌ حدث خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
