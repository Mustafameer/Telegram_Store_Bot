#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار منطق الشراء من متجر مغلق
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES, get_seller_by_id, get_user, is_customer_registered_for_store_by_telegram_id

def test_closed_store_purchase_logic():
    """محاكاة منطق الشراء من متجر مغلق"""
    print("=" * 80)
    print("🧪 اختبار منطق الشراء من متجر مغلق")
    print("=" * 80)
    
    # استخدم معرف تليجرام حقيقي من النظام
    test_telegram_ids = [
        1041977029,  # مستخدم مسجل في Seller=26
        8401054513,  # مستخدم مسجل في Seller=21
        6619127767,  # مستخدم مسجل في Seller=21
        999999999,   # مستخدم غير موجود
    ]
    
    test_sellers = [21, 26]  # المتاجر المغلقة
    
    for telegram_id in test_telegram_ids:
        print(f"\n{'='*80}")
        print(f"🔍 اختبار telegram_id = {telegram_id}")
        print(f"{'='*80}")
        
        # التحقق من وجود المستخدم
        user_info = get_user(telegram_id)
        print(f"user_info = {user_info}")
        
        # اختبر لكل متجر
        for seller_id in test_sellers:
            seller = get_seller_by_id(seller_id)
            if not seller:
                print(f"❌ البائع {seller_id} غير موجود")
                continue
            
            seller_id_from_db, seller_telegram_id, seller_username, seller_storename, *_ = seller
            require_registration = seller[-1] if len(seller) > 10 else 0
            
            print(f"\n   Seller ID={seller_id}:")
            print(f"     StoreName: {seller_storename}")
            print(f"     RequireCustomerRegistration: {require_registration}")
            
            # التحقق من التسجيل
            is_registered = is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id)
            print(f"     Is Registered: {is_registered}")
            
            # تقييم الشروط
            is_seller_closed = require_registration
            all_sellers_closed = is_seller_closed  # في هذه الحالة، هناك متجر واحد فقط
            
            print(f"\n   منطق الشراء:")
            print(f"     is_seller_closed (require_registration): {is_seller_closed}")
            print(f"     all_sellers_closed: {all_sellers_closed}")
            print(f"     user_info: {bool(user_info)}")
            print(f"     is_registered: {is_registered}")
            
            # الشرط الذي يجب أن يكون صحيحاً لتنفيذ create_confirmed_order_for_closed_store
            should_create_order = all_sellers_closed and user_info
            print(f"\n     RESULT: all_sellers_closed and user_info = {should_create_order}")
            
            if should_create_order:
                print(f"     ✅ سيتم استدعاء create_confirmed_order_for_closed_store()")
            else:
                if not all_sellers_closed:
                    print(f"     ❌ المتجر ليس مغلقاً (require_registration = {is_seller_closed})")
                if not user_info:
                    print(f"     ❌ المستخدم غير مسجل (user_info = {user_info})")
    
    print(f"\n{'='*80}")

if __name__ == '__main__':
    test_closed_store_purchase_logic()
