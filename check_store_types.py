#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص قيم RequireCustomerRegistration في قاعدة البيانات
Check RequireCustomerRegistration values in database
"""

import sqlite3

def check_database():
    """فحص جميع المتاجر وقيم RequireCustomerRegistration الخاصة بهم"""
    
    try:
        conn = sqlite3.connect("data/bot_storage.db")
        cursor = conn.cursor()
        
        # فحص 1: عرض جميع المتاجر وقيمهم
        print("="*70)
        print("🔍 **فحص قيم RequireCustomerRegistration في قاعدة البيانات**")
        print("="*70)
        print()
        
        cursor.execute("""
            SELECT 
                SellerID,
                StoreName,
                UserName,
                RequireCustomerRegistration as IsLocked,
                Status
            FROM Sellers
            ORDER BY SellerID
        """)
        
        sellers = cursor.fetchall()
        
        if not sellers:
            print("❌ لا توجد متاجر في قاعدة البيانات!")
            return
        
        print("📋 **جميع المتاجر:**\n")
        for seller in sellers:
            seller_id, name, username, is_locked, status = seller
            locked_status = "🔴 مقفول (متجر مغلق)" if is_locked == 1 else "🟢 مفتوح"
            print(f"  المتجر #{seller_id}: {name} (@{username})")
            print(f"    المتجر: {locked_status} | الحالة: {status}")
            print()
        
        # فحص 2: إحصائيات
        cursor.execute("""
            SELECT 
                COUNT(*) as total_stores,
                COUNT(CASE WHEN RequireCustomerRegistration = 0 THEN 1 END) as open_stores,
                COUNT(CASE WHEN RequireCustomerRegistration = 1 THEN 1 END) as closed_stores
            FROM Sellers
        """)
        
        stats = cursor.fetchone()
        total, open_stores, closed_stores = stats
        
        print("📊 **الإحصائيات:**")
        print(f"  إجمالي المتاجر: {total}")
        print(f"  متاجر مفتوحة: {open_stores} 🟢")
        print(f"  متاجر مقفولة: {closed_stores} 🔴")
        print()
        
        # فحص 3: المشكلة
        if closed_stores > 0:
            print("⚠️ **المشكلة المكتشفة:**")
            print(f"   يوجد {closed_stores} متجر مقفول يعرض خيار الصور المتعددة!")
            print("   السبب: النطاق الاحتياطي requireCustomerRegistration = 1")
            print()
            
            cursor.execute("""
                SELECT SellerID, StoreName FROM Sellers 
                WHERE RequireCustomerRegistration = 1
            """)
            closed = cursor.fetchall()
            
            print("   المتاجر المقفولة:")
            for seller_id, name in closed:
                print(f"     - {name} (SellerID: {seller_id})")
        else:
            print("✅ **جميع المتاجر مفتوحة!**")
            print("   لا توجد متاجر مقفولة في قاعدة البيانات")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        print("   تأكد من أن البوت قد عمل مرة واحدة لإنشاء قاعدة البيانات")

if __name__ == "__main__":
    check_database()
