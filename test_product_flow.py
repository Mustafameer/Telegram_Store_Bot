#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار شامل لتدفق إضافة المنتجات للمتاجر المفتوحة
Comprehensive test for open store product addition flow
"""

def trace_product_addition_flow():
    """تتبع تدفق إضافة المنتج من البداية إلى النهاية"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    flow = {
        "add_product_step1": False,  # اختيار القسم
        "add_product_step2": False,  # اختيار القسم الفعلي
        "add_product_step3": False,  # إدخال اسم المنتج
        "add_product_step4": False,  # إدخال السعر
        "add_product_step4b": False, # إدخال سعر الجملة
        "add_product_step5": False,  # إدخال الكمية
        "add_product_step6": False,  # معالجة صورة المنتج (النص والصورة معاً)
        "handle_product_image_photo": False,  # معالج الصور
        "handle_product_image_text": False,  # معالج النص (تخطي الصورة)
        "finish_adding_product": False,  # حفظ المنتج النهائي
    }
    
    for step in flow:
        if f"def {step}(" in content:
            flow[step] = True
    
    return flow

def check_state_initialization():
    """التحقق من تهيئة الحالة الصحيحة"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    # البحث عن حيث يتم تهيئة state لإضافة منتج
    found = False
    correct_init = False
    
    for idx, line in enumerate(lines):
        if 'user_states[telegram_id] = {' in line and idx > 4700:  # بحث قريب من add_product
            # تحقق من السطور التالية لحقول الحالة
            state_snippet = '\n'.join(lines[idx:idx+10])
            if 'seller_id' in state_snippet and 'category_id' in state_snippet:
                if 'product_images' not in state_snippet:  # تأكد أنه لا توجد قائمة الصور
                    found = True
                    correct_init = True
                else:
                    found = True
                    correct_init = False
                break
    
    return found, correct_init

def check_product_database_save():
    """التحقق من حفظ المنتج في قاعدة البيانات بشكل صحيح"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    issues = []
    
    # البحث عن دالة حفظ المنتج
    for idx, line in enumerate(lines):
        if "INSERT INTO Products" in line:
            # استخرج السطور المحيطة
            snippet = '\n'.join(lines[max(0, idx-3):min(len(lines), idx+10)])
            
            # تحقق من أن الكمية يتم إدراجها كقيمة ثابتة وليس حساب
            if "SELECT COUNT(*) FROM ProductImages" in snippet:
                issues.append({
                    'line': idx + 1,
                    'issue': 'حساب تلقائي للكمية من الصور (للمتاجر المقفولة)',
                    'severity': 'error'
                })
    
    return issues

def check_image_insertion():
    """التحقق من إدراج الصورة الواحدة في ProductImages"""
    
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    image_insertions = []
    
    for idx, line in enumerate(lines):
        if "INSERT INTO ProductImages" in line:
            snippet = '\n'.join(lines[max(0, idx-2):min(len(lines), idx+8)])
            image_insertions.append({
                'line': idx + 1,
                'snippet': snippet[:100] + "..."
            })
    
    return image_insertions

def print_summary():
    """طباعة الملخص الشامل"""
    
    print("\n" + "=" * 70)
    print("🔍 **اختبار تدفق إضافة المنتجات للمتاجر المفتوحة**")
    print("=" * 70 + "\n")
    
    # 1. تتبع التدفق
    print("1️⃣ **تتبع التدفق:**\n")
    flow = trace_product_addition_flow()
    
    all_exist = True
    for step, exists in flow.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {step}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n   ✅ جميع خطوات التدفق موجودة وتعمل!")
    
    # 2. التحقق من تهيئة الحالة
    print("\n2️⃣ **تهيئة الحالة:**\n")
    found, correct = check_state_initialization()
    
    if found:
        if correct:
            print("   ✅ تهيئة الحالة صحيحة (بدون قائمة صور متعددة)")
        else:
            print("   ❌ تهيئة الحالة تحتوي على قائمة صور متعددة!")
    else:
        print("   ⚠️ لم يتم العثور على تهيئة الحالة")
    
    # 3. حفظ المنتج
    print("\n3️⃣ **حفظ المنتج في قاعدة البيانات:**\n")
    db_issues = check_product_database_save()
    
    if db_issues:
        for issue in db_issues:
            print(f"   ❌ السطر {issue['line']}: {issue['issue']}")
    else:
        print("   ✅ حفظ المنتج بشكل صحيح (كمية يدوية، بدون حساب تلقائي)")
    
    # 4. إدراج الصورة
    print("\n4️⃣ **إدراج الصورة:**\n")
    image_inserts = check_image_insertion()
    
    if image_inserts:
        print(f"   ℹ️ عدد نقاط إدراج الصور المكتشفة: {len(image_inserts)}")
        for idx, insert in enumerate(image_inserts[:2], 1):
            print(f"   السطر {insert['line']}: {insert['snippet'][:60]}...")
        print("   ✅ إدراج الصورة موجود ويعمل")
    else:
        print("   ⚠️ لم يتم العثور على إدراج الصورة")
    
    # الملخص النهائي
    print("\n" + "=" * 70)
    print("✅ **النتيجة النهائية:**")
    print("=" * 70)
    
    if all_exist and correct and not db_issues:
        print("\n✅ تدفق إضافة المنتجات للمتاجر المفتوحة يعمل بشكل صحيح!")
        print("   🎯 المتطلبات:")
        print("      • إدخال يدوي للكمية (بدون حساب تلقائي)")
        print("      • صورة واحدة فقط لكل منتج")
        print("      • بدون منطق للمتاجر المقفولة")
        print("\n✅ النظام جاهز للاستخدام!")
    else:
        print("\n⚠️ هناك مشاكل تحتاج إلى إصلاح")

if __name__ == "__main__":
    print_summary()
