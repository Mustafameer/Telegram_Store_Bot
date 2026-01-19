#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار API endpoint لشراء الصور
Test /api/buy-images endpoint
"""

import requests
import json
import time

# API endpoint
API_URL = "http://localhost:5000/api/buy-images"

def test_buy_images():
    """اختبار شراء الصور من API"""
    
    # بيانات الطلب - عدّل هذه القيم حسب قاعدة بيانتك
    payload = {
        "product_id": 1,           # عدّل إلى منتج موجود
        "quantity": 2,             # عدد الصور المراد شراؤها
        "customer_id": 1,          # عدّل إلى عميل موجود
        "seller_id": 1,            # عدّل إلى بائع موجود
        "customer_telegram_id": 123456789  # أي قيمة
    }
    
    print("=" * 60)
    print("🧪 اختبار API: POST /api/buy-images")
    print("=" * 60)
    print(f"\n📤 إرسال الطلب:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        print(f"\n📡 جاري الاتصال بـ {API_URL}...")
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n✅ رد الخادم:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body:")
        
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except:
            print(f"   {response.text}")
        
        if response.status_code == 200:
            print("\n✅ النجاح! API يعمل بشكل صحيح")
            return True
        else:
            print(f"\n❌ خطأ: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ خطأ: لا يمكن الاتصال بـ {API_URL}")
        print("   تأكد من أن البوت يعمل: python bot.py")
        return False
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    test_buy_images()
