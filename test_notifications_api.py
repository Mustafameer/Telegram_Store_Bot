#!/usr/bin/env python3
"""
اختبار API الإشعارات
Test the Notifications API
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

def test_health():
    """اختبر حالة API"""
    print("🧪 Testing /api/health...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✅ Status: {response.status_code}")
        print(f"📝 Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_notifications(customer_id=123456789, unread_only=True):
    """اختبر الحصول على الإشعارات"""
    print(f"\n🧪 Testing GET /api/notifications...")
    print(f"   Parameters: customer_id={customer_id}, unread_only={unread_only}")
    
    try:
        url = f"{API_BASE}/notifications"
        params = {
            'customer_id': customer_id,
            'unread_only': str(unread_only).lower()
        }
        
        response = requests.get(url, params=params, timeout=10)
        print(f"✅ Status: {response.status_code}")
        
        data = response.json()
        print(f"📝 Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_mark_as_read(notification_id=1):
    """اختبر وضع علامة على إشعار"""
    print(f"\n🧪 Testing POST /api/notifications/{notification_id}/read...")
    
    try:
        url = f"{API_BASE}/notifications/{notification_id}/read"
        response = requests.post(url, timeout=10)
        print(f"✅ Status: {response.status_code}")
        
        data = response.json()
        print(f"📝 Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """تشغيل جميع الاختبارات"""
    print("=" * 60)
    print("🚀 Notification API Test Suite")
    print("=" * 60)
    
    print(f"\n📍 API Base URL: {API_BASE}")
    print("\nتأكد من أن bot.py يعمل على الخادم قبل الاختبار!")
    print("Make sure bot.py is running before testing!")
    
    time.sleep(2)
    
    # Test 1: Health check
    print("\n" + "=" * 60)
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ API is not responding. Make sure bot.py is running.")
        print("  تشغيل: python bot.py")
        return False
    
    # Test 2: Get notifications
    print("\n" + "=" * 60)
    test_get_notifications()
    
    # Test 3: Mark as read (if notifications exist)
    print("\n" + "=" * 60)
    test_mark_as_read()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️ Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
