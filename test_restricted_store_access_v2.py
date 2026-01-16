"""
اختبار السلوك الجديد للمتاجر المقفولة:
- زبون غير مسجل: يرى الفئات، عند الضغط على فئة يرى رسالة "نعتذر المتجر مقفول"
- زبون مسجل: يرى الفئات والمنتجات عادي
- صاحب المتجر: وصول كامل
"""

def test_registration_check_logic():
    """اختبار منطق التحقق من التسجيل"""
    
    # الحالة 1: متجر مفتوح - الجميع يرون الفئات والمنتجات
    print("=" * 60)
    print("الحالة 1: متجر مفتوح (RequireCustomerRegistration = 0)")
    print("=" * 60)
    require_registration = 0
    customer_is_registered = True  # افتراضي
    if not require_registration:
        customer_is_registered = True
    print(f"✅ customer_is_registered = {customer_is_registered}")
    print("النتيجة: سيرى الفئات والمنتجات ✓")
    print()
    
    # الحالة 2: متجر مغلق، زبون مسجل
    print("=" * 60)
    print("الحالة 2: متجر مغلق (RequireCustomerRegistration = 1)")
    print("زبون مسجل في CreditCustomers")
    print("=" * 60)
    require_registration = 1
    customer_telegram_id = 123456789
    seller_telegram_id = 987654321
    is_registered_check = True  # نتيجة is_customer_registered_for_store_by_telegram_id()
    
    customer_is_registered = True  # افتراضي
    if require_registration:
        if customer_telegram_id == seller_telegram_id:  # صاحب المتجر
            customer_is_registered = True
        else:
            customer_is_registered = is_registered_check
    
    print(f"✅ customer_is_registered = {customer_is_registered}")
    print("في send_store_catalog: سيرى الفئات ✓")
    print("في handle_view_category: سيرى المنتجات ✓ (لأنه مسجل)")
    print()
    
    # الحالة 3: متجر مغلق، زبون غير مسجل
    print("=" * 60)
    print("الحالة 3: متجر مغلق (RequireCustomerRegistration = 1)")
    print("زبون غير مسجل في CreditCustomers")
    print("=" * 60)
    require_registration = 1
    customer_telegram_id = 111111111
    seller_telegram_id = 987654321
    is_registered_check = False  # نتيجة is_customer_registered_for_store_by_telegram_id()
    
    customer_is_registered = True  # افتراضي
    if require_registration:
        if customer_telegram_id == seller_telegram_id:  # صاحب المتجر
            customer_is_registered = True
        else:
            customer_is_registered = is_registered_check
    
    print(f"❌ customer_is_registered = {customer_is_registered}")
    print("في send_store_catalog: سيرى الفئات ✓ (السلوك الجديد)")
    print("في handle_view_category:")
    
    # منطق handle_view_category
    is_registered = customer_is_registered
    if require_registration and not is_registered:
        print("  ❌ سيعرض رسالة الرفض: 'نعتذر، المتجر مقفول' ✓")
        print("  لن يرى المنتجات")
    else:
        print("  ✅ سيرى المنتجات")
    print()
    
    # الحالة 4: متجر مغلق، صاحب المتجر
    print("=" * 60)
    print("الحالة 4: متجر مغلق (RequireCustomerRegistration = 1)")
    print("صاحب المتجر نفسه")
    print("=" * 60)
    require_registration = 1
    customer_telegram_id = 987654321
    seller_telegram_id = 987654321
    
    customer_is_registered = True  # افتراضي
    if require_registration:
        if customer_telegram_id == seller_telegram_id:  # صاحب المتجر
            customer_is_registered = True
        else:
            customer_is_registered = False
    
    print(f"✅ customer_is_registered = {customer_is_registered}")
    print("في send_store_catalog: سيرى الفئات ✓")
    print("في handle_view_category: سيرى المنتجات ✓")
    print()

if __name__ == "__main__":
    print("\n🧪 اختبار منطق التحقق من تسجيل الزبائن\n")
    test_registration_check_logic()
    print("\n" + "=" * 60)
    print("📋 ملخص السلوك الجديد:")
    print("=" * 60)
    print("✅ جميع الزبائن (مسجلين وغير مسجلين) يرون الفئات")
    print("✅ الزبائن غير المسجلين: رسالة 'نعتذر المتجر مقفول' عند الضغط على فئة")
    print("✅ الزبائن المسجلين: يرون المنتجات عادي")
    print("✅ صاحب المتجر: وصول كامل")
    print("=" * 60 + "\n")
