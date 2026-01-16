#!/usr/bin/env python3
"""
اختبار البوت - التحقق من الـ Token
Test Bot - Verify Token
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_KEY = os.getenv("TELEGRAM_API_KEY")
print(f"\n{'='*60}")
print(f"🔍 التحقق من البوت Token")
print(f"{'='*60}\n")

# اختبار الـ Token
url = f"https://api.telegram.org/bot{API_KEY}/getMe"
response = requests.get(url)
data = response.json()

if data.get('ok'):
    bot_info = data['result']
    print(f"✅ البوت Token صحيح!")
    print(f"\n📋 معلومات البوت:")
    print(f"   • الاسم: {bot_info.get('first_name')}")
    print(f"   • Username: @{bot_info.get('username')}")
    print(f"   • ID: {bot_info.get('id')}")
    print(f"   • تم إنشاؤه: {bot_info.get('can_join_groups')}")
    
    # حذف أي webhook قديم
    print(f"\n🔄 جاري حذف أي webhook قديم...")
    del_url = f"https://api.telegram.org/bot{API_KEY}/deleteWebhook"
    del_response = requests.get(del_url)
    print(f"✅ تم حذف webhook")
    
    print(f"\n{'='*60}")
    print(f"✅ جميع الاختبارات نجحت!")
    print(f"\nالآن شغّل:")
    print(f"   python polling_bot.py")
    print(f"{'='*60}\n")
else:
    print(f"❌ خطأ: {data.get('description')}")
    print(f"\nتأكد من الـ Token في ملف .env")
