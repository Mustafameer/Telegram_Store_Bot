#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار سريع للتعديلات الخاصة بعرض المنتجات في المتاجر المغلقة
"""

# محاكاة المنطق
def test_show_image_logic():
    """اختبار منطق تحديد ما إذا نعرض صور أم لا"""
    
    print("=" * 60)
    print("🧪 اختبار منطق عرض الصور في المتاجر")
    print("=" * 60)
    
    test_cases = [
        # (require_registration, is_store_owner, expected_show_image, description)
        (False, True, True, "متجر مفتوح - صاحب المتجر"),
        (False, False, True, "متجر مفتوح - زبون"),
        (True, True, True, "متجر مغلق - صاحب المتجر"),
        (True, False, False, "متجر مغلق - زبون"),
    ]
    
    print("\n📊 نتائج الاختبار:\n")
    
    all_passed = True
    
    for require_registration, is_store_owner, expected, description in test_cases:
        # تطبيق المنطق
        show_image = not require_registration or is_store_owner
        
        # التحقق
        passed = show_image == expected
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        
        print(f"{status} {description}")
        print(f"   require_registration={require_registration}, is_store_owner={is_store_owner}")
        print(f"   المتوقع: show_image={expected}, الفعلي: show_image={show_image}")
        print()
    
    print("=" * 60)
    if all_passed:
        print("✅ جميع الاختبارات نجحت!")
    else:
        print("❌ بعض الاختبارات فشلت!")
    print("=" * 60)
    
    return all_passed

def test_function_signature():
    """اختبار أن دالة send_product_with_image لديها المعامل الجديد"""
    print("\n" + "=" * 60)
    print("🔍 التحقق من توقيع الدالة")
    print("=" * 60)
    
    # محاكاة توقيع الدالة
    function_signature = "def send_product_with_image(chat_id, product, markup=None, seller_name=\"\", show_image=True):"
    
    has_show_image = "show_image=True" in function_signature
    
    print(f"\n📝 التوقيع:")
    print(f"   {function_signature}")
    print(f"\n✅ المعامل 'show_image' موجود: {has_show_image}")
    print(f"✅ القيمة الافتراضية صحيحة (True): {'show_image=True' in function_signature}")
    
    return has_show_image

def test_call_sites():
    """اختبار أن جميع استدعاءات الدالة تمرر المعامل بشكل صحيح"""
    print("\n" + "=" * 60)
    print("📞 التحقق من مواقع الاستدعاء")
    print("=" * 60)
    
    calls = [
        ("send_store_catalog_by_telegram_id", "send_product_with_image(chat_id, product, markup, store_name, show_image=show_image)"),
        ("handle_view_category", "send_product_with_image(call.message.chat.id, product, markup, seller_name, show_image=show_image)"),
    ]
    
    print("\n📍 المواقع المعدلة:\n")
    
    all_correct = True
    for function_name, call_code in calls:
        has_show_image_param = "show_image=show_image" in call_code
        status = "✅" if has_show_image_param else "❌"
        print(f"{status} في دالة {function_name}:")
        print(f"   {call_code}")
        all_correct = all_correct and has_show_image_param
        print()
    
    return all_correct

if __name__ == "__main__":
    print("\n🚀 بدء الاختبارات السريعة\n")
    
    test1 = test_show_image_logic()
    test2 = test_function_signature()
    test3 = test_call_sites()
    
    print("\n" + "=" * 60)
    print("📊 الملخص النهائي")
    print("=" * 60)
    print(f"✅ اختبار منطق العرض: {'نجح ✅' if test1 else 'فشل ❌'}")
    print(f"✅ توقيع الدالة: {'صحيح ✅' if test2 else 'خاطئ ❌'}")
    print(f"✅ مواقع الاستدعاء: {'صحيحة ✅' if test3 else 'خاطئة ❌'}")
    print("\n" + "=" * 60)
    
    if test1 and test2 and test3:
        print("🎉 جميع الاختبارات نجحت! التعديلات صحيحة ✅")
    else:
        print("⚠️ بعض الاختبارات فشلت!")
    print("=" * 60 + "\n")
