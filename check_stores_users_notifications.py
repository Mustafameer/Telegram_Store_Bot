#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار محاكاة شراء من متجر مغلق
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import (
    get_db_connection, IS_POSTGRES, get_seller_by_id, 
    get_user, is_customer_registered_for_store_by_telegram_id,
    get_customer_notifications
)

def check_store_and_user_status():
    """فحص حالة المتاجر والمستخدم"""
    print("=" * 80)
    print("🔍 فحص حالة المتاجر والمستخدمين")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على قائمة البائعين (المتاجر)
    print("\n1️⃣ قائمة جميع البائعين (المتاجر):")
    print("-" * 80)
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT "sellerid", "telegramid", "storename", "requirecustomerregistration"
            FROM sellers
            ORDER BY "sellerid"
        """)
    else:
        cursor.execute("""
            SELECT SellerID, TelegramID, Name, RequireRegistration
            FROM Sellers
            ORDER BY SellerID
        """)
    
    sellers = cursor.fetchall()
    for seller in sellers:
        seller_id, telegram_id, name, require_registration = seller
        status = "🔒 مغلقة (يتطلب تسجيل)" if require_registration else "🔓 مفتوحة"
        print(f"   • ID={seller_id:2d} | TG={telegram_id} | {name:20s} | {status}")
    
    # الحصول على قائمة العملاء المسجلين
    print("\n2️⃣ قائمة العملاء المسجلين (CreditCustomers):")
    print("-" * 80)
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT "customerid", "telegramid", "fullname", "sellerid"
            FROM creditcustomers
            ORDER BY "customerid"
        """)
    else:
        cursor.execute("""
            SELECT CustomerID, TelegramID, FullName, SellerID
            FROM CreditCustomers
            ORDER BY CustomerID
        """)
    
    customers = cursor.fetchall()
    for customer in customers:
        customer_id, tg_id, full_name, seller_id = customer
        print(f"   • ID={customer_id:2d} | TG={tg_id} | {full_name:20s} | Seller={seller_id}")
    
    # فحص المستخدمين العاديين
    print("\n3️⃣ قائمة المستخدمين (Users table):")
    print("-" * 80)
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT "userid", "telegramid", "username"
            FROM users
            ORDER BY "userid"
        """)
    else:
        cursor.execute("""
            SELECT UserID, TelegramID, Username
            FROM Users
            ORDER BY UserID
        """)
    
    users = cursor.fetchall()
    for user in users:
        user_id, tg_id, username = user
        print(f"   • ID={user_id:2d} | TG={tg_id} | {username}")
    
    cursor.close()
    conn.close()
    
    # الآن فحص الإشعارات
    print("\n4️⃣ قائمة جميع الإشعارات:")
    print("-" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT "NotificationID", "CustomerTelegramID", "Type", "Title", "CreatedAt"
            FROM "Notifications"
            ORDER BY "NotificationID" DESC
            LIMIT 10
        """)
    else:
        cursor.execute("""
            SELECT NotificationID, CustomerTelegramID, Type, Title, CreatedAt
            FROM Notifications
            ORDER BY NotificationID DESC
            LIMIT 10
        """)
    
    notifications = cursor.fetchall()
    if notifications:
        for notif in notifications:
            print(f"   • ID={notif[0]} | TG={notif[1]} | Type={notif[2]} | {notif[3]} | {notif[4]}")
    else:
        print("   ❌ لا توجد إشعارات")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_store_and_user_status()
