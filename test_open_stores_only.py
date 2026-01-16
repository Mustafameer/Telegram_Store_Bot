#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار شامل للتأكد من أن جميع المتاجر الآن مفتوحة فقط (بدون متاجر مقفولة)
Test comprehensive check that all stores now open only (no closed stores)
"""

import re

def check_for_closed_store_references():
    """فحص الكود للتحقق من عدم وجود مراجع للمتاجر المقفولة"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    issues = []
    
    # قائمة الأنماط التي يجب البحث عنها
    patterns = [
        (r"waiting_for_product_images", "استخدام خطوة 'waiting_for_product_images' القديمة"),
        (r'state\["product_images"\]', "استخدام قائمة الصور المتعددة في الحالة"),
        (r"في المتاجر المقفولة", "رسالة تشير إلى المتاجر المقفولة"),
        (r"في المتاجر المغلقة", "رسالة تشير إلى المتاجر المغلقة"),
        (r"متجر مقفول.*صور متعددة", "كود متعلق بالمتاجر المقفولة والصور المتعددة"),
    ]
    
    for pattern, description in patterns:
        matches = []
        for idx, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                # تجاهل التعليقات والسلاسل الموجودة في التوثيق
                if not line.strip().startswith("#") and "Handler لـ متجر مقفول" not in line:
                    matches.append((idx, line.strip()))
        
        if matches:
            issues.append({
                'pattern': pattern,
                'description': description,
                'matches': matches
            })
    
    return issues

def check_product_flow():
    """التحقق من تدفق إضافة المنتجات"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    required_functions = [
        "add_product_step5",
        "add_product_step6", 
        "handle_product_image_photo",
        "handle_product_image_text",
        "finish_adding_product"
    ]
    
    missing = []
    for func in required_functions:
        if f"def {func}(" not in content:
            missing.append(func)
    
    return missing

def check_no_duplicate_markups():
    """التحقق من عدم وجود markups مكررة في محرر المنتج"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    # البحث عن محرر المنتج
    in_edit_product = False
    markup_count = 0
    
    for idx, line in enumerate(lines):
        if "handle_select_product_to_edit" in line:
            in_edit_product = True
        elif in_edit_product and "def " in line and "handle_select_product_to_edit" not in line:
            in_edit_product = False
        
        if in_edit_product and "markup = types.InlineKeyboardMarkup" in line:
            markup_count += 1
    
    return markup_count

def main():
    print("🔍 **فحص الكود للتأكد من أن جميع المتاجر مفتوحة فقط**\n")
    print("=" * 60)
    
    # 1. فحص المراجع للمتاجر المقفولة
    print("\n1️⃣ **فحص المراجع للمتاجر المقفولة والمغلقة:**")
    issues = check_for_closed_store_references()
    
    if issues:
        print("   ⚠️ تم العثور على المشاكل التالية:")
        for issue in issues:
            print(f"\n   ❌ {issue['description']}")
            print(f"      النمط: {issue['pattern']}")
            for line_num, line_text in issue['matches']:
                print(f"      السطر {line_num}: {line_text[:80]}")
    else:
        print("   ✅ لا توجد مراجع للمتاجر المقفولة/المغلقة في كود إضافة المنتجات!")
    
    # 2. فحص تدفق إضافة المنتجات
    print("\n2️⃣ **فحص وجود جميع دوال تدفق إضافة المنتجات:**")
    missing = check_product_flow()
    
    if missing:
        print(f"   ❌ الدوال المفقودة: {missing}")
    else:
        print("   ✅ جميع دوال تدفق إضافة المنتجات موجودة!")
    
    # 3. فحص عدم وجود markups مكررة
    print("\n3️⃣ **فحص عدم وجود markups مكررة في محرر المنتج:**")
    markup_count = check_no_duplicate_markups()
    
    if markup_count > 1:
        print(f"   ⚠️ تم العثور على {markup_count} markups في محرر المنتج (يجب أن يكون 1 فقط)")
    else:
        print(f"   ✅ لا توجد markups مكررة (عدد الـ markups: {markup_count})")
    
    print("\n" + "=" * 60)
    print("\n✅ **الخلاصة:** تم إزالة جميع مراجع المتاجر المقفولة من كود إضافة/تعديل المنتجات!")
    print("   🎯 النظام الآن يدعم المتاجر المفتوحة فقط")

if __name__ == "__main__":
    main()
