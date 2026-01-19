#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار سريع للتحقق من حالة البوت والـ API
"""

import subprocess
import time
import requests
import sys

def check_bot_running():
    """التحقق من أن البوت يعمل"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=2)
        if response.status_code == 200:
            print("✅ البوت يعمل!")
            print(f"   الرد: {response.json()}")
            return True
    except:
        print("❌ البوت غير مشغّل أو لا يمكن الوصول إليه")
        return False

def check_database():
    """التحقق من قاعدة البيانات"""
    try:
        from bot import get_db_connection, IS_POSTGRES
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            # PostgreSQL
            cursor.execute("SELECT COUNT(*) FROM imagestorage")
        else:
            # SQLite
            cursor.execute("SELECT COUNT(*) FROM imagestorage")
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"✅ قاعدة البيانات تعمل")
        print(f"   عدد الصور في imagestorage: {count}")
        return True
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False

def test_api_endpoint():
    """اختبار API endpoint"""
    payload = {
        "product_id": 1,
        "quantity": 1,
        "customer_id": 1,
        "seller_id": 1,
        "customer_telegram_id": 123456789
    }
    
    try:
        response = requests.post(
            'http://localhost:5000/api/buy-images',
            json=payload,
            timeout=5
        )
        
        print(f"✅ API endpoint يرد")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ لا يمكن الاتصال بـ API")
        return False
    except Exception as e:
        print(f"❌ خطأ في API: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 فحص شامل للنظام")
    print("=" * 60)
    
    print("\n1️⃣ التحقق من البوت...")
    bot_ok = check_bot_running()
    
    print("\n2️⃣ التحقق من قاعدة البيانات...")
    db_ok = check_database()
    
    if bot_ok:
        print("\n3️⃣ اختبار API endpoint...")
        api_ok = test_api_endpoint()
    else:
        print("\n⚠️ البوت غير مشغّل - تخطي اختبار API")
    
    print("\n" + "=" * 60)
    print("📊 النتائج:")
    print(f"  البوت: {'✅' if bot_ok else '❌'}")
    print(f"  قاعدة البيانات: {'✅' if db_ok else '❌'}")
    if bot_ok:
        print(f"  API: {'✅' if api_ok else '❌'}")
    print("=" * 60)
