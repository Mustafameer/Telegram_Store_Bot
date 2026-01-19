#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار نهائي: محاكاة شراء من متجر مغلق مع save_notification
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_db_connection, IS_POSTGRES, get_seller_by_id, get_user, is_customer_registered_for_store_by_telegram_id, save_notification

def simulate_closed_store_purchase():
    """محاكاة شراء من متجر مغلق مع التحقق من save_notification"""
    
    # معرف مستخدم مسجل في Seller=21
    telegram_id = 8401054513  # Muhammed
    seller_id = 21
    
    print(f"{'='*80}")
    print(f"🧪 محاكاة شراء من متجر مغلق")
    print(f"{'='*80}\n")
    
    # التحقق من المستخدم
    user_info = get_user(telegram_id)
    print(f"1️⃣ المستخدم:")
    print(f"   TelegramID: {telegram_id}")
    print(f"   user_info: {bool(user_info)}")
    
    # التحقق من البائع
    seller = get_seller_by_id(seller_id)
    print(f"\n2️⃣ البائع:")
    print(f"   SellerID: {seller_id}")
    if seller:
        require_registration = seller[10] if len(seller) > 10 else 0
        print(f"   require_registration: {require_registration}")
        print(f"   is_closed: {bool(require_registration)}")
    
    # التحقق من التسجيل
    is_registered = is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id)
    print(f"\n3️⃣ الحالة:")
    print(f"   is_registered: {is_registered}")
    
    # تقييم الشروط
    print(f"\n4️⃣ شروط الشراء:")
    all_sellers_closed = True
    all_sellers_closed = all_sellers_closed and bool(require_registration)
    all_sellers_closed = all_sellers_closed and bool(user_info)
    all_sellers_closed = all_sellers_closed and is_registered
    
    print(f"   all_sellers_closed and user_info: {all_sellers_closed and bool(user_info)}")
    
    # محاكاة الشراء
    if all_sellers_closed and user_info:
        print(f"\n5️⃣ محاكاة create_confirmed_order_for_closed_store:")
        print(f"   ✅ سيتم استدعاء الدالة")
        print(f"   ✅ سيتم حفظ الإشعار")
        
        # اختبار حفظ الإشعار
        product_names = "منتج 1, منتج 2"
        total_amount = 100000
        
        result = save_notification(
            customer_telegram_id=telegram_id,
            notification_type='closed_store_purchase',
            title=f"✅ تم تأكيد طلبك",
            message=f"تم شراء 2 منتج(ات) بنجاح! المبلغ: {total_amount} د.ع",
            product_names=product_names,
            total_amount=total_amount,
            seller_id=seller_id,
            data=None
        )
        
        print(f"\n6️⃣ حفظ الإشعار:")
        print(f"   النتيجة: {result}")
        
        if result:
            # تحقق من الإشعار في قاعدة البيانات
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if IS_POSTGRES:
                cursor.execute("""
                    SELECT "NotificationID", "CustomerTelegramID", "Type", "Title"
                    FROM "Notifications"
                    WHERE "CustomerTelegramID" = %s
                    ORDER BY "NotificationID" DESC
                    LIMIT 1
                """, (telegram_id,))
            else:
                cursor.execute("""
                    SELECT NotificationID, CustomerTelegramID, Type, Title
                    FROM Notifications
                    WHERE CustomerTelegramID = ?
                    ORDER BY NotificationID DESC
                    LIMIT 1
                """, (telegram_id,))
            
            notif = cursor.fetchone()
            if notif:
                print(f"\n7️⃣ التحقق من الإشعار في قاعدة البيانات:")
                print(f"   ✅ وجدنا الإشعار!")
                print(f"   NotificationID: {notif[0]}")
                print(f"   CustomerTelegramID: {notif[1]}")
                print(f"   Type: {notif[2]}")
                print(f"   Title: {notif[3]}")
            else:
                print(f"\n7️⃣ التحقق من الإشعار في قاعدة البيانات:")
                print(f"   ❌ لم نجد الإشعار!")
            
            cursor.close()
            conn.close()
    else:
        print(f"   ❌ لن يتم استدعاء الدالة")
        if not (all_sellers_closed and user_info):
            print(f"   السبب: الشروط غير مستوفاة")
    
    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    simulate_closed_store_purchase()
