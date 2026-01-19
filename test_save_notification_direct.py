#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار مباشر لدالة save_notification
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import save_notification, get_customer_notifications, get_db_connection, IS_POSTGRES
import json

def test_save_notification():
    """اختبار حفظ إشعار"""
    print("=" * 60)
    print("🧪 اختبار save_notification()")
    print("=" * 60)
    
    # اختبار حفظ إشعار
    print("\n1️⃣ محاولة حفظ إشعار تجريبي...")
    
    telegram_id = 123456789  # معرف تليجرام تجريبي
    
    result = save_notification(
        customer_telegram_id=telegram_id,
        notification_type='test_notification',
        title='🧪 اختبار الإشعار',
        message='هذا اختبار لنظام الإشعارات',
        product_names='منتج اختبار',
        total_amount=100.0,
        seller_id=1,
        data=None
    )
    
    print(f"\n📊 النتيجة: {result}")
    
    # تحقق من قاعدة البيانات
    print("\n2️⃣ فحص جدول الإشعارات...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute('SELECT COUNT(*) FROM "Notifications"')
        else:
            cursor.execute('SELECT COUNT(*) FROM Notifications')
        
        count = cursor.fetchone()[0]
        print(f"✅ عدد الإشعارات في الجدول: {count}")
        
        # اعرض آخر إشعار
        if IS_POSTGRES:
            cursor.execute("""
                SELECT "NotificationID", "CustomerTelegramID", "Title", "CreatedAt" 
                FROM "Notifications" 
                ORDER BY "NotificationID" DESC 
                LIMIT 1
            """)
        else:
            cursor.execute("""
                SELECT NotificationID, CustomerTelegramID, Title, CreatedAt 
                FROM Notifications 
                ORDER BY NotificationID DESC 
                LIMIT 1
            """)
        
        last_notification = cursor.fetchone()
        if last_notification:
            print(f"\n📝 آخر إشعار:")
            print(f"   ID: {last_notification[0]}")
            print(f"   TelegramID: {last_notification[1]}")
            print(f"   Title: {last_notification[2]}")
            print(f"   CreatedAt: {last_notification[3]}")
        else:
            print("❌ لا توجد إشعارات")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الجدول: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_save_notification()
