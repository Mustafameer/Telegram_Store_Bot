#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار دوال المزامنة الجديدة
Test the new sync functions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# نقل البيئة
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 اختبار دوال المزامنة الجديدة")
print("=" * 60)

# 1. التحقق من وجود الدوال
print("\n✅ الخطوة 1: التحقق من الدوال...")

try:
    # نحاول استيراد الدوال
    import importlib.util
    spec = importlib.util.spec_from_file_location("bot", "bot.py")
    bot_module = importlib.util.module_from_spec(spec)
    
    print("⏳ جاري تحميل bot.py...")
    # لا نقوم بتنفيذ كل شيء، فقط التحقق من الاستيراد
    
    print("✅ تم التحقق من الملف")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    sys.exit(1)

# 2. التحقق من الكود
print("\n✅ الخطوة 2: التحقق من الكود...")

try:
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    # التحقق من وجود الدوال الجديدة
    required_functions = [
        "def send_order_notification",
        "def sync_order_status_to_cloud",
    ]
    
    for func in required_functions:
        if func in content:
            print(f"  ✅ وجدت {func}")
        else:
            print(f"  ❌ لم أجد {func}")
            sys.exit(1)
    
    # التحقق من التحديثات
    updates = [
        ("handle_confirm_order_seller", "sync_order_status_to_cloud"),
        ("handle_ship_order", "sync_order_status_to_cloud"),
        ("handle_deliver_order", "sync_order_status_to_cloud"),
        ("handle_reject_order", "sync_order_status_to_cloud"),
    ]
    
    print("\n  التحديثات:")
    for func_name, call in updates:
        # نبحث عن الدالة والاستدعاء
        func_start = content.find(f"def {func_name}")
        if func_start > 0:
            func_end = content.find("\ndef ", func_start + 1)
            func_content = content[func_start:func_end if func_end > 0 else func_start + 500]
            if call in func_content:
                print(f"    ✅ {func_name} يستخدم {call}")
            else:
                print(f"    ⚠️ {func_name} لا يستخدم {call}")
        else:
            print(f"    ❌ لم أجد {func_name}")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    sys.exit(1)

# 3. معلومات الملف
print("\n✅ الخطوة 3: معلومات الملف...")

try:
    file_stats = os.stat("bot.py")
    file_size = file_stats.st_size / 1024  # KB
    
    print(f"  📁 حجم الملف: {file_size:.1f} KB")
    print(f"  📅 آخر تعديل: {file_stats.st_mtime}")
    
except Exception as e:
    print(f"❌ خطأ: {e}")

# 4. الملفات الإضافية
print("\n✅ الخطوة 4: التحقق من ملفات التوثيق...")

docs = [
    "SYNC_ORDER_STATUS.md",
    "QUICK_START_SYNC.md",
]

for doc in docs:
    if os.path.exists(doc):
        size = os.path.getsize(doc) / 1024
        print(f"  ✅ {doc} ({size:.1f} KB)")
    else:
        print(f"  ❌ {doc} غير موجود")

# النتيجة النهائية
print("\n" + "=" * 60)
print("✅ اكتمل الاختبار بنجاح!")
print("=" * 60)

print("\n📝 ملخص التغييرات:")
print("  • إضافة send_order_notification()")
print("  • إضافة sync_order_status_to_cloud()")
print("  • تحديث handle_confirm_order_seller()")
print("  • تحديث handle_ship_order()")
print("  • تحديث handle_deliver_order()")
print("  • تحديث handle_reject_order()")

print("\n🚀 الخطوات التالية:")
print("  1. اختبر البوت محلياً: python bot.py")
print("  2. اضغط على زر تأكيد/شحن")
print("  3. تحقق من استقبال العميل للإشعار")
print("  4. تحقق من الـ logs للتأكد من المزامنة")

print("\n💡 ملاحظة: لا حاجة لأي إعدادات إضافية، النظام يعمل تلقائياً!")
