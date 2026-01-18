#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
جلب بيانات البائع من الـ Telegram ID
Get seller data from Telegram ID
"""

import os
import sys
import sqlite3
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
IS_POSTGRES = bool(DATABASE_URL)

def get_db_connection():
    """الحصول على اتصال قاعدة البيانات"""
    if IS_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print(f"❌ خطأ في الاتصال بـ PostgreSQL: {e}")
            return None
    else:
        try:
            db_path = os.path.join('data', 'TelegramStoreBot.db')
            conn = sqlite3.connect(db_path)
            return conn
        except Exception as e:
            print(f"❌ خطأ في الاتصال بـ SQLite: {e}")
            return None

def test():
    """اختبار"""
    print("\n" + "="*60)
    print("📱 جلب بيانات جميع البائعين")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ فشل الاتصال بقاعدة البيانات")
        return
    
    try:
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute('''
                SELECT 
                    sellerid,
                    telegramid,
                    username,
                    storename,
                    COALESCE(requirecustomerregistration, 0) as is_closed
                FROM sellers
                ORDER BY sellerid
            ''')
        else:
            cursor.execute('''
                SELECT 
                    SellerID,
                    TelegramID,
                    UserName,
                    StoreName,
                    COALESCE(RequireCustomerRegistration, 0) as is_closed
                FROM Sellers
                ORDER BY SellerID
            ''')
        
        sellers = cursor.fetchall()
        
        for sid, tid, uname, sname, is_closed in sellers:
            status = "🔒 مقفول" if is_closed == 1 else "🔓 مفتوح"
            print(f"\n📦 SellerID={sid}  TelegramID={tid}  {status}")
            print(f"   Username: {uname}")
            print(f"   StoreName: {sname}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test()
